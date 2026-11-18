"""Kapitalwertmethode: Plausibilität gegenüber der Annuitätenmethode."""
import dataclasses
import pytest

from lcoh.economics import compute_economics
from lcoh.inputs import Inputs
from lcoh.npv import npv_lcoh
from lcoh.operation import run_operation
from lcoh.zeitreihen import build_timeseries


def _run(**kw):
    inp = Inputs(**kw)
    ts = build_timeseries({}, 1)
    r = run_operation(inp, ts, steps_per_hour=1)
    return r, compute_economics(r)


def test_rate_zero_equals_plain_average():
    r, e = _run(discount_rate_mode="Eigener Wert", discount_rate=0.0, lcoh_method="Kapitalwertmethode")
    n = npv_lcoh(r, e)
    assert n.lcoh_eur_per_kg > 0
    assert n.economics.lcoh_eur_per_kg == pytest.approx(n.lcoh_eur_per_kg, rel=1e-9)


def test_equivalent_economics_consistent_with_headline():
    r, e = _run(lcoh_method="Kapitalwertmethode")
    n = npv_lcoh(r, e)
    assert n.economics.lcoh_eur_per_kg == pytest.approx(n.lcoh_eur_per_kg, rel=1e-9)


def test_constant_prices_close_to_annuity():
    # THG-Erlöse sind zeitlich ungleich verteilt (Abzinsung gewichtet frühe Jahre stärker): hier ausgeschaltet
    kw = dict(lcoh_method="Kapitalwertmethode", stack_degradation_per_year=0.0, corporate_tax_rate=0.0, thg_enabled=False)
    r, e = _run(**kw)
    inp = r.inputs
    esc = {f.name: 0.0 for f in dataclasses.fields(Inputs) if f.name.endswith("escalation")}
    r2, e2 = _run(**kw, **esc)
    n = npv_lcoh(r2, e2)
    assert n.lcoh_eur_per_kg == pytest.approx(e2.lcoh_eur_per_kg, rel=0.03)


def test_higher_rate_raises_cost():
    r, e = _run(lcoh_method="Kapitalwertmethode", discount_rate_mode="Eigener Wert", discount_rate=0.04)
    a = npv_lcoh(r, e).lcoh_eur_per_kg
    r, e = _run(lcoh_method="Kapitalwertmethode", discount_rate_mode="Eigener Wert", discount_rate=0.10)
    assert npv_lcoh(r, e).lcoh_eur_per_kg > a


def test_yearly_view_reproduces_npv_result():
    from lcoh.yearly import yearly_lcoh
    r, e = _run(lcoh_method="Kapitalwertmethode")
    n = npv_lcoh(r, e)
    y = yearly_lcoh(r, n.economics, n.rate, n.capital_service, n.stack_service)
    assert y.lcoh_sum_ratio == pytest.approx(n.lcoh_eur_per_kg, rel=1e-9)


def test_sensitivity_uses_annuity_base_in_npv_mode():
    from lcoh.sensitivity import sensitivity
    r, e = _run(lcoh_method="Kapitalwertmethode")
    for row in sensitivity(r, e, 0.3):
        if row.name == "CAPEX":
            assert row.lcoh_minus < row.base < row.lcoh_plus
