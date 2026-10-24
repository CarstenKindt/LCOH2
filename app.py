"""LCOH2-Rechner: Oberfläche.  Start:  streamlit run app.py"""
from __future__ import annotations

import io
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lcoh.economics import compute_economics
from lcoh.help_texts import HELP
from lcoh.input_spec import SPEC_BY_KEY
from lcoh.inputs import Inputs
from lcoh.operation import run_operation
from lcoh.ui_layout import CHOICE_LABELS, COCKPIT, GATES, LEVIES, PAGES, REVENUE_PAGE, VISIBLE
from lcoh.waterfall import (BLOCK_CAPEX, BLOCK_INTEREST, BLOCK_OPEX, BLOCK_POWER, BLOCK_REVENUE, BLOCK_STACK,
                            BLOCK_SUBSIDY, block_subtotal, waterfall_items)
from lcoh.zeitreihen import SERIES_LABELS, load_default_timeseries, parse_series

st.set_page_config(page_title="LCOH2-Rechner", page_icon="💧", layout="wide")
st.markdown("""
<style>
div[data-testid="stVerticalBlockBorderWrapper"] h4 {margin-top: 0; font-size: 1.05rem;}
.block-container {padding-top: 2.2rem;}
</style>""", unsafe_allow_html=True)


def de(x: float, n: int = 2) -> str:
    """Zahl im deutschen Format."""
    return f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- Zustand
if "S" not in st.session_state:
    st.session_state["S"] = Inputs().to_dict()
if "series" not in st.session_state:
    st.session_state["series"] = {}
S: dict = st.session_state["S"]


def reset_widgets() -> None:
    for key in [k for k in st.session_state if k.startswith("w_")]:
        del st.session_state[key]


def to_display(spec, value):
    return value * 100 if spec.kind == "percent" else value


def from_display(spec, value):
    if spec.kind == "percent":
        return value / 100
    if spec.kind == "number" and isinstance(spec.default, int) and not isinstance(spec.default, bool):
        return int(value)
    return value


def default_step(spec) -> float:
    if isinstance(spec.default, int) and not isinstance(spec.default, bool):
        return 1
    d = abs(spec.default) if spec.default else 1.0
    if spec.kind == "percent":
        return 0.5
    return 100.0 if d >= 5000 else 10.0 if d >= 100 else 1.0 if d >= 10 else 0.5 if d >= 1 else 0.1


def field(key: str, label: str | None = None, hide_label: bool = False) -> None:
    """Zeichnet ein Eingabefeld. Der Wert bleibt auch dann erhalten, wenn das Feld ausgeblendet wird."""
    spec = SPEC_BY_KEY[key]
    wk = f"w_{key}"
    unit = {"percent": "%"}.get(spec.kind, spec.unit)
    text = label or (spec.label + (f" [{unit}]" if unit else ""))
    vis = "collapsed" if hide_label else "visible"
    if wk not in st.session_state:
        st.session_state[wk] = to_display(spec, S[key])
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
                               label_visibility=vis)
    else:
        step = default_step(spec)
        minv = to_display(spec, spec.minimum) if spec.minimum is not None else None
        maxv = to_display(spec, spec.maximum) if spec.maximum is not None else None
        is_int = isinstance(spec.default, int) and not isinstance(spec.default, bool)
        if is_int:
            fmt_str = "%d"
        else:
            fmt_str = "%g"
        if is_int:
            minv = int(minv) if minv is not None else None
            maxv = int(maxv) if maxv is not None else None
        else:
            minv = float(minv) if minv is not None else None
            maxv = float(maxv) if maxv is not None else None
            st.session_state[wk] = float(st.session_state[wk])
            step = float(step)
        val = st.number_input(text, key=wk, min_value=minv, max_value=maxv, step=step, format=fmt_str,
                              help=helptext, label_visibility=vis)
    S[key] = from_display(spec, val)


def visible(key: str) -> bool:
    rule = VISIBLE.get(key)
    return True if rule is None else bool(rule(S))


def render_section(title: str, gate: str | None, keys: list[str], skip: set[str] | None = None) -> None:
    keys = [k for k in keys if not skip or k not in skip]
    with st.container(border=True):
        st.markdown(f"#### {title}")
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
    st.markdown("### 💧 LCOH2-Rechner")
    st.caption("Wasserstoffgestehungskosten für Elektrolyseprojekte")
    st.markdown("**Eingaben speichern und laden**")
    upload = st.file_uploader("Gespeicherte Eingaben laden (.json)", type="json", key="up_inputs")
    if upload is not None and st.session_state.get("_loaded") != (upload.name, upload.size):
        try:
            loaded = Inputs.from_dict(json.load(upload)).to_dict()
            S.update(loaded)
            reset_widgets()
            st.session_state["_loaded"] = (upload.name, upload.size)
            st.rerun()
        except Exception:
            st.error("Die Datei konnte nicht gelesen werden. Bitte eine mit diesem Tool gespeicherte Datei verwenden.")
    if st.button("Auf Standardwerte zurücksetzen", width="stretch"):
        S.update(Inputs().to_dict())
        st.session_state["series"] = {}
        st.session_state.pop("_loaded", None)
        reset_widgets()
        st.rerun()

tab_cockpit, tab_inputs, tab_rev, tab_res, tab_data = st.tabs(
    ["🎛️ Cockpit", "⚙️ Eingaben", "💶 Einnahmepotenziale", "📊 Ergebnisse", "📁 Daten"])

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
    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("### Elektrolysesystem")
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
    cockpit_slot = right.container()

# ---------------------------------------------------------------- Eingabeseiten
with tab_inputs:
    sub = st.tabs([name for name, _ in PAGES])
    cockpit_keys = {k for _, _, ks in COCKPIT for k in ks}
    for tab, (name, sections) in zip(sub, PAGES):
        with tab:
            cols = st.columns(2)
            i = 0
            for title, gate, keys in sections:
                with cols[i % 2]:
                    render_section(title, gate, keys, skip=cockpit_keys)
                i += 1
            if name == "Strombezug & Nebenkosten":
                render_levies()

with tab_rev:
    st.markdown("### Einnahmepotenziale")
    st.caption("Zusätzliche Erlöse, die die Gestehungskosten senken.")
    cols = st.columns(2)
    for i, (title, gate, keys) in enumerate(REVENUE_PAGE):
        with cols[i % 2]:
            render_section(title, gate, keys)

# ---------------------------------------------------------------- Prüfung und Rechnung
errors = Inputs.from_dict(S).validate()
if errors:
    with tab_cockpit:
        right.error("Bitte Eingaben prüfen:\n\n" + "\n".join(f"- {m}" for m in errors))
    st.stop()

series_json = json.dumps(st.session_state["series"])
r, e = rechnen(json.dumps(S, sort_keys=True, default=float), series_json)
inp = r.inputs

with st.sidebar:
    st.divider()
    st.metric("Gestehungskosten", f"{de(e.lcoh_eur_per_kg)} €/kg")
    st.caption(f"{de(e.lcoh_ct_per_kwh)} ct/kWh (Brennwert) · {de(e.h2_kg_per_year / 1000, 0)} t Wasserstoff pro Jahr")
    st.download_button("Eingaben speichern (.json)", json.dumps(S, ensure_ascii=False, indent=1, default=float),
                       "eingaben_lcoh2.json", "application/json", width="stretch")

# ---------------------------------------------------------------- Cockpit (Ergebnis rechts)
with cockpit_slot:
    st.markdown("### Ergebnis")
    k1, k2 = st.columns(2)
    k1.metric("Gestehungskosten", f"{de(e.lcoh_eur_per_kg)} €/kg", help="Wasserstoffgestehungskosten über die Projektlaufzeit, "
              "inklusive Förderungen, Befreiungen und Zusatzeinnahmen.")
    k2.metric("in ct/kWh", f"{de(e.lcoh_ct_per_kwh)} ct/kWh", help="Bezogen auf den Brennwert von 39,4 kWh/kg.")
    k3, k4 = st.columns(2)
    k3.metric("Wasserstoff", f"{de(e.h2_kg_per_year / 1000, 0)} t/a")
    k4.metric("Volllaststunden", f"{de(r.full_load_hours, 0)} h/a")
    items = waterfall_items(r, e)
    parts = {
        "CAPEX": block_subtotal(items, BLOCK_CAPEX), "OPEX": block_subtotal(items, BLOCK_OPEX),
        "Stacktausch": block_subtotal(items, BLOCK_STACK), "Strom": block_subtotal(items, BLOCK_POWER),
        "Zinsen": block_subtotal(items, BLOCK_INTEREST),
        "Förderungen & Befreiungen": block_subtotal(items, BLOCK_SUBSIDY),
        "Zusatzeinnahmen": block_subtotal(items, BLOCK_REVENUE)}
    st.caption("Kostenstruktur in €/kg (Kosten positiv, Förderungen/Befreiungen/Einnahmen negativ)")
    fig = go.Figure(go.Waterfall(
        x=list(parts) + ["Gestehungskosten"], y=list(parts.values()) + [0],
        measure=["relative"] * len(parts) + ["total"],
        increasing={"marker": {"color": "#d1495b"}}, decreasing={"marker": {"color": "#2e8b57"}},
        totals={"marker": {"color": "#1f4e79"}}, connector={"line": {"color": "#999"}},
        text=[de(v) for v in parts.values()] + [de(e.lcoh_eur_per_kg)], textposition="outside"))
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
                      yaxis_title="€ pro kg H₂")
    st.plotly_chart(fig, width="stretch")
    st.caption("Detaillierte Auswertung im Reiter „Ergebnisse“.")

# ---------------------------------------------------------------- Ergebnisse
with tab_res:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Gestehungskosten", f"{de(e.lcoh_eur_per_kg)} €/kg")
    c2.metric("ct/kWh (Brennwert)", f"{de(e.lcoh_ct_per_kwh)}")
    c3.metric("Wasserstoff", f"{de(e.h2_kg_per_year / 1000, 0)} t/a")
    c4.metric("Anlagenleistung gesamt", f"{de(r.power.total_kw / 1000, 1)} MW")
    c5.metric("CAPEX nach Förderung", f"{de(e.capex_net / 1e6, 1)} Mio. €")

    st.markdown("### Zusammensetzung der Gestehungskosten")
    view = st.radio("Stromkosten gliedern nach", ["Bezugsquelle und Abgaben", "Verbrauchern"], horizontal=True,
                    key="power_view_radio")
    items = waterfall_items(r, e, "verbraucher" if view == "Verbrauchern" else "quelle")
    detail = st.toggle("Detailansicht (alle Einzelposten)", value=True, key="detail_toggle")
    cost_blocks = [BLOCK_CAPEX, BLOCK_OPEX, BLOCK_STACK, BLOCK_POWER, BLOCK_INTEREST]
    labels, values, measures = [], [], []
    def add_block(block: str) -> None:
        if detail:
            for it in [i for i in items if i.block == block and abs(i.eur_per_kg) > 1e-9]:
                labels.append(f"{block}: {it.label}" if block in (BLOCK_POWER,) else it.label)
                values.append(it.eur_per_kg)
                measures.append("relative")
        else:
            labels.append(block)
            values.append(block_subtotal(items, block))
            measures.append("relative")
    for b in cost_blocks:
        add_block(b)
    labels.append("Zwischenergebnis")
    values.append(0); measures.append("total")
    for b in (BLOCK_SUBSIDY, BLOCK_REVENUE):
        add_block(b)
    labels.append("Gestehungskosten")
    values.append(0); measures.append("total")
    zw = sum(i.eur_per_kg for i in items if i.block in cost_blocks)
    fig = go.Figure(go.Waterfall(
        x=labels, y=values, measure=measures,
        increasing={"marker": {"color": "#d1495b"}}, decreasing={"marker": {"color": "#2e8b57"}},
        totals={"marker": {"color": "#1f4e79"}}, connector={"line": {"color": "#aaa"}},
        text=[de(v) if m == "relative" else "" for v, m in zip(values, measures)], textposition="outside"))
    fig.add_annotation(x="Zwischenergebnis", y=zw, text=f"<b>{de(zw)}</b>", showarrow=False, yshift=12)
    fig.add_annotation(x="Gestehungskosten", y=e.lcoh_eur_per_kg, text=f"<b>{de(e.lcoh_eur_per_kg)}</b>",
                       showarrow=False, yshift=12)
    fig.update_layout(height=620 if detail else 480, margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
                      yaxis_title="€ pro kg H₂", xaxis_tickangle=-55)
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Zwischenergebnis ohne Förderungen, Befreiungen und Zusatzeinnahmen: {de(zw)} €/kg · "
               f"Gestehungskosten: {de(e.lcoh_eur_per_kg)} €/kg")

    st.markdown("### Geordneter Lastverlauf")
    util = np.sort(r.hourly["consumption_kwh"].to_numpy() / r.power.total_kw * 100)[::-1]
    fl = go.Figure(go.Scatter(x=np.arange(1, len(util) + 1), y=util, fill="tozeroy", line=dict(color="#1f4e79"),
                              hovertemplate="Stunde %{x}: %{y:.1f} %<extra></extra>"))
    fl.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0), xaxis_title="Stunden pro Jahr (nach Auslastung geordnet)",
                     yaxis_title="Auslastung des Gesamtsystems [%]", yaxis_range=[0, 105])
    st.plotly_chart(fl, width="stretch")
    run_hours = int((r.hourly["consumption_kwh"] > 0).sum())
    st.caption(f"Betriebsstunden: {de(run_hours, 0)} h · davon Volllast: {de(int((util >= 99.999).sum()), 0)} h · "
               f"Mittlere Auslastung des Elektrolyseurs: {de(r.full_load_hours / 87.6, 1)} %")

    t1, t2 = st.columns(2)
    with t1:
        st.markdown("### Kosten und Erlöse pro Jahr")
        rows = [("Kapitalkosten (Finanzierung)", e.financing_total), ("Betriebskosten (OPEX)", e.opex_total),
                ("Stacktausch", e.stack_cost_per_year), ("Stromkosten", e.power_cost),
                ("Strompreiskompensation", -e.spk), ("THG-Quote", -e.revenue_thg),
                ("Stromverkauf", -(e.revenue_power_spot + e.revenue_power_ppa)), ("Sauerstoff", -e.revenue_oxygen),
                ("Abwärme", -e.revenue_heat), ("Regelenergie", -e.revenue_balancing), ("Sonstige", -e.revenue_other)]
        df = pd.DataFrame(rows, columns=["Position", "€ pro Jahr"])
        df["€ pro kg H₂"] = df["€ pro Jahr"] / e.h2_kg_per_year if e.h2_kg_per_year else 0.0
        df.loc[len(df)] = ["Summe (Gestehungskosten)", df["€ pro Jahr"].sum(), df["€ pro kg H₂"].sum()]
        st.dataframe(df.style.format({"€ pro Jahr": lambda v: de(v, 0), "€ pro kg H₂": lambda v: de(v, 3)}),
                     hide_index=True, width="stretch")
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

# ---------------------------------------------------------------- Daten
with tab_data:
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
