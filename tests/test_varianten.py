"""Zusätzliche Testfälle aus Excel-Varianten (tests/reference/varianten)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lcoh.dispatch import simulate_dispatch
from lcoh.inputs import Inputs
from lcoh.operation import run_operation
from lcoh.prices import build_market_series
from lcoh.system import system_power
from lcoh.zeitreihen import load_default_timeseries
from tests.test_dispatch import SPALTEN

VAR = Path(__file__).parent / "reference" / "varianten"


def lade(name):
    inp = Inputs.from_dict(json.loads((VAR / f"{name}_eingaben.json").read_text()))
    ref = json.loads((VAR / f"{name}_zellwerte.json").read_text())
    stunden = pd.read_csv(VAR / f"{name}_stunden.csv.gz")
    return inp, ref, stunden


def pruefe_stunden(inp, ref, stunden, hourly):
    for py, xl in SPALTEN.items():
        np.testing.assert_allclose(hourly[py].to_numpy(), stunden[xl].to_numpy(dtype=float),
                                   rtol=1e-7, atol=1e-6, err_msg=f"Spalte {xl}")


def test_ohne_batterie_komplett():
    inp, ref, stunden = lade("ohne_batterie")
    r = run_operation(inp, load_default_timeseries())
    pruefe_stunden(inp, ref, stunden, r.hourly)
    assert r.power.total_kw == pytest.approx(ref["B4!C5"], rel=1e-9)
    assert r.ely_consumption_kwh == pytest.approx(ref["B4!Y4"], rel=1e-9)
    assert r.full_load_hours == pytest.approx(ref["B2!F13"], rel=1e-9)
    assert r.h2_kg_per_year == pytest.approx(ref["B2!F8"], rel=1e-9)


def test_klein_stunden_mit_excel_wirkungsgrad():
    """In dieser Excel-Datei wurde die Hilfszelle F129 nicht nachgeführt (10 statt 6,67 Jahre);
    der Excel-Wirkungsgrad ist daher nicht konvergiert. Die Stundenrechnung wird mit dem
    Excel-Wirkungsgrad geprüft, die Konvergenz des Tools separat."""
    inp, ref, stunden = lade("klein")
    ts = load_default_timeseries()
    power = system_power(inp, ref["B3!C29"])
    hourly = simulate_dispatch(inp, ts, build_market_series(inp, ts), power)
    pruefe_stunden(inp, ref, stunden, hourly)
    assert power.total_kw == pytest.approx(ref["B4!C5"])
    r = run_operation(inp, ts)
    assert r.stack_interval_years == pytest.approx(ref["B6!C5"])
    assert r.ely_consumption_kwh == pytest.approx(ref["B4!Y4"], rel=1e-9)


def test_s13k_spot_schalter_stunden():
    """Spotmarkt und §13k sind eingeschaltet, die Grundlast deckt die Anlage aber schon voll ab;
    geprüft wird, dass die eingeschalteten Schalter nichts verändern (wie in der Excel)."""
    inp, ref, stunden = lade("s13k")
    assert inp.section13k_enabled and inp.spot_enabled
    ts = load_default_timeseries()
    power = system_power(inp, ref["B3!C29"])
    hourly = simulate_dispatch(inp, ts, build_market_series(inp, ts), power)
    pruefe_stunden(inp, ref, stunden, hourly)


def test_s13k_knapp_komplett():
    """5-MW-Anlage, Grundlast 1,2 MW, dazu §13k-Strom und Spotmarkt (beide wirksam), ohne Batterie."""
    inp, ref, stunden = lade("s13k_knapp")
    r = run_operation(inp, load_default_timeseries())
    pruefe_stunden(inp, ref, stunden, r.hourly)
    assert r.power.total_kw == pytest.approx(ref["B4!C5"], rel=1e-9)
    assert r.ely_consumption_kwh == pytest.approx(ref["B4!Y4"], rel=1e-9)
    assert r.h2_kg_per_year == pytest.approx(ref["B2!F8"], rel=1e-9)
    assert r.section13k_hours > 0 and (r.hourly["spot_kwh"] > 0).any()


def test_s13k_batterie_eigener_spotpreis():
    """Batterie + §13k + Spotmarkt (eigener Preis 50 EUR/MWh) bei 5 MW und 1,2 MW Grundlast."""
    inp, ref, stunden = lade("s13k_batt")
    assert inp.battery_enabled and inp.spot_price_source == "Eigene Preise"
    r = run_operation(inp, load_default_timeseries())
    pruefe_stunden(inp, ref, stunden, r.hourly)
    assert r.ely_consumption_kwh == pytest.approx(ref["B4!Y4"], rel=1e-9)
    assert r.h2_kg_per_year == pytest.approx(ref["B2!F8"], rel=1e-9)


def test_v5_thg_variante_betrieb():
    """Variante mit THG (Inbetriebnahme 2029, THG-Preis 500 EUR/t); Ziel-LCOH 4,5695 EUR/kg (Etappe 4)."""
    inp, ref, stunden = lade("v5")
    assert inp.thg_enabled and inp.commissioning_year == 2029
    r = run_operation(inp, load_default_timeseries())
    pruefe_stunden(inp, ref, stunden, r.hourly)
    assert r.h2_kg_per_year == pytest.approx(ref["B2!F8"], rel=1e-9)
