"""LCOH2-Rechner: Oberfläche.  Start:  streamlit run app.py"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lcoh.economics import compute_economics
from lcoh.help_texts import HELP
from lcoh.input_spec import SPEC_BY_KEY
from lcoh.inputs import Inputs
from lcoh.operation import run_operation
from lcoh.charts import COST_BLOCKS as COST_BLOCK_NAMES, battery_soc_figure, cost_structure_figure, load_duration_figure, spot_price_figure
from lcoh.ui_layout import (CHOICE_LABELS, COCKPIT, FINE_STEP, GATES, LABEL_OVERRIDES, LEVIES, PAGES, REVENUE_PAGE,
                            VISIBLE)
from lcoh.waterfall import (BLOCK_CAPEX, BLOCK_INTEREST, BLOCK_OPEX, BLOCK_POWER, BLOCK_REVENUE, BLOCK_STACK,
                            BLOCK_SUBSIDY, block_subtotal, net_power_items, waterfall_items)
from lcoh.zeitreihen import SERIES_LABELS, load_default_timeseries, parse_series

ASSETS = Path(__file__).resolve().parent / "assets"
st.set_page_config(page_title="Wasserstoff-Kostenrechner", page_icon="💧", layout="wide")
st.markdown("""
<style>
div[data-testid="stVerticalBlockBorderWrapper"] h4 {margin-top: 0; font-size: 1.05rem;}
.block-container {padding-top: 2.2rem;}
[data-testid="stTab"] p {font-weight: 700 !important; font-size: 1.2rem !important;}
.st-key-cockpit_out [data-testid="stMetricLabel"] p {white-space: normal !important;}
.st-key-cockpit_in [data-testid="stWidgetLabel"] {min-height: 2.8rem; align-items: flex-end;}
.st-key-cockpit_out [data-testid="stMetricValue"] {font-size: 1.6rem;}
[data-testid="stTabPanel"] [data-testid="stTab"] p {font-weight: 400 !important; font-size: 1.05rem !important;}
section[data-testid="stSidebar"] {width: 250px !important; min-width: 250px !important;}
.st-key-cockpit_out [data-testid="stMetric"] {width: 100%; align-items: center;}
.st-key-cockpit_out [data-testid="stMetric"] * {justify-content: center !important; text-align: center !important;}
.sumbox.small {margin-bottom: 0; gap: 1.2rem;}
.sumbox.small .v {font-size: 1rem;}
.sumbox {display: flex; gap: 2rem; justify-content: flex-end; text-align: right; margin-bottom: .5rem;}
.sumbox .l {font-size: .8rem; color: #666;}
.sumbox .v {font-size: 1.25rem; font-weight: 700; white-space: nowrap;}
</style>""", unsafe_allow_html=True)


def de(x: float, n: int = 2) -> str:
    """Zahl im deutschen Format."""
    return f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- Zustand
NUMERIC_KEYS = [sp.key for sp in SPEC_BY_KEY.values() if sp.kind in ("number", "percent")]
SELECT_KEYS = [sp.key for sp in SPEC_BY_KEY.values()
               if sp.kind == "choice" and (len(sp.choices) > 3 or isinstance(sp.choices[0], int))]
BLANK_KEYS = NUMERIC_KEYS + SELECT_KEYS


def empty_state() -> dict:
    """Leerer Startzustand: Zahlenfelder ohne Wert; Schalter und Auswahlfelder stehen auf ihren Standardwerten."""
    d = Inputs().to_dict()
    for k in BLANK_KEYS:
        d[k] = None
    return d


if "S" not in st.session_state:
    st.session_state["S"] = empty_state()
if "series" not in st.session_state:
    st.session_state["series"] = {}
S: dict = st.session_state["S"]


def reset_widgets() -> None:
    for key in [k for k in st.session_state if k.startswith("w_")]:
        del st.session_state[key]


def to_display(spec, value):
    if value is None:
        return None
    return value * 100 if spec.kind == "percent" else value


def from_display(spec, value):
    if value is None:
        return None
    if spec.kind == "percent":
        return value / 100
    if spec.kind == "number" and is_int(spec):
        return int(value)
    return value


def is_int(spec) -> bool:
    return isinstance(spec.default, int) and not isinstance(spec.default, bool)


def fine_percent(spec) -> bool:
    d = spec.default * 100
    return spec.key in FINE_STEP or abs(round(d, 1) - d) > 1e-9


def default_step(spec) -> float:
    if is_int(spec):
        return 1
    if spec.kind == "percent":
        return 0.01 if fine_percent(spec) else 0.1
    d = abs(spec.default) if spec.default else 1.0
    return 100.0 if d >= 5000 else 10.0 if d >= 100 else 1.0 if d >= 10 else 0.5 if d >= 1 else 0.1


def decimals_of(spec):
    """Anzahl Nachkommastellen: Geldwerte 2, Prozent 1 (bzw. 2), ganze Zahlen 0, sonst frei (None)."""
    unit = spec.unit or ""
    if is_int(spec):
        return 0
    if spec.kind == "percent":
        return 2 if fine_percent(spec) else 1
    if "€" in unit or unit.startswith("ct"):
        return 2
    return None


def fmt_de(value: float, decimals) -> str:
    if value is None:
        return ""
    if decimals is None:
        txt = f"{value:,.4f}".rstrip("0").rstrip(".")
    else:
        txt = f"{value:,.{decimals}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def parse_de(text: str) -> float:
    t = text.strip().replace(" ", "").replace("\u00a0", "")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif "." in t and re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    return float(t)


def uses_text_field(spec) -> bool:
    """Zahlen werden als Textfeld im deutschen Format (1.000,00) dargestellt; das Streamlit-Zahlenfeld kann das nicht."""
    return spec.kind in ("number", "percent")


def commit_text(key: str) -> None:
    spec = SPEC_BY_KEY[key]
    wk = f"w_{key}"
    errs = st.session_state.setdefault("_ferr", {})
    dec = decimals_of(spec)
    if not str(st.session_state[wk]).strip():
        errs.pop(key, None)
        S[key] = None
        st.session_state[wk] = ""
        return
    try:
        v = parse_de(st.session_state[wk])
        lo = to_display(spec, spec.minimum) if spec.minimum is not None else None
        hi = to_display(spec, spec.maximum) if spec.maximum is not None else None
        if lo is not None and v < lo - 1e-12:
            raise ValueError(f"Der Wert darf nicht kleiner als {fmt_de(lo, dec)} sein.")
        if hi is not None and v > hi + 1e-12:
            raise ValueError(f"Der Wert darf nicht größer als {fmt_de(hi, dec)} sein.")
    except ValueError as err:
        msg = str(err)
        errs[key] = msg if msg.startswith("Der Wert") else "Bitte eine Zahl eingeben, zum Beispiel 25.000 oder 12,5."
        st.session_state[wk] = fmt_de(to_display(spec, S[key]), dec)
        return
    errs.pop(key, None)
    S[key] = from_display(spec, v)
    st.session_state[wk] = fmt_de(v, dec)


def field(key: str, label: str | None = None, hide_label: bool = False) -> None:
    """Zeichnet ein Eingabefeld. Der Wert bleibt auch dann erhalten, wenn das Feld ausgeblendet wird."""
    spec = SPEC_BY_KEY[key]
    wk = f"w_{key}"
    unit = {"percent": "%"}.get(spec.kind, spec.unit)
    base = label or LABEL_OVERRIDES.get(key) or spec.label
    text = label or (base + (f" [{unit}]" if unit else ""))
    vis = "collapsed" if hide_label else "visible"
    use_text = uses_text_field(spec)
    dec = decimals_of(spec)
    if wk not in st.session_state:
        v0 = to_display(spec, S[key])
        st.session_state[wk] = fmt_de(v0, dec) if use_text else v0
    helptext = HELP.get(key)
    if spec.kind == "bool":
        val = st.toggle(text, key=wk, help=helptext)
    elif spec.kind == "choice":
        fmt = CHOICE_LABELS.get(key, {}).get
        if len(spec.choices) <= 3 and not isinstance(spec.choices[0], int):
            val = st.radio(text, spec.choices, key=wk, help=helptext, horizontal=True,
                           format_func=lambda x: fmt(x, x), label_visibility=vis)
        else:
            val = st.selectbox(text, spec.choices, key=wk, help=helptext, format_func=lambda x: fmt(x, str(x)),
                               label_visibility=vis, index=None, placeholder="Bitte wählen")
    elif use_text:
        st.text_input(text, key=wk, help=helptext, on_change=commit_text, args=(key,), label_visibility=vis)
        err = st.session_state.get("_ferr", {}).get(key)
        if err:
            st.caption(f":red[{err}]")
        return
    S[key] = from_display(spec, val)


def visible(key: str) -> bool:
    rule = VISIBLE.get(key)
    return True if rule is None else bool(rule(S))


SECTION_SLOTS: dict = {}


def render_section(title: str, gate: str | None, keys: list[str], skip: set[str] | None = None,
                   scope: str = "") -> None:
    keys = [k for k in keys if not skip or k not in skip]
    with st.container(border=True):
        h1, h2 = st.columns([1.1, 1.1])
        h1.markdown(f"#### {title}")
        SECTION_SLOTS[f"{scope}|{title}"] = h2.container()
        if gate is not None:
            on = GATES[gate](S) if gate in GATES else bool(S[gate])
            if not on:
                st.caption("Dieser Bereich ist ausgeschaltet. Der Schalter steht im Cockpit bzw. in einem anderen Bereich.")
                return
        for key in keys:
            if visible(key):
                field(key)


def render_levies() -> None:
    with st.container(border=True):
        st.markdown("#### Stromnebenkosten und Befreiungen")
        st.caption("Je Bestandteil: Höhe in ct/kWh und – falls zutreffend – die Befreiung. Befreite Bestandteile werden "
                   "nicht berechnet, ihr Wert erscheint als Privilegierung in den Ergebnissen.")
        h = st.columns([2.2, 1.4, 1.1, 1.4, 1.1])
        for col, txt in zip(h, ["Bestandteil", "Elektrolyseur [ct/kWh]", "befreit", "Übrige Verbraucher [ct/kWh]", "befreit"]):
            col.markdown(f"**{txt}**")
        for name, label in LEVIES:
            c = st.columns([2.2, 1.4, 1.1, 1.4, 1.1])
            c[0].markdown(label, help=HELP[f"levy_ely_{name}_ct_per_kwh"].split(" für ")[0] + ".")
            with c[1]:
                field(f"levy_ely_{name}_ct_per_kwh", hide_label=True)
            with c[2]:
                field(f"levy_ely_{name}_exempt", label="befreit")
            with c[3]:
                field(f"levy_rest_{name}_ct_per_kwh", hide_label=True)
            with c[4]:
                field(f"levy_rest_{name}_exempt", label="befreit")
        c = st.columns([2.2, 1.4, 1.1, 1.4, 1.1])
        c[0].markdown("Leistungspreis [€/kW·Monat]", help="Monatlicher Preis für die bezogene Leistung. Er wirkt nur, "
                      "wenn der Leistungspreis nicht befreit ist.")
        with c[1]:
            field("demand_charge_ely_eur_per_kw_month", hide_label=True)
        with c[2]:
            field("demand_charge_ely_exempt", label="befreit")
        with c[3]:
            field("demand_charge_rest_eur_per_kw_month", hide_label=True)
        with c[4]:
            field("demand_charge_rest_exempt", label="befreit")


# ---------------------------------------------------------------- Zeitreihen
def build_timeseries() -> pd.DataFrame:
    ts = load_default_timeseries().copy()
    for name, values in st.session_state["series"].items():
        if name == "day_ahead":
            for col in [c for c in ts.columns if c.startswith("day_ahead_")]:
                ts[col] = values
        else:
            ts[name] = values
    return ts


@st.cache_data(show_spinner="Berechnung läuft ...", max_entries=8)
def rechnen(inputs_json: str, series_json: str):
    inp = Inputs.from_dict(json.loads(inputs_json))
    ts = load_default_timeseries().copy()
    for name, values in json.loads(series_json).items():
        if name == "day_ahead":
            for col in [c for c in ts.columns if c.startswith("day_ahead_")]:
                ts[col] = values
        else:
            ts[name] = values
    r = run_operation(inp, ts)
    return r, compute_economics(r)


# ---------------------------------------------------------------- Seitenleiste (Laden/Speichern)
with st.sidebar:
    st.image(str(ASSETS / "logo_hs_flensburg.png"), width=170)
    st.image(str(ASSETS / "logo_nrl.png"), width=190)
    st.markdown("**Eingaben speichern und laden**")
    upload = st.file_uploader("Gespeicherte Eingaben laden (.json)", type="json", key="up_inputs")
    if upload is not None and st.session_state.get("_loaded") != (upload.name, upload.size):
        try:
            raw = json.load(upload)
            filled = {k: v for k, v in raw.items() if v is not None}
            loaded = Inputs.from_dict({**Inputs().to_dict(), **filled}).to_dict()
            for k in BLANK_KEYS:
                if k in raw and raw[k] is None:
                    loaded[k] = None
            S.update(loaded)
            reset_widgets()
            st.session_state["_loaded"] = (upload.name, upload.size)
            st.rerun()
        except Exception:
            st.error("Die Datei konnte nicht gelesen werden. Bitte eine mit diesem Tool gespeicherte Datei verwenden.")
    if st.button("Standardwerte laden", width="stretch",
                 help="Füllt alle Eingabefelder mit sinnvollen Beispielwerten. Diese können Sie anschließend anpassen."):
        S.update(Inputs().to_dict())
        st.session_state.pop("_loaded", None)
        reset_widgets()
        st.rerun()
    if st.button("Alle Felder leeren", width="stretch"):
        S.update(empty_state())
        st.session_state.pop("_loaded", None)
        reset_widgets()
        st.rerun()

st.markdown("# Wasserstoff-Kostenrechner")
st.caption("Was kostet ein Kilogramm grüner Wasserstoff aus Ihrem Elektrolyseprojekt?")
tab_cockpit, tab_inputs, tab_rev, tab_res, tab_data = st.tabs(
    ["Cockpit", "Eingaben", "Einnahmepotenziale", "Ergebnisse", "Daten"])

# ---------------------------------------------------------------- Cockpit (Eingaben links)
def row(keys: list[str]) -> None:
    cols = st.columns(len(keys))
    for col, key in zip(cols, keys):
        with col:
            if key is None:
                continue
            if visible(key):
                field(key)


with tab_cockpit:
    left, right = st.columns([1.1, 1.1])
    with left:
        st.markdown("### **Elektrolysesystem**")
        with st.container(key="cockpit_in"):
            with st.container(border=True):
                st.markdown("#### Elektrolyseur & Projekt")
                row(["electrolyzer_power_kw", "capex_electrolyzer_eur_per_kw", "electrolyzer_efficiency"])
                row(["commissioning_year", "project_lifetime_years", "min_part_load"])
            with st.container(border=True):
                st.markdown("#### Batterie")
                row(["battery_enabled", "battery_capacity_hours", "battery_input_power_kw"])
            with st.container(border=True):
                st.markdown("#### Strombezug")
                st.caption("Grundlast-PPA: konstanter Bezug. Pay-as-Produced-PPA: Bezug folgt der PV- bzw. Windeinspeisung.")
                row(["ppa_baseload_enabled", "ppa_baseload_kw", "ppa_baseload_price_eur_per_mwh"])
                row(["ppa_pap_enabled", None, None])
                row([None, "ppa_pv_kw", "ppa_pv_price_eur_per_mwh"])
                row([None, "ppa_wind_kw", "ppa_wind_price_eur_per_mwh"])
                st.caption("Weitere Bezugsquellen (Details unter „Eingaben“, Reiter „Strombezug & Nebenkosten“):")
                row(["section7_enabled", "section13k_enabled", "spot_enabled"])
    cockpit_slot = right.container(key="cockpit_out")

# ---------------------------------------------------------------- Eingabeseiten
SUMMARY_SLOTS: dict = {}
with tab_inputs:
    sub = st.tabs([name for name, _ in PAGES])
    cockpit_keys = {k for _, _, ks in COCKPIT for k in ks}
    for tab, (name, sections) in zip(sub, PAGES):
        with tab:
            SUMMARY_SLOTS[name] = st.container()
            cols = st.columns(2)
            i = 0
            for title, gate, keys in sections:
                with cols[i % 2]:
                    render_section(title, gate, keys, skip=cockpit_keys, scope=name)
                i += 1
            if name == "Strombezug & Nebenkosten":
                render_levies()

with tab_rev:
    st.markdown("### Einnahmepotenziale")
    st.caption("Zusätzliche Erlöse, die die Gestehungskosten senken.")
    SUMMARY_SLOTS["Einnahmepotenziale"] = st.container()
    cols = st.columns(2)
    for i, (title, gate, keys) in enumerate(REVENUE_PAGE):
        with cols[i % 2]:
            render_section(title, gate, keys, scope="Einnahmepotenziale")

# ---------------------------------------------------------------- Prüfung und Rechnung
GATE_OF = {k: g for _, secs in PAGES for _, g, ks in secs for k in ks}
GATE_OF.update({k: g for _, g, ks in REVENUE_PAGE for k in ks})


def is_active(key: str) -> bool:
    """Eingabe ist sichtbar und ihr Abschnitt eingeschaltet."""
    gate = GATE_OF.get(key)
    if gate is not None and not (GATES[gate](S) if gate in GATES else bool(S[gate])):
        return False
    return visible(key)


defaults_dict = Inputs().to_dict()
shown_keys = set(GATE_OF) | {k for _, _, ks in COCKPIT for k in ks} | {f"levy_{sd}_{n}_ct_per_kwh" for sd in ("ely", "rest")
                                                                      for n, _ in LEVIES}
shown_keys |= {"demand_charge_ely_eur_per_kw_month", "demand_charge_rest_eur_per_kw_month"}
# Felder mit Standardwert 0 sind freiwillig; ein leeres Feld zählt dort als 0
missing = [k for k in BLANK_KEYS if S[k] is None and k in shown_keys and defaults_dict[k] not in (0, 0.0)
           and is_active(k)]
effective = {k: (defaults_dict[k] if v is None else v) for k, v in S.items()}
inp_eff = Inputs.from_dict(effective)
errors = inp_eff.validate()


def render_data_tab(inp) -> None:
    st.markdown("### Zeitreihen (Energiedaten und Preise)")
    st.caption("Im Standard rechnet das Tool mit den hinterlegten Zeitreihen. Eigene Reihen müssen genau 8.760 Stundenwerte "
               "enthalten (eine Zahl pro Zeile, als .csv oder .txt; Dezimalkomma ist erlaubt).")
    defaults = load_default_timeseries()
    series_info = {
        "wind_kwh_per_kw": ("wind_kwh_per_kw", "kWh/kW"), "pv_kwh_per_kw": ("pv_kwh_per_kw", "kWh/kW"),
        "day_ahead": (f"day_ahead_{inp.day_ahead_scenario_year}_eur_per_mwh", "€/MWh"),
        "co2_eur_per_t": ("co2_eur_per_t", "€/t"), "section13k_kwh": ("section13k_kwh", "kWh")}
    for name, (col, unit) in series_info.items():
        with st.container(border=True):
            c1, c2 = st.columns([1.2, 1])
            custom = name in st.session_state["series"]
            values = np.array(st.session_state["series"][name] if custom else defaults[col], dtype=float)
            with c1:
                st.markdown(f"**{SERIES_LABELS[name]}** · {'eigene Datei' if custom else 'Standardwerte'}")
                fig = go.Figure(go.Scatter(y=values, mode="lines", line=dict(color="#1f4e79", width=1)))
                fig.update_layout(height=160, margin=dict(l=0, r=0, t=5, b=0), yaxis_title=unit, xaxis_title="Stunde")
                st.plotly_chart(fig, width="stretch", key=f"plot_{name}")
                st.caption(f"Summe {de(values.sum(), 0)} · Mittelwert {de(values.mean(), 3)} · Maximum {de(values.max(), 2)} {unit}")
            with c2:
                up = st.file_uploader("Eigene Zeitreihe hochladen", type=["csv", "txt"], key=f"up_{name}")
                if up is not None and st.session_state.get(f"_up_{name}") != (up.name, up.size):
                    try:
                        st.session_state["series"][name] = parse_series(up.getvalue())
                        st.session_state[f"_up_{name}"] = (up.name, up.size)
                        st.rerun()
                    except ValueError as err:
                        st.error(str(err))
                st.download_button("Aktuelle Reihe herunterladen (.csv)", "\n".join(f"{v:.6g}" for v in values),
                                   f"{name}.csv", "text/csv", key=f"dl_{name}", width="stretch")
                if custom and st.button("Auf Standard zurücksetzen", key=f"rs_{name}", width="stretch"):
                    del st.session_state["series"][name]
                    st.session_state.pop(f"_up_{name}", None)
                    st.rerun()
    st.info("Hinweis: Eine hochgeladene Preisreihe ersetzt alle hinterlegten Börsenpreis-Szenarien. Die Reihen gelten "
            "für die gesamte Projektlaufzeit; die jährlichen Preisentwicklungen werden wie bisher darauf angewendet.")


if missing or errors:
    with tab_cockpit:
        if missing:
            right.info(f"Es fehlen noch {len(missing)} Angaben. Tragen Sie die Werte ein oder klicken Sie links auf "
                       f"„Standardwerte laden“. Sobald alle Pflichtfelder gefüllt sind, erscheinen hier die Ergebnisse.")
            with right.expander("Welche Angaben fehlen?"):
                for k in missing:
                    st.markdown(f"- {SPEC_BY_KEY[k].label}")
        else:
            right.error("Bitte Eingaben prüfen:\n\n" + "\n".join(f"- {m}" for m in errors))
    with tab_res:
        st.info("Noch keine Ergebnisse: Es fehlen Angaben oder sie sind nicht plausibel. Siehe Reiter „Cockpit“.")
    with tab_data:
        render_data_tab(inp_eff)
    with st.sidebar:
        st.divider()
        st.caption("Noch keine Ergebnisse. Bitte Eingaben ergänzen oder Standardwerte laden.")
        st.divider()
        st.image(str(ASSETS / "logo_bmwe.png"), width=150)
    st.stop()

series_json = json.dumps(st.session_state["series"])
r, e = rechnen(json.dumps(effective, sort_keys=True, default=float), series_json)
inp = r.inputs

with st.sidebar:
    st.divider()
    st.metric("Kosten pro kg Wasserstoff", f"{de(e.lcoh_eur_per_kg)} €/kg",
              help="Wasserstoffgestehungskosten (LCOH2): alle Kosten über die Projektlaufzeit, abzüglich Förderungen und Zusatzeinnahmen, je kg Wasserstoff.")
    st.caption(f"{de(e.lcoh_ct_per_kwh)} ct/kWh (Brennwert)  \n{de(e.h2_kg_per_year / 1000, 0)} t Wasserstoff pro Jahr  \n"
               f"{de(r.full_load_hours, 0)} h/a Ø Auslastung (Volllaststunden)  \n"
               f"{de(r.full_load_hours / 87.6, 1)} % Auslastung")
    st.download_button("Eingaben speichern (.json)", json.dumps(S, ensure_ascii=False, indent=1, default=float),
                       "eingaben_lcoh2.json", "application/json", width="stretch")
    st.divider()
    st.image(str(ASSETS / "logo_bmwe.png"), width=150)

# ---------------------------------------------------------------- Kennzahlen
pc = e.power
green_share = 1 - pc.spot_kwh / pc.total_procurement_kwh if pc.total_procurement_kwh else 0.0
system_util = pc.consumption_total_kwh / (r.power.total_kw * 8760) if r.power.total_kw else 0.0
ely_util = r.full_load_hours / 8760
run_hours = int((r.hourly["consumption_kwh"] > 0).sum())
full_hours = int((r.hourly["consumption_kwh"] >= r.power.total_kw * 0.99999).sum())
part_hours = run_hours - full_hours
HELP_GREEN = ("Anteil des bezogenen Stroms, der nicht aus dem Spotmarkt (Netzmix) stammt. PPA (PV, Wind, Grundlast), "
              "§7 und §13k werden als erneuerbar gewertet. Vereinfachte Kennzahl; sie ersetzt keine Prüfung nach den "
              "RFNBO-Kriterien.")


def summary_box(slot, pairs: list[tuple[str, str]], small: bool = False) -> None:
    html = "".join(f'<div><div class="l">{lab}</div><div class="v">{val}</div></div>' for lab, val in pairs)
    with slot:
        st.markdown(f'<div class="sumbox{" small" if small else ""}">{html}</div>', unsafe_allow_html=True)


def section_sum(scope: str, title: str, pairs: list[tuple[str, str]]) -> None:
    slot = SECTION_SLOTS.get(f"{scope}|{title}")
    if slot is not None:
        summary_box(slot, pairs, small=True)


def eur(v: float) -> str:
    return f"{de(v)} €"


def per_year(label: str, v: float) -> list[tuple[str, str]]:
    return [(label, f"{eur(v)} /a")]


def capex_pair(*names: str) -> list[tuple[str, str]]:
    v = sum(e.capex_items.get(n, 0.0) for n in names)
    return [("Kosten", eur(v)), ("je kW Ely", f"{de(v / ely_kw)} €/kW")]


ely_kw = r.power.ely_kw
capex_sum = sum(e.capex_items.values())
summary_box(SUMMARY_SLOTS["Anlage & Investitionen"], [
    ("Investitionskosten gesamt (CAPEX)", f"{de(e.capex_gross)} €"),
    ("CAPEX je kW Elektrolyseur", f"{de(e.capex_gross / ely_kw)} €/kW")])
summary_box(SUMMARY_SLOTS["Strombezug & Nebenkosten"], [
    ("Stromkosten pro Jahr", f"{de(e.power_cost)} €"),
    ("Mittlerer Strompreis (inkl. Abgaben)", f"{de(e.power_cost / (pc.total_procurement_kwh / 1000) if pc.total_procurement_kwh else 0)} €/MWh")])
summary_box(SUMMARY_SLOTS["Betrieb (OPEX)"], [
    ("OPEX gesamt pro Jahr", f"{de(e.opex_total)} €"),
    ("OPEX je kW Elektrolyseur", f"{de(e.opex_total / ely_kw)} €/(kW·a)"),
    ("Anteil am CAPEX", f"{de(e.opex_total / e.capex_gross * 100 if e.capex_gross else 0, 1)} %")])
summary_box(SUMMARY_SLOTS["Finanzierung & Förderungen"], [
    ("Kapitalkosten pro Jahr", f"{de(e.financing_total)} €"),
    ("Kapitalkostensatz (WACC)", f"{de(e.wacc * 100, 1)} %"),
    ("CAPEX-Förderung gesamt", f"{de(e.capex_subsidy)} €")])
summary_box(SUMMARY_SLOTS["Einnahmepotenziale"], [
    ("Zusatzeinnahmen pro Jahr", f"{de(e.revenue_total)} €"),
    ("je kg Wasserstoff", f"{de(e.revenue_total / e.h2_kg_per_year if e.h2_kg_per_year else 0)} €/kg")])

A, P, O, F, R = "Anlage & Investitionen", "Strombezug & Nebenkosten", "Betrieb (OPEX)", "Finanzierung & Förderungen", "Einnahmepotenziale"
section_sum(A, "Investitionskosten (CAPEX)", capex_pair("EPC", "Balance of Plant", "Gebäude und Tiefbau"))
section_sum(A, "Abwärme", capex_pair("Abwärmesystem"))
section_sum(A, "Sauerstoff", capex_pair("Sauerstoffsystem"))
section_sum(A, "Wasserstoff-Aufbereitung", capex_pair("H2-Aufbereitung"))
section_sum(A, "Peripherie", [("Leistung Peripherie", f"{de(r.power.peripherals_kw, 0)} kW")])
section_sum(A, "Batteriesystem (Kosten)", capex_pair("Batteriesystem") if inp.battery_enabled else [("Kosten", eur(0))])
section_sum(A, "Stacktausch", per_year("Kosten pro Jahr", e.stack_cost_per_year) + [("Tausche", f"{r.stack_replacements}")])
section_sum(A, "Individuelle CAPEX", capex_pair("Individuelle CAPEX"))
section_sum(P, "Preisentwicklung PPA", per_year("PPA-Kosten", pc.cost_pv + pc.cost_wind + pc.cost_baseload))
section_sum(P, "Spotmarkt und Börsenpreise", per_year("Spotmarkt-Kosten", pc.cost_spot))
section_sum(P, "Strombezug nach §7 der 37. BImSchV", per_year("Kosten", pc.cost_s7))
section_sum(P, "Strombezug nach §13k EnWG", per_year("Kosten", pc.cost_13k))
section_sum(O, "Pauschale oder Einzelpositionen", per_year("OPEX gesamt", e.opex_total))
section_sum(O, "Wartung & Instandhaltung", per_year("Kosten", e.opex_maintenance))
section_sum(O, "Personal", per_year("Kosten", e.opex_personnel))
section_sum(O, "Rückstellungen (ohne Stacktausch)", per_year("Kosten", e.opex_provisions))
section_sum(O, "Wasser", per_year("Kosten", e.opex_water))
section_sum(O, "Sonstige OPEX", per_year("Kosten", e.opex_other))
section_sum(F, "Finanzierung", per_year("Kapitalkosten", e.financing_total))
section_sum(F, "CAPEX-Förderung", [("Fördersumme", eur(e.capex_subsidy))])
section_sum(F, "OPEX-Förderung", per_year("Förderung", e.opex_subsidy))
section_sum(F, "Strompreisförderung", per_year("Förderung", pc.power_subsidy))
section_sum(F, "Strompreiskompensation", per_year("Förderung", e.spk))
section_sum(R, "THG-Quote", per_year("Einnahmen", e.revenue_thg))
section_sum(R, "Verkauf von Überschussstrom", per_year("Einnahmen", e.revenue_power_spot + e.revenue_power_ppa))
section_sum(R, "Sauerstoff", per_year("Einnahmen", e.revenue_oxygen))
section_sum(R, "Abwärme", per_year("Einnahmen", e.revenue_heat))
section_sum(R, "Regelenergie", per_year("Einnahmen", e.revenue_balancing))
section_sum(R, "Sonstige Einnahmen", per_year("Einnahmen", e.revenue_other))

# ---------------------------------------------------------------- Cockpit (Ergebnis rechts)
with cockpit_slot:
    st.markdown("### **Ergebnis**")
    k1, k2, k3 = st.columns(3)
    k1.metric("Gestehungskosten", f"{de(e.lcoh_eur_per_kg)} €/kg", help="Wasserstoffgestehungskosten (LCOH2) über die "
              "Projektlaufzeit, inklusive Förderungen, Befreiungen und Zusatzeinnahmen.")
    k2.metric("in ct/kWh", f"{de(e.lcoh_ct_per_kwh)} ct/kWh", help="Bezogen auf den Brennwert von 39,4 kWh/kg.")
    k3.metric("Wasserstoff", f"{de(e.h2_kg_per_year / 1000, 0)} t/a")
    k4, k5, k6 = st.columns(3)
    k4.metric("Anteil grüner Wasserstoff", f"{de(green_share * 100, 1)} %", help=HELP_GREEN)
    k5.metric("Systemauslastung", f"{de(system_util * 100, 1)} %", help="Stromverbrauch des Gesamtsystems bezogen auf "
              "den Dauerbetrieb mit Nennleistung über 8.760 Stunden.")
    k6.metric("Ø Effizienz", f"{de(r.avg_efficiency * 100, 1)} %", help="Mittlerer Wirkungsgrad des Elektrolyseurs über "
              "die Projektlaufzeit (inklusive Degradation).")
    k7, k8, k9 = st.columns(3)
    k7.metric("Volllaststunden", f"{de(r.full_load_hours, 0)} h/a")
    k8.metric("Kapitalkostensatz (WACC)", f"{de(e.wacc * 100, 1)} %")
    k9.metric("Stacktausche", f"{r.stack_replacements}", help=f"Anzahl der Stacktausche in der Projektlaufzeit "
              f"(alle {de(r.stack_interval_years, 1)} Jahre).")
    items = waterfall_items(r, e, "verbraucher", netto=True)
    st.markdown("#### Kostenstruktur")
    st.plotly_chart(cost_structure_figure(items, e.lcoh_eur_per_kg, detail=False, height=430,
                                          subsidy_title="Förderungen", gross_label="Zwischensumme"), width="stretch")
    st.caption("Detaillierte Auswertung im Reiter „Ergebnisse“.")

# ---------------------------------------------------------------- Ergebnisse
with tab_res:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Gestehungskosten", f"{de(e.lcoh_eur_per_kg)} €/kg", help="Wasserstoffgestehungskosten (LCOH2).")
    c2.metric("ct/kWh (Brennwert)", f"{de(e.lcoh_ct_per_kwh)}")
    c3.metric("Wasserstoff", f"{de(e.h2_kg_per_year / 1000, 0)} t/a")
    c4.metric("Anlagenleistung gesamt", f"{de(r.power.total_kw / 1000, 1)} MW")
    c5.metric("CAPEX nach Förderung", f"{de(e.capex_net / 1e6, 1)} Mio. €")
    o1, o2, o3, o4, o5 = st.columns(5)
    o1.metric("Betriebsstunden", f"{de(run_hours, 0)} h/a", help="Stunden, in denen das System Strom verbraucht.")
    o2.metric("davon Volllast", f"{de(full_hours, 0)} h/a")
    o3.metric("davon Teillast", f"{de(part_hours, 0)} h/a")
    o4.metric("Volllaststunden (Ely)", f"{de(r.full_load_hours, 0)} h/a", help="Jahresenergie des Elektrolyseurs geteilt "
              "durch seine Nennleistung.")
    o5.metric("Ø Auslastung (Ely)", f"{de(ely_util * 100, 1)} %")

    st.markdown("### Zusammensetzung der Gestehungskosten")
    ctl1, ctl2 = st.columns(2)
    with ctl1:
        view = st.radio("Stromkosten aufteilen nach", ["Verbrauchern", "Bezugsquellen und Abgaben"], horizontal=True,
                        key="power_view_radio",
                        help="Verbrauchern: Wie viel Stromkosten entfallen auf Elektrolyseur, Peripherie und Verdichter? "
                             "Bezugsquellen und Abgaben: Wie viel entfällt auf PPA, Spotmarkt usw. und auf Netzentgelt, "
                             "Steuern und Umlagen? Die Summe der Stromkosten ist in beiden Fällen gleich.")
    with ctl2:
        mode = st.radio("Darstellung", ["Detailliert (Einzelposten)", "Gestapelt nach Bereichen",
                                        "Strom netto (Befreiungen verrechnet)"], index=2, key="chart_mode",
                        help="Gestapelt: ein Balken je Bereich, farbig nach Einzelposten unterteilt. Detailliert: jeder "
                             "Einzelposten ein eigener Balken. Strom netto: Die Befreiungen von Stromnebenkosten werden "
                             "direkt mit den Stromkosten verrechnet; unter „Förderungen“ stehen nur echte Förderungen.")
    items = waterfall_items(r, e, "verbraucher" if view == "Verbrauchern" else "quelle")
    detail = mode.startswith("Detailliert")
    sub_title = None
    if mode.startswith("Strom netto"):
        items = (waterfall_items(r, e, "verbraucher", netto=True) if view == "Verbrauchern"
                 else net_power_items(items))
        sub_title = "Förderungen"
    fig = cost_structure_figure(items, e.lcoh_eur_per_kg, detail=detail, height=640 if detail else 520,
                                subsidy_title=sub_title, gross_label="Zwischensumme" if sub_title else None)
    st.plotly_chart(fig, width="stretch")
    gross = sum(i.eur_per_kg for i in items if i.block in COST_BLOCK_NAMES)
    gross_text = ("Zwischensumme (ohne Förderungen und Zusatzeinnahmen)" if sub_title
                  else "Gestehungskosten brutto (ohne Förderungen, Befreiungen und Zusatzeinnahmen)")
    st.caption(f"{gross_text}: {de(gross)} €/kg · "
               f"Gestehungskosten: {de(e.lcoh_eur_per_kg)} €/kg")

    st.markdown("### Geordneter Lastverlauf")
    st.plotly_chart(load_duration_figure(r.hourly, r.power), width="stretch")
    st.caption("Jede Linie zeigt die Energie je Stunde, der Größe nach geordnet (höchste Stunde links). Der "
               "Gesamtstrombezug liegt über dem Verbrauch, wenn Strom in die Batterie geladen oder als Überschuss verkauft wird.")

    st.markdown("### Ladezustand der Batterie")
    if inp.battery_enabled and r.power.battery_capacity_kwh > 0:
        st.plotly_chart(battery_soc_figure(r.hourly, r.power), width="stretch")
        st.caption(f"Ladezyklen pro Jahr: {r.battery_cycles}")
    else:
        st.info("Die Batterie ist ausgeschaltet.")

    st.markdown("### Spotmarktpreise")
    st.plotly_chart(spot_price_figure(r.market), width="stretch")
    st.caption(f"Die Linie ist grün, solange der Preis unter der §7-Grenze liegt. Gelb: zwischen der §7-Grenze und Ihrem Maximalpreis "
               f"({de(inp.spot_max_price_eur_per_mwh)} €/MWh). Rot: darüber. Einzelne extreme Preisspitzen sind zugunsten der "
               f"Lesbarkeit abgeschnitten; Sie können im Diagramm hineinzoomen.")

    t1, t2 = st.columns(2)
    with t1:
        st.markdown("### Kosten und Erlöse pro Jahr")
        h2 = e.h2_kg_per_year
        rows = []
        for blk in COST_BLOCK_NAMES:
            rows.append((blk, block_subtotal(items, blk) * h2))
        rows.append(("Gestehungskosten brutto", sum(v for _, v in rows)))
        for blk in (BLOCK_SUBSIDY, BLOCK_REVENUE):
            rows.append((blk, block_subtotal(items, blk) * h2))
        rows.append(("Gestehungskosten", sum(v for n, v in rows if n != "Gestehungskosten brutto")))
        df = pd.DataFrame(rows, columns=["Position", "€ pro Jahr"])
        df["€ pro kg H₂"] = df["€ pro Jahr"] / h2 if h2 else 0.0
        st.dataframe(df.style.format({"€ pro Jahr": lambda v: de(v, 2), "€ pro kg H₂": lambda v: de(v, 2)}),
                     hide_index=True, width="stretch")
        capex_part = e.capex_net / inp.project_lifetime_years / h2 if h2 else 0.0
        st.caption(f"Die Kapitalkosten (Finanzierung) von {de(e.financing_total / h2 if h2 else 0)} €/kg bestehen aus dem "
                   f"CAPEX-Anteil nach Förderung ({de(capex_part)} €/kg, Tilgung über die Laufzeit) und den "
                   f"Zinskosten ({de(block_subtotal(items, BLOCK_INTEREST))} €/kg). Im Diagramm stehen beide getrennt.")
    with t2:
        st.markdown("### Anlage und Betrieb")
        pc = e.power
        kennz = [
            ("Elektrolyseurleistung", f"{de(r.power.ely_kw, 0)} kW"), ("Gesamtleistung System", f"{de(r.power.total_kw, 0)} kW"),
            ("Batteriekapazität", f"{de(r.power.battery_capacity_kwh, 0)} kWh"),
            ("Stromverbrauch gesamt", f"{de(pc.consumption_total_kwh / 1e6, 2)} GWh/a"),
            ("Stromverbrauch Elektrolyseur", f"{de(pc.consumption_ely_kwh / 1e6, 2)} GWh/a"),
            ("Überschussstrom", f"{de(pc.surplus_kwh / 1e6, 2)} GWh/a"),
            ("Mittlerer Wirkungsgrad", f"{de(r.avg_efficiency * 100, 1)} %"),
            ("Stacktausche in der Laufzeit", f"{r.stack_replacements} (alle {de(r.stack_interval_years, 1)} Jahre)"),
            ("Stunden mit §7-Bezug", f"{r.section7_hours}"), ("Stunden mit §13k-Bezug", f"{r.section13k_hours}"),
            ("Ladezyklen Batterie", f"{r.battery_cycles}"),
            ("CAPEX brutto", f"{de(e.capex_gross / 1e6, 2)} Mio. €"),
            ("CAPEX-Förderung", f"{de(e.capex_subsidy / 1e6, 2)} Mio. €"),
            ("Kapitalkostensatz (WACC)", f"{de(e.wacc * 100, 2)} %"),
        ]
        st.dataframe(pd.DataFrame(kennz, columns=["Kennzahl", "Wert"]), hide_index=True, width="stretch")

    st.markdown("### Strombezug im Überblick")
    m = 1000.0
    quellen = [("PPA PV", pc.ppa_pv_kwh, pc.price_pv), ("PPA Wind", pc.ppa_wind_kwh, pc.price_wind),
               ("PPA Grundlast", pc.baseload_kwh, pc.price_baseload), ("§7 (37. BImSchV)", pc.section7_kwh, pc.price_s7),
               ("§13k EnWG", pc.section13k_kwh, pc.price_13k), ("Spotmarkt", pc.spot_kwh, pc.price_spot)]
    tab = pd.DataFrame([(n, q / m, q / pc.total_procurement_kwh * 100 if pc.total_procurement_kwh else 0, p, q / m * p)
                        for n, q, p in quellen],
                       columns=["Quelle", "Menge [MWh/a]", "Anteil [%]", "Preis [€/MWh]", "Kosten [€/a]"])
    st.dataframe(tab.style.format({"Menge [MWh/a]": lambda v: de(v, 0), "Anteil [%]": lambda v: de(v, 1),
                                   "Preis [€/MWh]": lambda v: de(v, 2), "Kosten [€/a]": lambda v: de(v, 0)}),
                 hide_index=True, width="stretch")

    # ---- Download
    st.markdown("### Ergebnisse herunterladen")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame([("Gestehungskosten [€/kg]", e.lcoh_eur_per_kg), ("Gestehungskosten [ct/kWh]", e.lcoh_ct_per_kwh),
                      ("Wasserstoff [kg/a]", e.h2_kg_per_year), ("Volllaststunden [h/a]", r.full_load_hours),
                      ("Gesamtleistung [kW]", r.power.total_kw), ("CAPEX brutto [€]", e.capex_gross),
                      ("CAPEX netto [€]", e.capex_net), ("OPEX [€/a]", e.opex_total), ("Stromkosten [€/a]", e.power_cost),
                      ("Finanzierung [€/a]", e.financing_total), ("Erlöse [€/a]", e.revenue_total)],
                     columns=["Kennzahl", "Wert"]).to_excel(xw, sheet_name="Ergebnis", index=False)
        pd.DataFrame([(i.block, i.label, i.eur_per_kg) for i in items], columns=["Block", "Posten", "€ pro kg H2"]).to_excel(
            xw, sheet_name="Wasserfall", index=False)
        df.to_excel(xw, sheet_name="Kosten und Erlöse", index=False)
        tab.to_excel(xw, sheet_name="Strombezug", index=False)
        pd.DataFrame([(SPEC_BY_KEY[k].label, SPEC_BY_KEY[k].unit, v) for k, v in S.items() if k in SPEC_BY_KEY],
                     columns=["Eingabe", "Einheit", "Wert (Anteile als Dezimalzahl)"]).to_excel(xw, sheet_name="Eingaben", index=False)
        r.hourly.to_excel(xw, sheet_name="Stundenwerte", index=False)
    d1, d2, d3 = st.columns(3)
    d1.download_button("Ergebnisse als Excel (.xlsx)", buf.getvalue(), "ergebnisse_lcoh2.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    d2.download_button("Stundenwerte (.csv)", r.hourly.to_csv(index=False), "stundenwerte_lcoh2.csv", "text/csv",
                       width="stretch")
    d3.download_button("Eingaben (.json)", json.dumps(S, ensure_ascii=False, indent=1, default=float),
                       "eingaben_lcoh2.json", "application/json", width="stretch")


with tab_data:
    render_data_tab(inp)
