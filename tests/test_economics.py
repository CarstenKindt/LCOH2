import pytest

from lcoh.economics import compute_economics
from lcoh.operation import run_operation
from lcoh.zeitreihen import load_default_timeseries
from tests.test_power_costs import FAELLE, lade


@pytest.mark.parametrize("name", FAELLE)
def test_lcoh_und_zwischenwerte(name):
    inp, ref = lade(name)
    # In "klein" und "s13k" wurde die Excel-Hilfszelle F129 nicht nachgeführt: Excel rechnet mit ihrem Wert.
    fix = ref["B2!F129"] if name in ("klein", "s13k") else None
    e = compute_economics(run_operation(inp, load_default_timeseries(), fixed_interval_years=fix))
    ziele = {
        "B3!G5": e.capex_gross, "B2!F169": e.capex_subsidy, "B2!G19": e.capex_net, "B2!G20": e.capex_specific_eur_per_kw,
        "B2!F174": e.opex_subsidy, "B2!G131": e.opex_total, "B2!G159": e.financing_total,
        "B2!F198": e.revenue_thg, "B2!F208": e.revenue_power_spot, "B2!F209": e.revenue_power_ppa,
        "B2!F213": e.revenue_oxygen, "B2!F217": e.revenue_heat, "B2!F222": e.revenue_balancing,
        "B2!F227": e.revenue_other, "B2!G196": e.revenue_total, "B2!F189": e.spk,
        "B2!F3": e.lcoh_eur_per_kg, "B2!F4": e.lcoh_ct_per_kwh,
    }
    for zelle, wert in ziele.items():
        assert wert == pytest.approx(ref[zelle], rel=1e-9, abs=1e-6), zelle
