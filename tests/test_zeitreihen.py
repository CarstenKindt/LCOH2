"""Prüft die Standard-Zeitreihen gegen die Stundenwerte der Excel (Blatt 4)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lcoh.zeitreihen import check_timeseries, load_default_timeseries

REF_DIR = Path(__file__).parent / "reference"


@pytest.fixture(scope="module")
def ts():
    return load_default_timeseries()


@pytest.fixture(scope="module")
def excel_hours():
    return pd.read_csv(REF_DIR / "excel_stunden.csv.gz")


def test_timeseries_complete(ts):
    assert check_timeseries(ts) == []


def test_wind_matches_excel_ppa2(ts, excel_hours):
    # Blatt 4, Spalte I = "PPA 2 [pro kW]" (Wind)
    np.testing.assert_allclose(ts["wind_kwh_per_kw"], excel_hours["I"], rtol=1e-12, atol=1e-12)


def test_pv_matches_excel_ppa1(ts, excel_hours):
    # Blatt 4, Spalte G = "PPA 1 [pro kW]" (PV)
    np.testing.assert_allclose(ts["pv_kwh_per_kw"], excel_hours["G"], rtol=1e-12, atol=1e-12)


def test_day_ahead_2024_matches_excel(ts, excel_hours):
    # Blatt 4, Spalte P = Strompreis nach §7 (mit negativen Preisen) = Börsenpreis 2024
    np.testing.assert_allclose(ts["day_ahead_2024_eur_per_mwh"], excel_hours["P"], rtol=1e-12, atol=1e-12)


def test_check_finds_missing_columns_and_length():
    bad = pd.DataFrame({"hour": [1, 2, 3]})
    assert any("fehlen" in p for p in check_timeseries(bad))
    ts = load_default_timeseries().head(100)
    assert any("8760" in p for p in check_timeseries(ts))
