import pytest

from lcoh.economics import compute_economics
from lcoh.operation import run_operation
from lcoh.waterfall import BLOCK_CAPEX, BLOCK_INTEREST, BLOCK_OPEX, BLOCK_POWER, BLOCK_STACK, waterfall_items
from lcoh.zeitreihen import load_default_timeseries
from tests.test_power_costs import FAELLE, lade


@pytest.mark.parametrize("name", FAELLE)
@pytest.mark.parametrize("ansicht", ["quelle", "verbraucher"])
def test_wasserfall_summe_ist_lcoh(name, ansicht):
    inp, ref = lade(name)
    r = run_operation(inp, load_default_timeseries())
    e = compute_economics(r)
    items = waterfall_items(r, e, ansicht)
    assert sum(i.eur_per_kg for i in items) == pytest.approx(e.lcoh_eur_per_kg, rel=1e-9, abs=1e-9)
    # Zwischenergebnis (Kosten ohne Förderungen und Befreiungen) wie Excel Blatt 7, R3
    bloecke = (BLOCK_CAPEX, BLOCK_OPEX, BLOCK_STACK, BLOCK_POWER, BLOCK_INTEREST)
    zwischen = sum(i.eur_per_kg for i in items if i.block in bloecke)
    assert zwischen == pytest.approx((e.capex_gross / inp.project_lifetime_years + e.opex_total + e.opex_subsidy
                                      + e.stack.annual_cost + e.interest_cost + sum(e.power.levy_full_eur.values())
                                      + e.power.demand_charge_eur + (e.power.cost_pv + e.power.cost_wind + e.power.cost_baseload
                                      + e.power.cost_13k + e.power.cost_s7 + e.power.cost_spot)) / e.h2_kg_per_year, rel=1e-9)


@pytest.mark.parametrize("name", FAELLE)
@pytest.mark.parametrize("ansicht", ["quelle", "verbraucher"])
def test_wasserfall_netto_summe_ist_lcoh(name, ansicht):
    from lcoh.waterfall import net_power_items
    inp, ref = lade(name)
    r = run_operation(inp, load_default_timeseries())
    e = compute_economics(r)
    if ansicht == "verbraucher":
        items = waterfall_items(r, e, "verbraucher", netto=True)
    else:
        items = net_power_items(waterfall_items(r, e, "quelle"))
    assert sum(i.eur_per_kg for i in items) == pytest.approx(e.lcoh_eur_per_kg, rel=1e-9, abs=1e-9)
    assert not [i for i in items if i.label.startswith("Befreiung ") and i.block != BLOCK_POWER]
