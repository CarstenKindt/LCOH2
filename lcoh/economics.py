"""Wirtschaftlichkeit: CAPEX, OPEX, Finanzierung, Förderungen, Erlöse und LCOH (Excel: Blatt 2, Blatt 3)."""
from __future__ import annotations

from dataclasses import dataclass

from lcoh import constants as k
from lcoh.inputs import Inputs
from lcoh.operation import OperationResult
from lcoh.power_costs import PowerCosts, power_costs
from lcoh.prices import average_escalation_factor
from lcoh.stack import StackCosts, stack_costs
from lcoh.system import h2_compressor_work_kwh_per_kg, o2_compressor_work_kwh_per_kg

# THG-Quote: Jahr -> (Minderungsquote, Basiswert kg CO2/GJ, Anrechnungsfaktor); Excel Blatt 3, L5:AJ14
THG_FIRST_YEAR = 2026
THG_QUOTA = [0.12, 0.175, 0.195, 0.225, 0.265, 0.30, 0.33, 0.36, 0.38, 0.41, 0.46, 0.51, 0.56, 0.61] + [0.65] * 11
THG_CREDIT = [3.0] * 11 + [2.5, 2.0, 1.5] + [1.0] * 11
THG_BASE_VALUE = 94.0
THG_KG_CO2_PER_KG_H2_FACTOR = 0.1201
THG_PRICE_CAP_EUR_PER_T = 600.0


def _esc(price: float, g: float, years: float) -> float:
    return price * average_escalation_factor(g, years)


def thg_revenue_per_year(inp: Inputs, h2_kg: float) -> float:
    """Durchschnittliche THG-Erlöse pro Jahr (Blatt 3, L4). Erlöse nur in den Projektjahren ab Inbetriebnahme."""
    if not inp.thg_enabled:
        return 0.0
    life = inp.project_lifetime_years
    price = inp.thg_price_eur_per_t
    total = 0.0
    for i, (quota, credit) in enumerate(zip(THG_QUOTA, THG_CREDIT)):
        year = THG_FIRST_YEAR + i
        if i > 0:
            price = min(price * (1 + inp.thg_price_escalation), THG_PRICE_CAP_EUR_PER_T)
        if year < inp.commissioning_year or year - inp.commissioning_year > life - 1:
            continue
        adj = 0.4 if inp.thg_adjustment_factor == 0.4 else 1.0
        target = (1 - quota) * THG_BASE_VALUE
        ghg = inp.thg_h2_intensity_kgco2_per_gj * adj
        per_kg = (target - ghg) * credit * THG_KG_CO2_PER_KG_H2_FACTOR
        tonnes = inp.thg_mobility_share * h2_kg * per_kg / k.KG_PER_TONNE
        total += tonnes * price * inp.thg_producer_share
    return total / life


@dataclass(frozen=True)
class Economics:
    # CAPEX und Förderung
    capex_gross: float          # Blatt 3, G5
    capex_subsidy: float        # Blatt 2, F169
    capex_net: float            # Blatt 2, G19
    capex_specific_eur_per_kw: float  # Blatt 2, G20
    battery_capex: float
    # OPEX
    opex_maintenance: float
    opex_personnel: float
    opex_provisions: float
    opex_water: float
    opex_other: float
    opex_subsidy: float         # Blatt 2, F174
    opex_total: float           # Blatt 2, G131
    # Strom und Stack
    power_cost: float           # Blatt 2, G59
    stack_cost_per_year: float  # Blatt 2, G121
    # Finanzierung
    debt: float
    debt_annuity: float
    equity: float
    equity_annuity: float
    financing_total: float      # Blatt 2, G159
    # Erlöse
    revenue_thg: float
    revenue_power_spot: float
    revenue_power_ppa: float
    revenue_oxygen: float
    revenue_heat: float
    revenue_balancing: float
    revenue_other: float
    revenue_total: float        # Blatt 2, G196
    spk: float                  # Blatt 2, F189
    # Ergebnis
    h2_kg_per_year: float
    lcoh_eur_per_kg: float      # Blatt 2, F3
    lcoh_ct_per_kwh: float      # Blatt 2, F4
    power: PowerCosts
    stack: StackCosts
    capex_items: dict           # CAPEX je Position in EUR (brutto)
    interest_cost: float        # Zinskosten Fremd- und Eigenkapital pro Jahr (Blatt 3, C63)
    wacc: float                 # Blatt 2, F17
    water_cost: float


def compute_economics(r: OperationResult) -> Economics:
    inp, p = r.inputs, r.power
    life = inp.project_lifetime_years
    ely_kw = inp.electrolyzer_power_kw
    h2 = r.h2_kg_per_year
    pc = power_costs(r)
    sc = stack_costs(inp, r.full_load_hours)

    def esc(price: float, g: float) -> float:
        return _esc(price, g, life)

    # ---- CAPEX (Blatt 2, F23:F54 und Blatt 3, G5)
    per_kw = inp.capex_electrolyzer_eur_per_kw + inp.capex_epc_eur_per_kw + inp.capex_bop_eur_per_kw
    per_kw += inp.capex_building_eur_per_kw + inp.capex_civil_eur_per_kw
    per_kw += inp.capex_waste_heat_eur_per_kw if inp.waste_heat_enabled else 0.0
    per_kw += inp.capex_oxygen_eur_per_kw if inp.oxygen_enabled else 0.0
    per_kw += inp.capex_h2_compression_eur_per_kw if inp.h2_processing_mode == "Verdichtung" else inp.capex_h2_direct_eur_per_kw
    battery = (p.battery_capacity_kwh * inp.battery_capex_eur_per_kwh + inp.battery_other_costs_eur) if inp.battery_enabled else 0.0
    custom = (inp.capex_custom_1_eur_per_kw + inp.capex_custom_2_share_of_electrolyzer * inp.capex_electrolyzer_eur_per_kw
              + (inp.capex_custom_3_eur / ely_kw if ely_kw else 0.0)) if ely_kw else 0.0
    capex = per_kw * ely_kw + battery + custom * ely_kw
    capex_items = {
        "Elektrolyseur": inp.capex_electrolyzer_eur_per_kw * ely_kw,
        "EPC": inp.capex_epc_eur_per_kw * ely_kw,
        "Balance of Plant": inp.capex_bop_eur_per_kw * ely_kw,
        "Gebäude und Tiefbau": (inp.capex_building_eur_per_kw + inp.capex_civil_eur_per_kw) * ely_kw,
        "Abwärmesystem": (inp.capex_waste_heat_eur_per_kw if inp.waste_heat_enabled else 0.0) * ely_kw,
        "Sauerstoffsystem": (inp.capex_oxygen_eur_per_kw if inp.oxygen_enabled else 0.0) * ely_kw,
        "H2-Aufbereitung": (inp.capex_h2_compression_eur_per_kw if inp.h2_processing_mode == "Verdichtung"
                            else inp.capex_h2_direct_eur_per_kw) * ely_kw,
        "Batteriesystem": battery,
        "Individuelle CAPEX": custom * ely_kw,
    }

    mode = inp.capex_subsidy_mode.lower()
    if mode == "prozentual":
        subsidy = inp.capex_subsidy_percent * capex
    elif mode == "absolut":
        subsidy = inp.capex_subsidy_eur_per_kw * ely_kw
    else:
        subsidy = 0.0
    capex_net = capex - subsidy
    capex_per_kw = (capex_net / ely_kw) if ely_kw else 0.0

    # ---- OPEX-Förderung (Blatt 2, F174)
    omode = inp.opex_subsidy_mode.lower()
    if omode == "pro kg":
        opex_subsidy = h2 * inp.opex_subsidy_eur_per_kg
    elif omode == "pro volllaststunde":
        opex_subsidy = r.full_load_hours * inp.opex_subsidy_eur_per_full_load_hour
    else:
        opex_subsidy = 0.0

    # ---- OPEX (Blatt 3, G68:G83)
    maintenance = esc(capex * inp.maintenance_share_of_capex, inp.maintenance_escalation)
    personnel = esc(inp.personnel_eur_per_year, inp.personnel_escalation)
    reserve = esc(capex * inp.replacement_reserve_share_of_capex, inp.reserves_escalation)
    decom = esc(capex * inp.decommissioning_share_of_capex, inp.reserves_escalation)
    provisions = reserve + decom
    fresh_m3 = h2 * k.WATER_KG_PER_KG_H2 * k.WATER_REAL_FACTOR / k.LITER_PER_M3
    waste_m3 = fresh_m3 - h2 * k.WATER_KG_PER_KG_H2 / k.LITER_PER_M3
    water = esc(fresh_m3 * inp.water_fresh_eur_per_m3 + fresh_m3 * inp.water_treatment_eur_per_m3
                + waste_m3 * inp.water_waste_eur_per_m3, inp.water_escalation)
    other = esc(capex * inp.other_opex_share_of_capex, inp.other_opex_escalation)
    if not inp.opex_lump_sum_enabled:
        opex = maintenance + personnel + provisions + water + other - opex_subsidy
    else:
        opex = esc(inp.opex_lump_sum_share_of_capex * capex_net, inp.opex_lump_sum_escalation) - opex_subsidy

    # ---- Finanzierung (Blatt 2, F161:G159)
    def annuity(amount: float, rate: float) -> float:
        return amount / life if rate == 0 else amount * rate / (1 - (1 + rate) ** -life)
    debt = capex_net * inp.debt_share
    equity = capex_net * (1 - inp.debt_share)
    a_debt, a_equity = annuity(debt, inp.debt_interest_rate), annuity(equity, inp.equity_interest_rate)
    financing = a_debt + a_equity
    interest = financing - capex_net / life
    wacc = (inp.equity_interest_rate * (1 - inp.debt_share)
            + inp.debt_interest_rate * inp.debt_share * (1 - inp.corporate_tax_rate))

    # ---- Erlöse (Blatt 3, K20:L50)
    thg = thg_revenue_per_year(inp, h2)
    o2_kg = h2 * k.O2_KG_PER_KG_H2
    oxygen = (o2_kg / k.KG_PER_TONNE * esc(inp.oxygen_price_eur_per_t, inp.oxygen_price_escalation)) if inp.oxygen_enabled else 0.0
    heat = 0.0
    if inp.waste_heat_enabled:
        heat_ely = r.ely_consumption_kwh * (1 - r.avg_efficiency) / k.KWH_PER_MWH
        heat_o2 = (o2_compressor_work_kwh_per_kg(inp) * o2_kg / k.KWH_PER_MWH) * (1 - inp.o2_compressor_efficiency) if inp.oxygen_enabled else 0.0
        heat_h2 = (h2_compressor_work_kwh_per_kg(inp) * h2 / k.KWH_PER_MWH) * (1 - inp.h2_compressor_efficiency) \
            if inp.h2_processing_mode == "Verdichtung" else 0.0
        heat = (heat_ely + heat_o2 + heat_h2) * inp.heat_usable_share * esc(inp.heat_price_eur_per_mwh, inp.heat_price_escalation)
    balancing = esc(inp.balancing_revenue_eur_per_year, inp.balancing_escalation) if inp.balancing_enabled else 0.0
    other_rev = (esc(inp.other_revenue_1_eur_per_year, inp.other_revenue_1_escalation)
                 + esc(inp.other_revenue_2_eur_per_year, inp.other_revenue_2_escalation)) if inp.other_revenue_enabled else 0.0
    revenue = thg + pc.sale_revenue_spot + pc.sale_revenue_ppa + oxygen + heat + balancing + other_rev

    # ---- Strompreiskompensation (Blatt 3, L39)
    smode = inp.spk_mode.lower()
    if smode == "separat":
        spk = esc(inp.spk_separate_revenue_eur, inp.spk_escalation)
    elif smode == "rechner":
        eua = esc(inp.spk_eua_price_eur_per_t, inp.spk_escalation)
        fallback = (0.8 + (0.8 - 0.0109 * life)) / 2
        consumption_mwh = pc.consumption_total_kwh * inp.spk_consumption_factor / k.KWH_PER_MWH
        spk = 0.75 * 0.72 * eua * fallback * consumption_mwh
    else:
        spk = 0.0

    lcoh = 0.0 if h2 == 0 else (sc.annual_cost + opex + pc.cost_total + financing - spk - revenue) / h2
    return Economics(
        capex, subsidy, capex_net, capex_per_kw, battery,
        maintenance, personnel, provisions, water, other, opex_subsidy, opex,
        pc.cost_total, sc.annual_cost, debt, a_debt, equity, a_equity, financing,
        thg, pc.sale_revenue_spot, pc.sale_revenue_ppa, oxygen, heat, balancing, other_rev, revenue, spk,
        h2, lcoh, lcoh * k.CT_PER_EUR / k.HHV_KWH_PER_KG_H2, pc, sc, capex_items, interest, wacc, water)
