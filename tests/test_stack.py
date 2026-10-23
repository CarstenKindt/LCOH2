import pytest

from lcoh.operation import run_operation
from lcoh.stack import stack_costs
from lcoh.zeitreihen import load_default_timeseries
from tests.test_power_costs import FAELLE, lade


@pytest.mark.parametrize("name", FAELLE)
def test_stacktausch(name):
    inp, ref = lade(name)
    r = run_operation(inp, load_default_timeseries())
    s = stack_costs(inp, r.full_load_hours)
    assert s.replacements == ref["B6!C4"]
    assert s.interval_years == pytest.approx(ref["B6!C5"])
    assert s.learning_average == pytest.approx(ref["B6!C6"], rel=1e-12)
    assert s.cost_per_kw == pytest.approx(ref["B6!C7"], rel=1e-12)
    assert s.total_exchange_cost == pytest.approx(ref["B6!C8"], rel=1e-12, abs=1e-9)
    assert s.total_with_interest == pytest.approx(ref["B2!G120"], rel=1e-9, abs=1e-6)
    assert s.annual_cost == pytest.approx(ref["B2!G121"], rel=1e-9, abs=1e-6)
