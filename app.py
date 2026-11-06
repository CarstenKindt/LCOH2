"""LCOH₂-Rechner: Oberfläche.  Start:  streamlit run app.py"""
from __future__ import annotations

import base64
import html
import io
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from lcoh.economics import compute_economics
from lcoh.help_texts import HELP
from lcoh.tool_defaults import tool_defaults
from lcoh.input_spec import SPEC_BY_KEY
from lcoh.inputs import Inputs
from lcoh.operation import run_operation
from lcoh.system import system_power
from lcoh.sensitivity import sensitivity
from lcoh.charts import COST_BLOCKS as COST_BLOCK_NAMES, battery_soc_figure, cost_structure_figure, load_duration_figure, sensitivity_figure, spot_price_figure
from lcoh.ui_layout import (rename_label, CHOICE_LABELS, COCKPIT, FINE_STEP, GATES, LABEL_OVERRIDES, LEVIES, PAGES, REVENUE_PAGE,
                            VISIBLE)
from lcoh.waterfall import (BLOCK_CAPEX, BLOCK_INTEREST, BLOCK_OPEX, BLOCK_POWER, BLOCK_REVENUE, BLOCK_STACK,
                            BLOCK_SUBSIDY, block_subtotal, net_power_items, waterfall_items)
from lcoh.zeitreihen import SERIES_KIND, SERIES_LABELS, build_timeseries, load_default_timeseries, read_series, to_grid

ASSETS = Path(__file__).resolve().parent / "assets"


@st.cache_data
def _logo_uri(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


@st.cache_data
def _logo_cropped_uri(name: str) -> str:
    """Logo ohne weiße Ränder (für die Kopfzeile), damit es bei kleiner Höhe größer wirkt."""
    from PIL import Image, ImageChops
    im = Image.open(ASSETS / name).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(bg, im).convert("RGB")
    box = ImageChops.difference(flat, Image.new("RGB", im.size, (255, 255, 255))).point(lambda v: 255 if v > 12 else 0).getbbox()
    if box:
        pad = 6
        box = (max(box[0] - pad, 0), max(box[1] - pad, 0), min(box[2] + pad, im.width), min(box[3] + pad, im.height))
        im = flat.crop(box)
    else:
        im = flat
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def logo(name: str, width: int) -> None:
    """Zeigt ein Logo in Originalauflösung (die Anzeigebreite wird per CSS gesetzt, damit es auf hochauflösenden Bildschirmen scharf bleibt)."""
    st.markdown(f'<img src="{_logo_uri(name)}" style="width:{width}px;max-width:100%;height:auto;display:block;" alt="Logo">',
                unsafe_allow_html=True)
st.set_page_config(page_title="Wasserstoffkostenrechner", page_icon="💧", layout="wide")
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
.kpi {margin-bottom: .6rem;}
.kpi .kl {font-size: .85rem; color: #555; line-height: 1.2;}
.kpi .kq {display: inline-block; width: 1.05em; height: 1.05em; line-height: 1em; margin-left: .35em; border: 1.5px solid #808495; border-radius: 50%; color: #808495; font-size: .72rem; font-weight: 600; text-align: center; cursor: help; vertical-align: 1px;}
.kpi .kv {font-size: 1.6rem; line-height: 1.3; white-space: nowrap;}
.kpi .ku {font-size: .8rem; color: #666; margin-left: .2rem;}
.st-key-cockpit_out .kpi {text-align: center;}
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


DEFAULTS = tool_defaults()
SOFT = {"Strompreisförderung": "Strompreis&shy;förderung",
        "Investitionskosten": "Investitions&shy;kosten", "Überschussstrom": "Überschuss&shy;strom",
        "Stromnebenkosten": "Stromneben&shy;kosten", "Wasserstoff-Aufbereitung": "Wasserstoff-&#8203;Aufbereitung",
        "Instandhaltung": "Instand&shy;haltung", "Rückstellungen": "Rück&shy;stellungen"}


def soft(title: str) -> str:
    for k, v in SOFT.items():
        title = title.replace(k, v)
    return title


def fill_defaults(keys: list[str]) -> None:
    for k in keys:
        if S.get(k) is None and DEFAULTS.get(k) is not None:
            S[k] = DEFAULTS[k]
            st.session_state.pop(f"w_{k}", None)
            st.session_state.get("_ferr", {}).pop(k, None)


def fill_button(keys: list[str], ident: str) -> None:
    """Schaltfläche, die nur die leeren Felder dieses Bereichs mit Standardwerten füllt."""
    if any(S.get(k) is None and k in BLANK_KEYS and visible(k) for k in keys):
        st.button("Leere Felder mit Standardwerten füllen", key=f"fill_{ident}", on_click=fill_defaults,
                  args=([k for k in keys if visible(k)],), help="Übernimmt die Standardwerte nur für die noch leeren "
                  "Felder dieses Bereichs. Bereits eingegebene Werte bleiben unverändert.")


TOGGLE_KEYS = {"waste_heat_enabled", "oxygen_enabled", "thg_enabled", "power_sale_enabled", "balancing_enabled",
               "other_revenue_enabled"}
START_OFF = ["battery_enabled", "battery_optimize", "ppa_baseload_enabled", "ppa_pv_enabled", "ppa_wind_enabled", "spot_enabled", "section7_enabled",
             "section13k_enabled"] + sorted(TOGGLE_KEYS)


def empty_state() -> dict:
    """Leerer Startzustand: Zahlenfelder ohne Wert; Schalter und Auswahlfelder stehen auf ihren Standardwerten."""
    d = dict(DEFAULTS)
    for k in BLANK_KEYS:
        if k != "sensitivity_step":
            d[k] = None
    for k in START_OFF:
        d[k] = False
    return d


if "S" not in st.session_state:
    st.session_state["S"] = empty_state()
if "series" not in st.session_state:
    st.session_state["series"] = {}       # eigene Reihen: Name -> Rate je Viertelstunde (35.040 Werte)
if "series_info" not in st.session_state:
    st.session_state["series_info"] = {}  # Name -> (ursprüngliche Auflösung, Hinweis, Dateiname)
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
    base = label or LABEL_OVERRIDES.get(key) or rename_label(spec.label)
    text = label or (base + (f" [{unit}]" if unit else ""))
    vis = "collapsed" if hide_label else "visible"
    use_text = uses_text_field(spec)
    dec = decimals_of(spec)
    if wk not in st.session_state:
        v0 = to_display(spec, S[key])
        st.session_state[wk] = fmt_de(v0, dec) if use_text else v0
    helptext = rename_label(HELP.get(key))
    if spec.kind == "bool":
        val = st.toggle(text, key=wk, help=helptext, label_visibility=vis)
    elif spec.kind == "choice":
        fmt = CHOICE_LABELS.get(key, {}).get
        if len(spec.choices) <= 3 and not isinstance(spec.choices[0], int):
            val = st.radio(text, spec.choices, key=wk, help=helptext, horizontal=True,
                           format_func=lambda x: fmt(x, x), label_visibility=vis)
        else:
            val = st.selectbox(text, spec.choices, key=wk, help=helptext, format_func=lambda x: fmt(x, str(x)),
                               label_visibility=vis, index=None, placeholder="Bitte wählen")
    elif use_text:
        dv = DEFAULTS.get(key)
        ph = f"Standard: {fmt_de(to_display(spec, dv), dec)}" if isinstance(dv, (int, float)) and not isinstance(dv, bool) else None
        st.text_input(text, key=wk, help=helptext, on_change=commit_text, args=(key,), label_visibility=vis,
                      placeholder=ph)
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
    own = keys[0] if keys and keys[0] in TOGGLE_KEYS else None
    rest = keys[1:] if own else keys
    with st.container(border=True):
        if own:
            c0, h1, h2 = st.columns([0.2, 1.0, 1.0], vertical_alignment="center")
            with c0:
                field(own, hide_label=True)
            h1.markdown(f"#### {soft(title)}")
        else:
            h1, h2 = st.columns([1.5, 1.0])
            h1.markdown(f"#### {soft(title)}")
        SECTION_SLOTS[f"{scope}|{title}"] = h2.container()
        if own:
            on = bool(S[own])
        elif gate is not None:
            on = GATES[gate](S) if gate in GATES else bool(S[gate])
            if not on:
                st.caption("Dieser Bereich ist ausgeschaltet. Der Schalter steht im Cockpit bzw. in einem anderen Bereich.")
        else:
            on = True
        if not on:
            return
        with st.expander("Eingaben anzeigen", expanded=False):
            fill_button(rest, f"{scope}_{title}")
            for key in rest:
                if visible(key):
                    field(key)


def render_levies() -> None:
    with st.container(border=True):
        st.markdown("#### Stromnebenkosten und Befreiungen")
        fill_button([f"levy_{sd}_{n}_ct_per_kwh" for sd in ("ely", "rest") for n, _ in LEVIES]
                    + ["demand_charge_ely_eur_per_kw_month", "demand_charge_rest_eur_per_kw_month"], "levies")
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
STEPS = 4          # Die Berechnung läuft immer in Viertelstunden (35.040 Schritte), egal wie die Daten aufgelöst sind
DT = 1.0 / STEPS


@st.cache_data(show_spinner="Berechnung läuft ...", max_entries=8)
def rechnen(inputs_json: str, series_json: str, steps: int):
    inp = Inputs.from_dict(json.loads(inputs_json))
    ts = build_timeseries(json.loads(series_json), steps)
    r = run_operation(inp, ts, steps_per_hour=steps)
    return r, compute_economics(r)


# ---------------------------------------------------------------- Seitenleiste (Laden/Speichern)
with st.sidebar:
    logo("logo_hs_flensburg.png", 190)
    st.divider()
    st.markdown("**Eingaben speichern und laden**")
    upload = st.file_uploader("Gespeicherte Eingaben laden (.json)", type="json", key="up_inputs")
    if upload is not None and st.session_state.get("_loaded") != (upload.name, upload.size):
        try:
            raw = json.load(upload)
            filled = {k: v for k, v in raw.items() if v is not None}
            if "ppa_pv_enabled" not in raw and "ppa_pap_enabled" in raw:  # ältere Dateien: ein gemeinsamer Schalter
                filled["ppa_pv_enabled"] = filled["ppa_wind_enabled"] = bool(raw["ppa_pap_enabled"])
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
        S.update(DEFAULTS)
        st.session_state.pop("_loaded", None)
        reset_widgets()
        st.rerun()
    if st.button("Alle Felder leeren", width="stretch"):
        S.update(empty_state())
        st.session_state.pop("_loaded", None)
        reset_widgets()
        st.rerun()

title_col, logo_col = st.columns([3, 2], vertical_alignment="center")
title_col.markdown("# Wasserstoffkostenrechner")
logo_col.markdown(
    '<div style="display:flex;justify-content:flex-end;align-items:center;gap:1.5rem;">'
    f'<img src="{_logo_cropped_uri("logo_nrl.png")}" style="height:64px;width:auto;" alt="Norddeutsches Reallabor">'
    f'<img src="{_logo_cropped_uri("logo_bmwe.png")}" style="height:84px;width:auto;" alt="Gefördert durch das Bundesministerium für Wirtschaft und Energie"></div>',
    unsafe_allow_html=True)
st.caption("Was kostet ein Kilogramm grüner Wasserstoff aus Ihrem Elektrolyseprojekt?")
tab_cockpit, tab_inputs, tab_rev, tab_data, tab_res = st.tabs(
    ["Cockpit", "Eingaben", "Einnahmepotenziale", "Daten", "Ergebnisse"])

def data_tab_button() -> None:
    """Schaltfläche, die zum Reiter „Daten“ wechselt (Streamlit kennt dafür keine eigene Funktion)."""
    page = """<style>body{margin:0}
    button{width:100%;box-sizing:border-box;padding:.45rem .75rem;border:1px solid rgba(49,51,63,.2);border-radius:.5rem;
    background:#fff;color:#31333f;font-size:15px;cursor:pointer}
    button:hover{border-color:#1f4e79;color:#1f4e79}</style>
    <button id="b">Zeitreihen im Reiter „Daten“ ansehen oder hochladen →</button><script>
    const P = window.parent.document;
    document.getElementById('b').style.fontFamily = getComputedStyle(P.body).fontFamily;
    document.getElementById('b').addEventListener('click', () => {
      const t = [...P.querySelectorAll('[data-testid="stTab"]')].find(e => e.innerText.trim() === 'Daten');
      if (t) { t.click(); P.defaultView.scrollTo({top: 0, behavior: 'smooth'}); }
    });
    </script>"""
    if hasattr(st, "iframe"):
        st.iframe(page, height=46)
    else:
        components.html(page, height=46)


# ---------------------------------------------------------------- Cockpit (Eingaben links)
def row(keys: list[str]) -> None:
    cols = st.columns(len(keys), vertical_alignment="bottom")  # Eingabefelder bündig, auch bei mehrzeiligen Beschriftungen
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
                fill_button(["electrolyzer_power_kw", "capex_electrolyzer_eur_per_kw", "electrolyzer_efficiency",
                             "commissioning_year", "project_lifetime_years", "min_part_load"], "cockpit_ely")
            with st.container(border=True):
                bc0, bc1 = st.columns([0.14, 1.0], vertical_alignment="center")
                with bc0:
                    field("battery_enabled", hide_label=True)
                bc1.markdown("#### Batterie")
                if S["battery_enabled"]:
                    row(["battery_capacity_hours", "battery_input_power_kw"])
                    row(["battery_optimize", "battery_efficiency"])
            with st.container(border=True):
                st.markdown("#### Strombezug")
                st.caption("Grundlast-PPA: konstanter Bezug. Pay-as-Produced-PPAs (PPA 1 und PPA 2): Bezug folgt dem jeweiligen Erzeugungsprofil.")
                row(["ppa_baseload_enabled", "ppa_baseload_kw", "ppa_baseload_price_eur_per_mwh"])
                row(["ppa_pv_enabled", "ppa_pv_kw", "ppa_pv_price_eur_per_mwh"])
                row(["ppa_wind_enabled", "ppa_wind_kw", "ppa_wind_price_eur_per_mwh"])
                if S.get("ppa_pv_enabled") or S.get("ppa_wind_enabled"):
                    st.caption("Die Erzeugungsprofile der PPAs lassen sich im Reiter „Daten“ durch eigene Zeitreihen ersetzen.")
                    data_tab_button()
                st.caption("Weitere Bezugsquellen (Details unter „Eingaben“, Reiter „Strombezug & Nebenkosten“):")
                row(["section7_enabled"])
                row(["section13k_enabled"])
                row(["spot_enabled"])
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
    m = re.match(r"levy_(ely|rest)_(\w+)_ct_per_kwh$", key) or re.match(r"demand_charge_(ely|rest)()_eur_per_kw_month$", key)
    if m:
        ex = f"levy_{m.group(1)}_{m.group(2)}_exempt" if m.group(2) else f"demand_charge_{m.group(1)}_exempt"
        if S.get(ex):
            return False
    gate = GATE_OF.get(key)
    if gate is not None and not (GATES[gate](S) if gate in GATES else bool(S[gate])):
        return False
    return visible(key)


defaults_dict = DEFAULTS
shown_keys = set(GATE_OF) | {k for _, _, ks in COCKPIT for k in ks} | {f"levy_{sd}_{n}_ct_per_kwh" for sd in ("ely", "rest")
                                                                      for n, _ in LEVIES}
shown_keys |= {"demand_charge_ely_eur_per_kw_month", "demand_charge_rest_eur_per_kw_month"}
# Felder mit Standardwert 0 sind freiwillig; ein leeres Feld zählt dort als 0
missing = [k for k in BLANK_KEYS if S[k] is None and k in shown_keys and defaults_dict[k] not in (0, 0.0)
           and is_active(k)]
effective = {k: (defaults_dict[k] if v is None else v) for k, v in S.items()}
effective["ppa_pap_enabled"] = bool(S["ppa_pv_enabled"] or S["ppa_wind_enabled"])
for _k in list(effective):  # befreite Abgaben ohne Wert: keine Rechnung mit einem Standardwert
    if S[_k] is None and BLANK_KEYS.count(_k) and not is_active(_k) and (_k.startswith("levy_") or _k.startswith("demand_charge_")):
        effective[_k] = 0.0
inp_eff = Inputs.from_dict(effective)
errors = inp_eff.validate()
if inp_eff.battery_enabled:
    _sys_kw = system_power(inp_eff, inp_eff.electrolyzer_efficiency).total_kw
    if inp_eff.battery_input_power_kw <= _sys_kw:
        errors = errors + [f"Batterie: Die Anschlussleistung gesamt ({de(inp_eff.battery_input_power_kw, 0)} kW) muss größer sein als "
                           f"die Systemleistung der Anlage (ca. {de(_sys_kw, 0)} kW). Nur die Differenz steht zum Laden der Batterie "
                           f"zur Verfügung; sonst kann die Batterie nicht geladen werden. Beispiel: {de(_sys_kw, 0)} kW Systemleistung "
                           f"+ 5.000 kW Batterieladung = {de(_sys_kw + 5000, 0)} kW. Bitte den Wert erhöhen oder die Batterie ausschalten."]
if not any(S[k] for k in ("ppa_baseload_enabled", "ppa_pv_enabled", "ppa_wind_enabled", "section7_enabled", "section13k_enabled", "spot_enabled")):
    errors = errors + ["Bitte mindestens eine Strombezugsquelle einschalten (PPA, §7, §13k oder Spotmarkt)."]


def locate(key: str) -> tuple[str, str | None, str]:
    """Reiter, Unterreiter und Bereich eines Eingabefelds (für die Sprungmarken bei fehlenden Angaben)."""
    cockpit_keys_ = {k for _, _, ks in COCKPIT for k in ks}
    if key in cockpit_keys_:
        return "Cockpit", None, ""
    for name, sections in PAGES:
        for title, _, ks in sections:
            if key in ks:
                return "Eingaben", name, title
    for title, _, ks in REVENUE_PAGE:
        if key in ks:
            return "Einnahmepotenziale", None, title
    return "Eingaben", "Strombezug & Nebenkosten", "Stromnebenkosten und Befreiungen"


def missing_links(keys: list[str]) -> None:
    """Liste fehlender Eingaben; ein Klick öffnet den Reiter und Bereich und springt zum Feld."""
    items = []
    for k in keys:
        tab, sub, area = locate(k)
        label = rename_label(SPEC_BY_KEY[k].label)
        ort = " › ".join(x for x in (tab, sub, area) if x)
        items.append(f'<li><a href="#" data-k="w_{k}" data-t="{html.escape(tab)}" data-s="{html.escape(sub or "")}">'
                     f'{html.escape(label)}</a> <span>· {html.escape(ort)}</span></li>')
    page = """<style>body{margin:0;color:#31333f;font-size:15px;line-height:1.35}
    ul{margin:0;padding-left:20px}li{margin:3px 0}
    a{color:#31333f;text-decoration:none;border-bottom:1px dotted #1f4e79;cursor:pointer;font-weight:400}
    a:hover{color:#1f4e79;border-bottom:1px solid #1f4e79}
    span{color:#808495;font-size:13px}</style><ul>""" + "".join(items) + """</ul><script>
    const P = window.parent.document;
    document.body.style.fontFamily = getComputedStyle(P.body).fontFamily;
    const wait = ms => new Promise(r => setTimeout(r, ms));
    async function tabTo(name) {
      const t = [...P.querySelectorAll('[data-testid="stTab"]')].find(e => e.innerText.trim() === name);
      if (t) { t.click(); await wait(350); }
    }
    document.querySelectorAll('a').forEach(a => a.addEventListener('click', async ev => {
      ev.preventDefault();
      await tabTo(a.dataset.t); if (a.dataset.s) await tabTo(a.dataset.s);
      const el = P.querySelector('.st-key-' + a.dataset.k);
      if (!el) return;
      let d = el.closest('details'), opened = false;
      while (d) {
        if (!d.open) { const sm = d.querySelector('summary'); if (sm) { sm.click(); opened = true; } }
        d = d.parentElement.closest('details');
      }
      await wait(opened ? 600 : 100);
      el.scrollIntoView({block: 'center', behavior: 'smooth'});
      const inp = el.querySelector('input, textarea');
      if (inp) inp.focus({preventScroll: true});
      el.style.transition = 'box-shadow .3s'; el.style.boxShadow = '0 0 0 3px #f0a500';
      setTimeout(() => { el.style.boxShadow = ''; }, 2500);
    }));
    </script>"""
    h = min(28 * len(keys) + 12, 420)
    if hasattr(st, "iframe"):
        st.iframe(page, height=h)
    else:
        components.html(page, height=h, scrolling=True)


def kmetric(col, label: str, value: str, unit: str = "", help: str | None = None) -> None:
    """Kennzahl mit kleinerer Einheit hinter dem Wert."""
    tip = f' title="{html.escape(help, quote=True)}"' if help else ""
    u = f'<span class="ku">{html.escape(unit)}</span>' if unit else ""
    col.markdown(f'<div class="kpi" data-kpi="{html.escape(label)}" data-v="{html.escape((value + " " + unit).strip())}"{tip}>'
                 f'<div class="kl">{html.escape(label)}{'<span class="kq">?</span>' if help else ""}</div>'
                 f'<div class="kv">{html.escape(value)}{u}</div></div>', unsafe_allow_html=True)


def footer() -> None:
    st.divider()
    st.caption("Der Wasserstoffkostenrechner liefert eine Abschätzung auf Basis der eingegebenen Annahmen und der "
               "hinterlegten Beispiel-Zeitreihen. Die Ergebnisse ersetzen keine Wirtschaftlichkeitsprüfung oder "
               "Genehmigungsplanung und erfolgen ohne Gewähr. Entwickelt an der Hochschule Flensburg im Norddeutschen Reallabor.")


SERIES_HELP = {
    "pv_kwh_per_kw": (
        "Stündliches Erzeugungsprofil der Anlage hinter PPA 1, angegeben als Erzeugung je installiertem kW und Zeitintervall (Stunde oder Viertelstunde; z. B. Photovoltaik). "
        "Das Tool multipliziert es mit der installierten Leistung von PPA 1; daraus ergibt sich der stündliche Strombezug. "
        "Hinterlegt ist ein Beispielprofil."),
    "wind_kwh_per_kw": (
        "Stündliches Erzeugungsprofil der Anlage hinter PPA 2, angegeben als Erzeugung je installiertem kW und Zeitintervall (Stunde oder Viertelstunde; z. B. Windkraft). "
        "Das Tool multipliziert es mit der installierten Leistung von PPA 2; daraus ergibt sich der stündliche Strombezug. "
        "Hinterlegt ist ein Beispielprofil."),
    "day_ahead": (
        "Börsenstrompreis (Day-Ahead) je Stunde bzw. Viertelstunde. Er bestimmt den Preis beim Strombezug am Spotmarkt und nach §7 der 37. BImSchV "
        "sowie den Erlös beim Verkauf von Überschussstrom (negative Preise werden dort mit 0 angesetzt). Eine hochgeladene Reihe "
        "ersetzt die hinterlegte Preisreihe (Standard: Preise des Jahres 2024)."),
    "co2_eur_per_t": (
        "CO₂-Preis (Emissionshandel) je Stunde bzw. Viertelstunde. Er legt die Preisgrenze für den Strombezug nach §7 fest: das 0,36-Fache des "
        "CO₂-Preises, mindestens 20 €/MWh, höchstens der maximale Nachfragepreis. Wirkt nur, wenn §7 eingeschaltet ist und als Quelle "
        "„Jahresdaten“ gewählt ist."),
    "section13k_kwh": (
        "Energiemenge je Zeitintervall (Stunde oder Viertelstunde), die im Netz sonst abgeregelt würde und für „Nutzen statt Abregeln“ (§13k EnWG) bezogen werden "
        "kann. Sie begrenzt den Bezug nach §13k je Stunde. Wirkt nur, wenn §13k eingeschaltet ist."),
}


SERIES_UNITS = {"pv_kwh_per_kw": ("kWh/kW je h", "kWh/kW"), "wind_kwh_per_kw": ("kWh/kW je h", "kWh/kW"),
                "day_ahead": ("€/MWh", ""), "co2_eur_per_t": ("€/t", ""), "section13k_kwh": ("kWh je h", "kWh")}


def series_download(name: str, rate_q: np.ndarray | None, res: str, default_col: str, defaults) -> str:
    """CSV-Text der aktuellen Reihe in ihrer ursprünglichen Auflösung (Energie je Intervall, Preise unverändert)."""
    if rate_q is None:
        return "\n".join(f"{v:.6g}" for v in defaults[default_col])
    if res == "Stunde":
        vals = to_grid(rate_q, 1)
    else:
        vals = rate_q / 4.0 if SERIES_KIND[name] == "energie" else rate_q
    return "\n".join(f"{v:.6g}" for v in vals)


def render_data_tab(inp) -> None:
    st.markdown("### Zeitreihen (Energiedaten und Preise)")
    st.caption("Im Standard rechnet das Tool mit den hinterlegten Stundenreihen. Eigene Reihen dürfen als Stunden-, "
               "Viertelstunden- oder gemischte Werte (z. B. das Jahr 2025) hochgeladen werden (.csv oder .txt).")
    st.caption("Das Tool rechnet immer in Viertelstunden (35.040 Schritte pro Jahr), unabhängig von der Auflösung Ihrer Daten. "
               "Stundenwerte werden dazu auf vier Viertelstunden gelegt (Preise und Leistungen bleiben gleich, Energie je Viertelstunde "
               "ein Viertel). Das geht über die Excel hinaus, die nur Stundenwerte kennt; mit reinen Stundendaten ergibt sich "
               "praktisch dasselbe Ergebnis wie in der Excel-Rechnung.")
    with st.expander("Allgemein: So muss eine eigene Reihe aufgebaut sein"):
        st.markdown(
            "- **Zeitraum:** ein Jahr ohne 29. Februar. Bei einem Schaltjahr wird der 29. Februar automatisch entfernt.\n"
            "- **Stundenwerte:** genau 8.760 Werte, einer je Stunde.\n"
            "- **Viertelstundenwerte:** genau 35.040 Werte, einer je Viertelstunde (seit dem 01.10.2025 am Day-Ahead-Markt üblich).\n"
            "- **Gemischte Auflösung** (z. B. 2025: bis 30.09. Stundenwerte, danach Viertelstundenwerte): Die Datei braucht eine Spalte "
            "mit dem Zeitstempel (Datum und Uhrzeit, z. B. „01.10.2025 00:15“ oder „2025-10-01 00:15“) vor dem Wert; Datum und "
            "Uhrzeit dürfen auch in zwei Spalten stehen. Aus dem Abstand zum nächsten Zeitstempel erkennt das Tool, ob der Wert "
            "eine Stunde oder eine Viertelstunde gilt.\n"
            "- **Einheiten:** Preise (Day-Ahead, CO₂) bleiben in €/MWh bzw. €/t, egal in welcher Auflösung. Energiewerte beziehen "
            "sich auf das jeweilige Intervall: Erzeugungsprofile in kWh je kW und Stunde bzw. je Viertelstunde (Viertelstunde: "
            "höchstens 0,25), §13k-Energie in kWh je Stunde bzw. je Viertelstunde.\n"
            "- **Reihenfolge:** zeitlich vom Jahresanfang bis zum Jahresende. Alle Reihen müssen dieselbe Zuordnung haben, damit z. B. "
            "Erzeugungsprofil und Börsenpreis zeitlich zusammenpassen.\n"
            "- **Dateiformat:** .csv oder .txt. Am einfachsten ist eine Spalte mit einer Zahl pro Zeile. Bei mehreren Spalten "
            "(getrennt durch Semikolon, Tabulator oder Komma) wird die **letzte** Spalte als Wert gelesen.\n"
            "- **Zahlen:** Dezimalkomma und Dezimalpunkt sind erlaubt, keine Tausendertrennzeichen. Eine Überschriftenzeile in der "
            "ersten Zeile wird übersprungen.\n"
            "- **Prüfung:** Das Tool prüft Anzahl, Zeitabstände und Lesbarkeit der Zahlen und nennt bei Fehlern die betroffene Zeile. "
            "Ob die Werte sinnvoll sind, müssen Sie selbst sicherstellen.\n"
            "- **Gültigkeit:** Hochgeladene Reihen gelten nur für die laufende Sitzung. Sie werden **nicht** in der gespeicherten "
            "Eingabedatei (.json) abgelegt und müssen nach einem Neuladen der Seite erneut hochgeladen werden. Mit „Auf Standard "
            "zurücksetzen“ nutzt das Tool wieder die hinterlegte Reihe.")
    defaults = load_default_timeseries()
    series_info = {
        "pv_kwh_per_kw": "pv_kwh_per_kw", "wind_kwh_per_kw": "wind_kwh_per_kw",
        "day_ahead": "day_ahead_eur_per_mwh",
        "co2_eur_per_t": "co2_eur_per_t", "section13k_kwh": "section13k_kwh"}
    for name, col in series_info.items():
        unit, sum_unit = SERIES_UNITS[name]
        with st.container(border=True):
            c1, c2 = st.columns([1.2, 1])
            custom = name in st.session_state["series"]
            rate_q = np.array(st.session_state["series"][name], dtype=float) if custom else None
            res, note, fname = st.session_state["series_info"].get(name, ("Stunde", "", ""))
            values = rate_q if custom else np.array(defaults[col], dtype=float)
            per_year = values.sum() / (4 if custom else 1)       # Jahresenergie je kW bzw. in kWh
            with c1:
                herkunft = (f"eigene Datei ({ {'Stunde': 'Stundenwerte', 'Viertelstunde': 'Viertelstundenwerte'}.get(res, 'gemischte Auflösung') })"
                            if custom else "Standardwerte (Stunde)")
                st.markdown(f"**{SERIES_LABELS[name]}** · {herkunft}")
                st.caption(f"**Bedeutung:** {SERIES_HELP[name]}")
                if custom and note:
                    st.caption(f"Hinweis zur Datei: {note}")
                fig = go.Figure(go.Scatter(y=values, mode="lines", line=dict(color="#1f4e79", width=1)))
                fig.update_layout(height=160, margin=dict(l=0, r=0, t=5, b=0), yaxis_title=unit,
                                  xaxis_title="Viertelstunde" if custom else "Stunde")
                st.plotly_chart(fig, width="stretch", key=f"plot_{name}")
                stats = [f"Summe {de(per_year, 0)} {sum_unit} pro Jahr"] if sum_unit else []
                stats += [f"Mittelwert {de(values.mean(), 3)}", f"Maximum {de(values.max(), 2)}"]
                if not sum_unit:
                    stats.insert(1, f"Minimum {de(values.min(), 2)}")
                st.caption(" · ".join(stats) + f" {unit}")
            with c2:
                up = st.file_uploader("Eigene Zeitreihe hochladen", type=["csv", "txt"], key=f"up_{name}")
                if up is not None and st.session_state.get(f"_up_{name}") != (up.name, up.size):
                    try:
                        parsed = read_series(up.getvalue(), SERIES_KIND[name])
                        st.session_state["series"][name] = parsed.rate_quarter.tolist()
                        st.session_state["series_info"][name] = (parsed.resolution, parsed.note, up.name)
                        st.session_state[f"_up_{name}"] = (up.name, up.size)
                        st.rerun()
                    except ValueError as err:
                        st.error(str(err))
                st.download_button("Aktuelle Reihe herunterladen (.csv)", series_download(name, rate_q, res, col, defaults),
                                   f"{name}.csv", "text/csv", key=f"dl_{name}", width="stretch")
                if custom and st.button("Auf Standard zurücksetzen", key=f"rs_{name}", width="stretch"):
                    del st.session_state["series"][name]
                    st.session_state["series_info"].pop(name, None)
                    st.session_state.pop(f"_up_{name}", None)
                    st.rerun()
    st.info("Hinweis: Eine hochgeladene Preisreihe ersetzt die hinterlegte Börsenpreisreihe (Standard: Jahr 2024). Die Reihen gelten "
            "für die gesamte Projektlaufzeit; die jährlichen Preisentwicklungen werden wie bisher darauf angewendet.")


if missing or errors:
    with tab_cockpit:
        if missing:
            right.info(f"Es fehlen noch {len(missing)} Angaben. Tragen Sie die Werte ein oder klicken Sie links auf "
                       f"„Standardwerte laden“. Sobald alle Pflichtfelder gefüllt sind, erscheinen hier die Ergebnisse.")
            with right.expander("Welche Angaben fehlen?", expanded=True):
                st.caption("Ein Klick auf den Namen springt zum Eingabefeld.")
                missing_links(missing)
        else:
            right.error("Bitte Eingaben prüfen:\n\n" + "\n".join(f"- {m}" for m in errors))
    with tab_res:
        st.info("Noch keine Ergebnisse: Es fehlen Angaben oder sie sind nicht plausibel. Siehe Reiter „Cockpit“.")
    with tab_data:
        render_data_tab(inp_eff)
    with st.sidebar:
        st.divider()
        st.caption("Noch keine Ergebnisse. Bitte Eingaben ergänzen oder Standardwerte laden.")
    footer()
    st.stop()

series_json = json.dumps(st.session_state["series"])
r, e = rechnen(json.dumps(effective, sort_keys=True, default=float), series_json, STEPS)
inp = r.inputs

with st.sidebar:
    st.divider()
    kmetric(st, "Gestehungskosten", de(e.lcoh_eur_per_kg), "€/kg",
              help="Wasserstoffgestehungskosten (LCOH₂): alle Kosten über die Projektlaufzeit, abzüglich Förderungen und Zusatzeinnahmen, je kg Wasserstoff.")
    st.caption(f"{de(e.lcoh_ct_per_kwh)} ct/kWh (Brennwert)  \n{de(e.h2_kg_per_year / 1000, 0)} t Wasserstoff pro Jahr  \n"
               f"{de(r.full_load_hours, 0)} h/a Ø Auslastung (Volllaststunden)  \n"
               f"{de(r.full_load_hours / 87.6, 1)} % Auslastung")
    st.download_button("Eingaben speichern (.json)", json.dumps(S, ensure_ascii=False, indent=1, default=float),
                       "eingaben_lcoh2.json", "application/json", width="stretch")

# ---------------------------------------------------------------- Kennzahlen
pc = e.power
green_share = 1 - pc.spot_kwh / pc.total_procurement_kwh if pc.total_procurement_kwh else 0.0
system_util = pc.consumption_total_kwh / (r.power.total_kw * 8760) if r.power.total_kw else 0.0
run_hours = int((r.hourly["consumption_kwh"] > 0).sum()) * DT
full_hours = int((r.hourly["consumption_kwh"] >= r.power.total_kw * DT * 0.99999).sum()) * DT
part_hours = run_hours - full_hours
avg_power_price = e.power_cost / (pc.total_procurement_kwh / 1000) if pc.total_procurement_kwh else 0.0
HELP_AVG_PRICE = ("Jährliche Stromkosten einschließlich Netzentgelten, Umlagen und Abgaben (nach Befreiungen), geteilt durch die "
                  "gesamte bezogene Strommenge.")
HELP_GREEN = ("Anteil des bezogenen Stroms, der nicht aus dem Spotmarkt (Netzmix) stammt. PPA (PPA 1, PPA 2, Grundlast), "
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
    ("Durchschnittlicher Strompreis (inkl. Abgaben)", f"{de(avg_power_price)} €/MWh")])
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
section_sum(A, "Wasserstoff-Aufbereitung", capex_pair("H₂-Aufbereitung"))
section_sum(A, "Leistung BoP", [("Leistung BoP", f"{de(r.power.peripherals_kw, 0)} kW")])
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
section_sum(R, "THG-Minderungsmenge", per_year("Einnahmen", e.revenue_thg))
section_sum(R, "Verkauf von Überschussstrom", per_year("Einnahmen", e.revenue_power_spot + e.revenue_power_ppa))
section_sum(R, "Sauerstoff", per_year("Einnahmen", e.revenue_oxygen))
section_sum(R, "Abwärme", per_year("Einnahmen", e.revenue_heat))
section_sum(R, "Regelenergie", per_year("Einnahmen", e.revenue_balancing))
section_sum(R, "Sonstige Einnahmen", per_year("Einnahmen", e.revenue_other))

# ---------------------------------------------------------------- Cockpit (Ergebnis rechts)
with cockpit_slot:
    st.markdown("### **Ergebnis**")
    k1, k2, k3 = st.columns(3)
    kmetric(k1, "Gestehungskosten", de(e.lcoh_eur_per_kg), "€/kg", help="Wasserstoffgestehungskosten (LCOH₂) über die "
              "Projektlaufzeit, inklusive Förderungen, Befreiungen und Zusatzeinnahmen.")
    kmetric(k2, "Gestehungskosten", de(e.lcoh_ct_per_kwh), "ct/kWh", help="Bezogen auf den Brennwert von 39,4 kWh/kg.")
    kmetric(k3, "Wasserstoff", de(e.h2_kg_per_year / 1000, 0), "t/a")
    k4, k5, k6 = st.columns(3)
    kmetric(k4, "Anteil grüner Wasserstoff", de(green_share * 100, 1), "%", help=HELP_GREEN)
    kmetric(k5, "Systemauslastung", de(system_util * 100, 1), "%", help="Stromverbrauch des Gesamtsystems bezogen auf "
              "den Dauerbetrieb mit Nennleistung über 8.760 Stunden.")
    kmetric(k6, "Ø Effizienz", de(r.avg_efficiency * 100, 1), "%", help="Mittlerer Wirkungsgrad des Elektrolyseurs über "
              "die Projektlaufzeit (inklusive Degradation).")
    k7, k8, k9 = st.columns(3)
    kmetric(k7, "Volllaststunden", de(r.full_load_hours, 0), "h/a")
    kmetric(k8, "Kapitalkostensatz (WACC)", de(e.wacc * 100, 1), "%")
    kmetric(k9, "Stacktausche", str(r.stack_replacements), "", help=f"Anzahl der Stacktausche in der Projektlaufzeit "
              f"(alle {de(r.stack_interval_years, 1)} Jahre).")
    k10, _, _ = st.columns(3)
    kmetric(k10, "Durchschnittlicher Strompreis (inkl. Abgaben)", de(avg_power_price), "€/MWh", help=HELP_AVG_PRICE)
    items = waterfall_items(r, e, "verbraucher", netto=True)
    st.markdown("#### Kostenstruktur")
    st.plotly_chart(cost_structure_figure(items, e.lcoh_eur_per_kg, detail=False, height=430,
                                          subsidy_title="Förderungen"), width="stretch")
    st.caption("Detaillierte Auswertung im Reiter „Ergebnisse“.")

# ---------------------------------------------------------------- Ergebnisse
with tab_res:
    r1, r2, r3 = st.columns(5), st.columns(5), st.columns(5)
    kmetric(r1[0], "Gestehungskosten", de(e.lcoh_eur_per_kg), "€/kg", help="Wasserstoffgestehungskosten (LCOH₂).")
    kmetric(r1[1], "Gestehungskosten", de(e.lcoh_ct_per_kwh), "ct/kWh", help="Bezogen auf den Brennwert von 39,4 kWh/kg.")
    kmetric(r1[2], "Wasserstoff", de(e.h2_kg_per_year / 1000, 0), "t/a")
    kmetric(r1[3], "CAPEX nach Förderung", de(e.capex_net / 1e6, 1), "Mio. €")
    kmetric(r1[4], "Kapitalkostensatz (WACC)", de(e.wacc * 100, 1), "%")
    kmetric(r2[0], "Anlagenleistung gesamt", de(r.power.total_kw / 1000, 1), "MW")
    kmetric(r2[1], "Betriebsstunden", de(run_hours, 0), "h/a", help="Stunden, in denen das System Strom verbraucht.")
    kmetric(r2[2], "davon Volllast", de(full_hours, 0), "h/a")
    kmetric(r2[3], "davon Teillast", de(part_hours, 0), "h/a")
    kmetric(r2[4], "Volllaststunden (Ely)", de(r.full_load_hours, 0), "h/a", help="Jahresenergie des Elektrolyseurs geteilt "
              "durch seine Nennleistung.")
    kmetric(r3[0], "Systemauslastung", de(system_util * 100, 1), "%", help="Stromverbrauch des Gesamtsystems bezogen auf "
              "den Dauerbetrieb mit Nennleistung über 8.760 Stunden.")
    kmetric(r3[1], "Ø Effizienz", de(r.avg_efficiency * 100, 1), "%", help="Mittlerer Wirkungsgrad des Elektrolyseurs über "
              "die Projektlaufzeit (inklusive Degradation).")
    kmetric(r3[2], "Anzahl Stacktausche", str(r.stack_replacements), "", help=f"Anzahl der Stacktausche in der "
            f"Projektlaufzeit (alle {de(r.stack_interval_years, 1)} Jahre).")
    kmetric(r3[3], "Anteil grüner Wasserstoff", de(green_share * 100, 1), "%", help=HELP_GREEN)
    kmetric(r3[4], "Durchschnittlicher Strompreis (inkl. Abgaben)", de(avg_power_price), "€/MWh", help=HELP_AVG_PRICE)
    st.caption("Die Berechnung erfolgt in Viertelstunden (35.040 Schritte pro Jahr) und geht damit über die Excel hinaus.")

    st.markdown("### Zusammensetzung der Gestehungskosten")
    mode = st.radio("Darstellung", ["Detailliert (Einzelposten)", "Gestapelt nach Bereichen",
                                    "Strom netto (Befreiungen verrechnet)"], index=2, key="chart_mode", horizontal=True,
                    help="Gestapelt: ein Balken je Bereich, farbig nach Einzelposten unterteilt. Detailliert: jeder "
                         "Einzelposten ein eigener Balken. Strom netto: Die Befreiungen von Stromnebenkosten werden "
                         "direkt mit den Stromkosten verrechnet; unter „Förderungen“ stehen nur echte Förderungen.")
    unit_mode = st.radio("Werte anzeigen als", ["€ pro kg Wasserstoff", "Anteil in %"], key="chart_unit", horizontal=True,
                         help="Wechselt die Beschriftung der Balken zwischen Euro je kg Wasserstoff und dem prozentualen "
                              "Anteil an den Gestehungskosten brutto.")
    percent = unit_mode.startswith("Anteil")
    items = waterfall_items(r, e, "verbraucher")
    detail = mode.startswith("Detailliert")
    sub_title = None
    if mode.startswith("Strom netto"):
        items = waterfall_items(r, e, "verbraucher", netto=True)
        sub_title = "Förderungen"
    fig = cost_structure_figure(items, e.lcoh_eur_per_kg, detail=detail, height=640 if detail else 520,
                                subsidy_title=sub_title, percent=percent)
    st.plotly_chart(fig, width="stretch")
    gross = sum(i.eur_per_kg for i in items if i.block in COST_BLOCK_NAMES)
    gross_text = ("Gestehungskosten brutto (ohne Förderungen und Zusatzeinnahmen)" if sub_title
                  else "Gestehungskosten brutto (ohne Förderungen, Befreiungen und Zusatzeinnahmen)")
    st.caption(f"{gross_text}: {de(gross)} €/kg · "
               f"Gestehungskosten: {de(e.lcoh_eur_per_kg)} €/kg")

    st.markdown("### Geordneter Lastverlauf")
    st.plotly_chart(load_duration_figure(r.hourly, r.power, steps_per_hour=STEPS), width="stretch")
    st.caption("Jede Linie zeigt die Energie je Stunde, der Größe nach geordnet (höchste Stunde links). Der "
               "Gesamtstrombezug liegt über dem Verbrauch, wenn Strom in die Batterie geladen oder als Überschuss verkauft wird.")

    st.markdown("### Ladezustand der Batterie")
    if inp.battery_enabled and r.power.battery_capacity_kwh > 0:
        st.plotly_chart(battery_soc_figure(r.hourly, r.power, steps_per_hour=STEPS), width="stretch")
        st.caption(f"Ladezyklen pro Jahr: {r.battery_cycles}")
    else:
        st.info("Die Batterie ist ausgeschaltet.")
    if inp.battery_enabled and inp.battery_optimize and r.power.battery_capacity_kwh > 0:
        st.markdown("#### Vergleich: Batterie wie in der Excel und nach Preissignalen optimiert")
        r0, e0 = rechnen(json.dumps({**effective, "battery_optimize": False}, sort_keys=True, default=float), series_json, STEPS)
        def _vgl(label, f, n=2, unit=""):
            a_, b_ = f(r0, e0), f(r, e)
            return (label, de(a_, n) + unit, de(b_, n) + unit, ("+" if b_ >= a_ else "−") + de(abs(b_ - a_), n) + unit)
        vgl = [_vgl("Gestehungskosten [€/kg]", lambda r_, e_: e_.lcoh_eur_per_kg),
               _vgl("Wasserstoff [t/a]", lambda r_, e_: e_.h2_kg_per_year / 1000, 0),
               _vgl("Volllaststunden Elektrolyseur [h/a]", lambda r_, e_: r_.full_load_hours, 0),
               _vgl("Stromkosten [Mio. €/a]", lambda r_, e_: e_.power_cost / 1e6),
               _vgl("Erlöse aus Stromverkauf [Mio. €/a]", lambda r_, e_: (e_.revenue_power_spot + e_.revenue_power_ppa) / 1e6),
               _vgl("Ladezyklen der Batterie [1/a]", lambda r_, e_: r_.battery_cycles, 0)]
        st.dataframe(pd.DataFrame(vgl, columns=["Kennzahl", "Batterie wie Excel", "Batterie optimiert", "Änderung"]),
                     hide_index=True, width="stretch")
        st.caption("Die optimierte Batterie plant täglich mit den Preisen der nächsten 24 Stunden plus Vorlauf (perfekte Voraussicht "
                   "im Fenster) und rechnet mit dem eingestellten Rundlaufwirkungsgrad. Sie geht über die Excel hinaus.")

    st.markdown("### Spotmarktpreise")
    st.plotly_chart(spot_price_figure(r.market, steps_per_hour=STEPS), width="stretch")
    st.caption(f"Die Linie ist grün, solange der Preis unter der §7-Grenze liegt. Gelb: zwischen der §7-Grenze und Ihrem Maximalpreis "
               f"({de(inp.spot_max_price_eur_per_mwh)} €/MWh). Rot: darüber. Einzelne extreme Preisspitzen sind zugunsten der "
               f"Lesbarkeit abgeschnitten; Sie können im Diagramm hineinzoomen.")

    st.markdown("### Sensitivitätsanalyse")
    sc1, sc2 = st.columns([1, 3])
    with sc1:
        field("sensitivity_step")
    rows_s = sensitivity(r, e, S["sensitivity_step"] if S["sensitivity_step"] is not None else 0.3)
    with sc2:
        st.caption("Jede Einflussgröße wird einzeln um die Schrittweite verringert bzw. erhöht; alle übrigen Kostenblöcke "
                   "bleiben unverändert (Vorgehen wie in der Excel). Links: Einflussgröße −x %, rechts: +x %. Die Länge zeigt die Kostenänderung; grün: Die Gestehungskosten sinken, rot: sie steigen.")
    st.plotly_chart(sensitivity_figure(rows_s, S["sensitivity_step"] or 0.3), width="stretch")
    pct_txt = f"{de(S['sensitivity_step'] * 100 if S['sensitivity_step'] is not None else 30, 0)} %"
    sens_df = pd.DataFrame([(z.name, z.block, z.v_minus, z.v_base, z.v_plus, z.setting, z.lcoh_minus, z.lcoh_plus)
                            for z in rows_s],
                           columns=["Einflussgröße", "Betroffener Kostenblock", f"Wert −{pct_txt}", "Basis",
                                    f"Wert +{pct_txt}", "Einstellung (− | Basis | +)", "Gestehungskosten − [€/kg]",
                                    "Gestehungskosten + [€/kg]"])
    def _unit(block: str) -> str:
        return block[block.index("["):] if "[" in block else ""

    def _setting(z) -> str:
        return z.setting or f"{de(z.v_minus, 0)} | {de(z.v_base, 0)} | {de(z.v_plus, 0)} {_unit(z.block)}"
    sens_show = pd.DataFrame([(z.name, z.lcoh_minus, z.lcoh_minus - z.base, z.lcoh_plus, z.lcoh_plus - z.base, _setting(z))
                              for z in rows_s],
                             columns=["Einflussgröße", f"Kosten −{pct_txt} [€/kg]", "Änderung [€/kg]",
                                      f"Kosten +{pct_txt} [€/kg]", "Änderung  [€/kg]",
                                      f"Eingestellter Wert (−{pct_txt} | Basis | +{pct_txt})"])
    fmt = {c: (lambda v: de(v, 2)) for c in sens_show.columns[1:5]}
    st.dataframe(sens_show.iloc[::-1].style.format(fmt), hide_index=True, width="stretch")
    st.caption("Reihenfolge wie im Diagramm (von oben nach unten). Die Excel-Datei zum Herunterladen enthält zusätzlich die "
               "veränderten Kostenblöcke in €.")

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
            ("Rechenauflösung", "Viertelstunde"),
            ("Elektrolyseurleistung", f"{de(r.power.ely_kw, 0)} kW"), ("Gesamtleistung System", f"{de(r.power.total_kw, 0)} kW"),
            ("Batteriekapazität", f"{de(r.power.battery_capacity_kwh, 0)} kWh"),
            ("Stromverbrauch gesamt", f"{de(pc.consumption_total_kwh / 1e6, 2)} GWh/a"),
            ("Stromverbrauch Elektrolyseur", f"{de(pc.consumption_ely_kwh / 1e6, 2)} GWh/a"),
            ("Überschussstrom", f"{de(pc.surplus_kwh / 1e6, 2)} GWh/a"),
            ("Mittlerer Wirkungsgrad", f"{de(r.avg_efficiency * 100, 1)} %"),
            ("Stacktausche in der Laufzeit", f"{r.stack_replacements} (alle {de(r.stack_interval_years, 1)} Jahre)"),
            ("Stunden mit §7-Bezug", de(r.section7_hours, 2)), ("Stunden mit §13k-Bezug", de(r.section13k_hours, 2)),
            ("Ladezyklen Batterie", f"{r.battery_cycles}"),
            ("CAPEX brutto", f"{de(e.capex_gross / 1e6, 2)} Mio. €"),
            ("CAPEX-Förderung", f"{de(e.capex_subsidy / 1e6, 2)} Mio. €"),
            ("Kapitalkostensatz (WACC)", f"{de(e.wacc * 100, 2)} %"),
        ]
        st.dataframe(pd.DataFrame(kennz, columns=["Kennzahl", "Wert"]), hide_index=True, width="stretch")

    st.markdown("### Strombezug im Überblick")
    m = 1000.0
    quellen = [("PPA 1", pc.ppa_pv_kwh, pc.price_pv), ("PPA 2", pc.ppa_wind_kwh, pc.price_wind),
               ("PPA Grundlast", pc.baseload_kwh, pc.price_baseload), ("§7 (37. BImSchV)", pc.section7_kwh, pc.price_s7),
               ("§13k EnWG", pc.section13k_kwh, pc.price_13k), ("Spotmarkt", pc.spot_kwh, pc.price_spot)]
    tab = pd.DataFrame([(n, q / m, q / pc.total_procurement_kwh * 100 if pc.total_procurement_kwh else 0, p, q / m * p)
                        for n, q, p in quellen],
                       columns=["Quelle", "Menge [MWh/a]", "Anteil [%]", "Preis [€/MWh]", "Kosten [€/a]"])
    st.dataframe(tab.style.format({"Menge [MWh/a]": lambda v: de(v, 0), "Anteil [%]": lambda v: de(v, 1),
                                   "Preis [€/MWh]": lambda v: de(v, 2), "Kosten [€/a]": lambda v: de(v, 0)}),
                 hide_index=True, width="stretch")

    # ---- Gesamttabelle
    st.markdown("### Alle Ergebnisse im Überblick")
    alle = [("Gestehungskosten", "Gestehungskosten", e.lcoh_eur_per_kg, "€/kg"),
            ("Gestehungskosten", "Gestehungskosten", e.lcoh_ct_per_kwh, "ct/kWh"),
            ("Gestehungskosten", "Gestehungskosten brutto", gross, "€/kg"),
            ("Anlage", "Wasserstoff pro Jahr", e.h2_kg_per_year / 1000, "t/a"),
            ("Anlage", "Anlagenleistung gesamt", r.power.total_kw / 1000, "MW"),
            ("Anlage", "Anzahl Stacktausche", r.stack_replacements, ""),
            ("Anlage", "Ø Effizienz", r.avg_efficiency * 100, "%"),
            ("Anlage", "Anteil grüner Wasserstoff", green_share * 100, "%"),
            ("Anlage", "Systemauslastung", system_util * 100, "%"),
            ("Anlage", "Betriebsstunden", run_hours, "h/a"),
            ("Anlage", "davon Volllast", full_hours, "h/a"),
            ("Anlage", "davon Teillast", part_hours, "h/a"),
            ("Anlage", "Volllaststunden (Ely)", r.full_load_hours, "h/a"),
            ("Finanzierung", "CAPEX nach Förderung", e.capex_net / 1e6, "Mio. €"),
            ("Finanzierung", "Kapitalkostensatz (WACC)", e.wacc * 100, "%")]
    alle += [("Kosten und Erlöse pro Jahr", n, v, "€/a") for n, v in rows]
    alle += [("Kosten und Erlöse je kg", n, v / h2 if h2 else 0.0, "€/kg") for n, v in rows]
    alle += [("Anlage und Betrieb", k, w.split(" ")[0], " ".join(w.split(" ")[1:])) for k, w in kennz]
    alle += [("Strombezug", f"{n}: Menge", q / m, "MWh/a") for n, q, _ in quellen]
    alle += [("Strombezug", f"{n}: Preis", p, "€/MWh") for n, _, p in quellen]
    alle += [("Strombezug", "Durchschnittlicher Strompreis (inkl. Abgaben)", avg_power_price, "€/MWh")]
    alle += [("Sensitivität", f"{z.name}: Kosten −{pct_txt}", z.lcoh_minus, "€/kg") for z in rows_s]
    alle += [("Sensitivität", f"{z.name}: Kosten +{pct_txt}", z.lcoh_plus, "€/kg") for z in rows_s]
    alle_df = pd.DataFrame([(b, k, (de(v, 2) if isinstance(v, float) else str(v)), u) for b, k, v, u in alle],
                           columns=["Bereich", "Kennzahl", "Wert", "Einheit"])
    st.dataframe(alle_df, hide_index=True, width="stretch", height=563)

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
        pd.DataFrame([(i.block, i.label, i.eur_per_kg) for i in items], columns=["Block", "Posten", "€ pro kg H₂"]).to_excel(
            xw, sheet_name="Wasserfall", index=False)
        df.to_excel(xw, sheet_name="Kosten und Erlöse", index=False)
        tab.to_excel(xw, sheet_name="Strombezug", index=False)
        sens_df.to_excel(xw, sheet_name="Sensitivität", index=False)
        pd.DataFrame([(SPEC_BY_KEY[k].label, SPEC_BY_KEY[k].unit, v) for k, v in S.items() if k in SPEC_BY_KEY],
                     columns=["Eingabe", "Einheit", "Wert (Anteile als Dezimalzahl)"]).to_excel(xw, sheet_name="Eingaben", index=False)
    d1, d2, d3 = st.columns(3)
    d1.download_button("Ergebnisse als Excel (.xlsx)", buf.getvalue(), "ergebnisse_lcoh2.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    d2.download_button("Viertelstundenwerte (.csv)", r.hourly.to_csv(index=False),
                       "viertelstundenwerte_lcoh2.csv", "text/csv",
                       width="stretch")
    d3.download_button("Eingaben (.json)", json.dumps(S, ensure_ascii=False, indent=1, default=float),
                       "eingaben_lcoh2.json", "application/json", width="stretch")


with tab_data:
    render_data_tab(inp)
footer()
