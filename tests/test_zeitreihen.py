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


def test_parse_series_formate():
    from lcoh.zeitreihen import parse_series
    n = 8760
    einfach = "\n".join(str(i / 10) for i in range(n)).encode()
    assert len(parse_series(einfach)) == n
    deutsch = ("Wert\n" + "\n".join(f"{i / 10:.1f}".replace(".", ",") for i in range(n))).encode("latin-1")
    assert parse_series(deutsch)[5] == pytest.approx(0.5)
    mehrspaltig = "\n".join(f"{i};{i / 10:.2f}".replace(".", ",") for i in range(n)).encode()
    assert parse_series(mehrspaltig)[10] == pytest.approx(1.0)
    with pytest.raises(ValueError, match="8760"):
        parse_series(b"1\n2\n3\n")
    with pytest.raises(ValueError, match="keine Zahl"):
        parse_series(("1\n" * 100 + "abc\n").encode())
