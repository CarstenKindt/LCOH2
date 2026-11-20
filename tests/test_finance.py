"""Weitere wirtschaftliche Kennzahlen: Zusammenhang mit den Gestehungskosten."""
import pytest

from lcoh.economics import compute_economics
from lcoh.finance import MODE_MARGIN, MODE_TARGET, compute_finance, irr
from lcoh.inputs import Inputs
from lcoh.npv import npv_lcoh
from lcoh.operation import run_operation
from lcoh.zeitreihen import build_timeseries
import numpy as np


def _fin(mode=MODE_MARGIN, margin=0.0, target=8.0, esc=0.0, **kw):
    r = run_operation(Inputs(**kw), build_timeseries({}, 1), steps_per_hour=1)
    e = compute_economics(r)
    n = npv_lcoh(r, e)
    return n, compute_finance(r, e, n, mode, margin, target, esc)


def test_preis_gleich_lcoh_ergibt_kapitalwert_null():
    n, f = _fin(margin=0.0)
    assert f.price_year1 == pytest.approx(n.lcoh_eur_per_kg)
    assert f.npv_project == pytest.approx(0.0, abs=1.0)
    assert f.irr_project == pytest.approx(n.rate, abs=1e-6)
    assert f.table["Kumuliert abgezinst [€]"].iloc[-1] == pytest.approx(0.0, abs=1.0)


def test_marge_erhoeht_kapitalwert_und_rendite():
    _, f0 = _fin(margin=0.0)
    _, f1 = _fin(margin=0.2)
    assert f1.npv_project > f0.npv_project and f1.irr_project > f0.irr_project
    assert f1.npv_equity > f0.npv_equity


def test_zielpreis():
    _, f = _fin(mode=MODE_TARGET, target=9.0, esc=0.02)
    assert f.price_year1 == 9.0
    assert f.table["Verkaufspreis [€/kg]"].iloc[2] == pytest.approx(9.0 * 1.02)


def test_eigenkapital_und_fremdkapital():
    _, f = _fin(margin=0.1)
    assert f.debt + f.equity == pytest.approx(-f.table["Investition [€]"].iloc[0])
    t = f.table.iloc[1:]
    assert list(t["Cashflow Eigenkapital [€]"]) == pytest.approx(list(t["Cashflow Projekt [€]"] + t["Kapitaldienst Fremdkapital [€]"]))


def test_irr_lehrbuch():
    assert irr(np.array([-100.0, 110.0])) == pytest.approx(0.10, abs=1e-6)
    assert irr(np.array([-100.0, -10.0])) is None
