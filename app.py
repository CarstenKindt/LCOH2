"""Einfache Testoberfläche (Vorabversion). Start:  streamlit run app.py"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from lcoh.economics import compute_economics
from lcoh.input_spec import GROUPS, SPECS
from lcoh.inputs import Inputs
from lcoh.operation import run_operation
from lcoh.zeitreihen import load_default_timeseries

st.set_page_config(page_title="LCOH2-Rechner (Vorabversion)", layout="wide")
st.title("LCOH2-Rechner – Vorabversion")
st.caption("Testversion zum Vergleich mit der Excel. Oberfläche und Layout werden noch überarbeitet.")


@st.cache_data(show_spinner="Berechnung läuft ...")
def rechnen(werte_json: str):
    inp = Inputs.from_dict(json.loads(werte_json))
    r = run_operation(inp, load_default_timeseries())
    return r, compute_economics(r)


# ---- Eingaben speichern/laden
with st.sidebar:
    st.header("Eingaben")
    datei = st.file_uploader("Gespeicherte Eingaben laden (.json)", type="json")
    if datei is not None and st.session_state.get("_geladen") != datei.name:
        for key, wert in Inputs.from_dict(json.load(datei)).to_dict().items():
            st.session_state[f"w_{key}"] = wert
            st.session_state[f"p_{key}"] = wert * 100 if isinstance(wert, float) else wert
        st.session_state["_geladen"] = datei.name
        st.rerun()

werte = {}
for gruppe in GROUPS:
    with st.sidebar.expander(gruppe, expanded=(gruppe == GROUPS[0])):
        for s in [x for x in SPECS if x.group == gruppe]:
            key = f"w_{s.key}"
            label = f"{s.label}" + (f" [{s.unit}]" if s.unit else "")
            if key not in st.session_state:
                st.session_state[key] = s.default
            if s.kind == "bool":
                werte[s.key] = st.checkbox(label, key=key)
            elif s.kind == "choice":
                werte[s.key] = st.selectbox(label, s.choices, key=key)
            elif s.kind == "percent":
                pkey = f"p_{s.key}"
                if pkey not in st.session_state:
                    st.session_state[pkey] = float(st.session_state[key]) * 100
                prozent = st.number_input(label, step=0.5, format="%.3f", key=pkey)
                werte[s.key] = prozent / 100
            else:
                step = 1 if isinstance(s.default, int) else None
                werte[s.key] = st.number_input(label, step=step, key=key)

eingabe_json = json.dumps(werte, sort_keys=True, default=float)
st.sidebar.download_button("Eingaben speichern (.json)", eingabe_json, "eingaben.json", "application/json")

fehler = Inputs.from_dict(werte).validate()
if fehler:
    st.error("Bitte Eingaben prüfen:\n\n" + "\n".join(f"- {f}" for f in fehler))
    st.stop()

r, e = rechnen(eingabe_json)

# ---- Ergebnis
c1, c2, c3, c4 = st.columns(4)
c1.metric("Wasserstoffgestehungskosten", f"{e.lcoh_eur_per_kg:.2f} €/kg")
c2.metric("in ct/kWh (Brennwert)", f"{e.lcoh_ct_per_kwh:.2f} ct/kWh")
c3.metric("Wasserstoff pro Jahr", f"{e.h2_kg_per_year/1000:,.0f} t")
c4.metric("Vollaststunden", f"{r.full_load_hours:,.0f} h/a")

zeilen = [
    ("Stackaustausch", e.stack_cost_per_year), ("Betriebskosten (OPEX)", e.opex_total),
    ("Stromkosten", e.power_cost), ("Finanzierung", e.financing_total),
    ("Strompreiskompensation", -e.spk), ("Erlöse (Nebenprodukte, THG, Stromverkauf)", -e.revenue_total),
]
df = pd.DataFrame(zeilen, columns=["Posten", "€ pro Jahr"])
df["€ pro kg H2"] = df["€ pro Jahr"] / e.h2_kg_per_year if e.h2_kg_per_year else 0.0
left, right = st.columns([3, 2])
with left:
    st.subheader("Kosten und Erlöse pro Jahr")
    st.bar_chart(df.set_index("Posten")["€ pro kg H2"])
with right:
    st.dataframe(df.style.format({"€ pro Jahr": "{:,.0f}", "€ pro kg H2": "{:.3f}"}), hide_index=True)

erloese = pd.DataFrame([
    ("THG-Quote", e.revenue_thg), ("Stromverkauf Spotmarkt", e.revenue_power_spot), ("Stromverkauf PPA", e.revenue_power_ppa),
    ("Sauerstoff", e.revenue_oxygen), ("Abwärme", e.revenue_heat), ("Regelenergie", e.revenue_balancing),
    ("Sonstige", e.revenue_other)], columns=["Erlös", "€ pro Jahr"])
with st.expander("Details: Erlöse, CAPEX, Anlage"):
    st.dataframe(erloese.style.format({"€ pro Jahr": "{:,.0f}"}), hide_index=True)
    st.write(f"CAPEX (brutto): {e.capex_gross:,.0f} € · Förderung: {e.capex_subsidy:,.0f} € · "
             f"Gesamtleistung der Anlage: {r.power.total_kw:,.0f} kW · Stack-Tauschintervall: {r.stack_interval_years:g} Jahre")

# ---- Ergebnis-Download
ergebnis = {"lcoh_eur_per_kg": e.lcoh_eur_per_kg, "lcoh_ct_per_kwh": e.lcoh_ct_per_kwh,
            "h2_kg_per_year": e.h2_kg_per_year, "kosten_und_erloese": df.to_dict("records"),
            "erloese": erloese.to_dict("records")}
st.download_button("Ergebnis herunterladen (.json)", json.dumps(ergebnis, ensure_ascii=False, indent=1, default=float),
                   "ergebnis.json", "application/json")
st.download_button("Stundenwerte herunterladen (.csv)", r.hourly.to_csv(index=False), "stundenwerte.csv", "text/csv")
