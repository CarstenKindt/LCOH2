"""Vergleich der stündlichen Rechnung mit den Excel-Werten des Beispielfalls (Blatt 4)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lcoh.dispatch import simulate_dispatch
from lcoh.inputs import Inputs
from lcoh.prices import build_market_series
from lcoh.system import system_power
from lcoh.zeitreihen import load_default_timeseries

REF = Path(__file__).parent / "reference"
ZELLEN = json.loads((REF / "excel_zellwerte.json").read_text())
STUNDEN = pd.read_csv(REF / "excel_stunden.csv.gz")

# Python-Spalte -> Excel-Spalte
SPALTEN = {
    "baseload_kwh": "F", "pv_kwh": "H", "wind_kwh": "J", "ppa_kwh": "L", "ppa_load_ratio": "M",
    "battery_charge_ppa_kwh": "N", "ppa_util_battery": "O", "price_s7": "P", "s7_kwh": "Q",
    "s7_cost_eur": "R", "ppa_s7_kwh": "S", "battery_charge_s7_kwh": "T", "util_s7": "U",
    "s13k_kwh": "V", "supply_s13k_kwh": "W", "battery_charge_s13k_kwh": "X",
    "battery_charge_kwh": "Y", "battery_discharge_kwh": "Z", "battery_soc_kwh": "AA",
    "battery_soc": "AB", "util_before_spot": "AC", "spot_kwh": "AD", "util_total": "AE",
    "purchase_kwh": "AF", "consumption_kwh": "AG", "surplus_kwh": "AH",
    "surplus_revenue_eur": "AI", "spot_cost_eur": "AJ",
}


@pytest.fixture(scope="module")
def ergebnis():
    inp = Inputs()
    ts = load_default_timeseries()
    power = system_power(inp, ZELLEN["B3!C29"])
    market = build_market_series(inp, ts)
    return power, simulate_dispatch(inp, ts, market, power)


def test_gesamtleistung(ergebnis):
    power, _ = ergebnis
    assert power.total_kw == pytest.approx(ZELLEN["B4!C5"], rel=1e-9)
    assert power.battery_capacity_kwh == pytest.approx(ZELLEN["B4!V3"])


@pytest.mark.parametrize("py_col,xl_col", list(SPALTEN.items()))
def test_stundenspalte(ergebnis, py_col, xl_col):
    _, df = ergebnis
    erwartet = STUNDEN[xl_col].to_numpy(dtype=float)
    np.testing.assert_allclose(df[py_col].to_numpy(), erwartet, rtol=1e-7, atol=1e-6,
                               err_msg=f"Spalte {xl_col}")


def test_summen(ergebnis):
    _, df = ergebnis
    assert df["consumption_kwh"].sum() * 1.0 == pytest.approx(STUNDEN["AG"].sum(), rel=1e-9)


def test_betriebsrechnung_gesamt():
    from lcoh.operation import run_operation
    r = run_operation(Inputs(), load_default_timeseries())
    assert r.stack_interval_years == ZELLEN["B6!C5"]
    assert r.avg_efficiency == pytest.approx(ZELLEN["B3!C29"])
    assert r.power.total_kw == pytest.approx(ZELLEN["B4!C5"], rel=1e-9)
    assert r.ely_consumption_kwh == pytest.approx(ZELLEN["B4!Y4"], rel=1e-9)
    assert r.full_load_hours == pytest.approx(ZELLEN["B2!F13"], rel=1e-9)
    assert r.h2_energy_kwh == pytest.approx(ZELLEN["B2!F7"], rel=1e-9)
    assert r.h2_kg_per_year == pytest.approx(ZELLEN["B2!F8"], rel=1e-9)
    assert r.section7_hours == ZELLEN["B4!S4"]
