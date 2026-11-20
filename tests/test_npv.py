"""Kapitalwertmethode: Plausibilität und Zusammenhang mit der Annuitätenmethode."""
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


def test_wacc_ohne_steuern():
    r, e = _run(debt_share=0.8, debt_interest_rate=0.065, equity_interest_rate=0.12)
    assert e.wacc == pytest.approx(0.076)
    assert npv_lcoh(r, e).rate == pytest.approx(0.076)


def test_beispiel_aus_dem_chat():
    """Lehrbuchbeispiel: 300 € Investition, 30 €/a Betrieb, 100 kg/a, 3 Jahre, 8 %: beide Methoden 1,464 €/kg."""
    i, n = 0.08, 3
    d = [(1 + i) ** -t for t in range(1, n + 1)]
    kw = (300 + sum(30 * x for x in d)) / sum(100 * x for x in d)
    an = (300 * i / (1 - (1 + i) ** -n) + 30) / 100
    assert kw == pytest.approx(an) == pytest.approx(1.464, abs=1e-3)


def test_equivalent_economics_consistent_with_headline():
    r, e = _run(lcoh_method="Kapitalwertmethode")
    n = npv_lcoh(r, e)
    assert n.economics.lcoh_eur_per_kg == pytest.approx(n.lcoh_eur_per_kg, rel=1e-9)


def test_constant_prices_close_to_annuity():
    """Ohne Preissteigerung, Degradation und THG (zeitlich ungleich verteilt) liegen beide Methoden nahe beieinander,
    wenn Fremd- und Eigenkapital denselben Zins haben (dann ist die Annuitätenmethode exakt eine Kapitalwertrechnung)."""
    esc = {f.name: 0.0 for f in dataclasses.fields(Inputs) if f.name.endswith("escalation")}
    r, e = _run(stack_degradation_per_year=0.0, thg_enabled=False, debt_interest_rate=0.07, equity_interest_rate=0.07, **esc)
    assert npv_lcoh(r, e).lcoh_eur_per_kg == pytest.approx(e.lcoh_eur_per_kg, rel=0.03)


def test_higher_rate_raises_cost():
    r, e = _run(debt_interest_rate=0.03, equity_interest_rate=0.05)
    a = npv_lcoh(r, e).lcoh_eur_per_kg
    r, e = _run(debt_interest_rate=0.08, equity_interest_rate=0.12)
    assert npv_lcoh(r, e).lcoh_eur_per_kg > a


def test_yearly_view_reproduces_npv_result():
    from lcoh.yearly import yearly_lcoh
    r, e = _run(lcoh_method="Kapitalwertmethode")
    n = npv_lcoh(r, e)
    y = yearly_lcoh(r, n.economics, n.rate, n.capital_service, n.stack_service)
    assert y.lcoh_sum_ratio == pytest.approx(n.lcoh_eur_per_kg, rel=1e-9)


def test_sensitivity_on_annuity_base():
    from lcoh.sensitivity import sensitivity
    r, e = _run()
    for row in sensitivity(r, e, 0.3):
        if row.name == "CAPEX":
            assert row.lcoh_minus < row.base < row.lcoh_plus


def test_stacktausch_als_jahresbetrag():
    """Stacktausch in beiden Methoden als gleichbleibender Jahresbetrag (Tauschkosten + Kreditzinsen)."""
    r, e = _run()
    n = npv_lcoh(r, e)
    assert n.stack_service == pytest.approx(e.stack.annual_cost)
    r2, e2 = _run(stack_interest_rate=0.10)
    assert npv_lcoh(r2, e2).lcoh_eur_per_kg > n.lcoh_eur_per_kg
