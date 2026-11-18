"""Gestehungskosten nach der Kapitalwertmethode (abgezinste Kosten geteilt durch abgezinste Wasserstoffmenge).

LCOH = (CAPEX + Summe der abgezinsten Jahreskosten + abgezinste Stacktausche - abgezinste Erlöse) / Summe der abgezinsten
Wasserstoffmengen.

Zeitpunkte: Die Investition fällt im Jahr 0 an. Betriebskosten, Erlöse und die Wasserstoffmenge eines Projektjahres t werden
am Jahresende (t) abgezinst. Ein Stacktausch wird zum Zeitpunkt k x Tauschintervall abgezinst. Preissteigerungen, Degradation
und THG-Erlöse wirken im jeweiligen Jahr (wie in der Jahresauswertung). Die Finanzierung steckt im Diskontierungssatz;
eine getrennte Annuität für Fremd- und Eigenkapital entfällt.

Damit alle Auswertungen (Wasserfall, Tabellen) unverändert weiterverwendet werden können, wird das Ergebnis zusätzlich als
"Jahresäquivalent" in der Struktur von Economics bereitgestellt: Jeder Barwert wird durch den Barwert der Wasserstoffmenge
geteilt und mit der mittleren Jahresmenge multipliziert. Dividiert durch die Jahresmenge ergibt das genau den Beitrag je kg.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from lcoh import constants as k
from lcoh.economics import Economics, compute_economics
from lcoh.operation import OperationResult
from lcoh.yearly import efficiency_by_year

METHOD_ANNUITY = "Annuitätenmethode"
METHOD_NPV = "Kapitalwertmethode"
RATE_WACC = "WACC aus Finanzierung"
RATE_OWN = "Eigener Wert"

_OPEX_FIELDS = ("opex_maintenance", "opex_personnel", "opex_provisions", "opex_water", "opex_other", "opex_subsidy", "opex_total", "water_cost")
_REV_FIELDS = ("revenue_thg", "revenue_power_spot", "revenue_power_ppa", "revenue_oxygen", "revenue_heat",
               "revenue_balancing", "revenue_other", "revenue_total")
_PC_FIELDS = ("cost_pv", "cost_wind", "cost_baseload", "cost_13k", "cost_s7", "cost_spot", "cost_levies_ely", "cost_levies_rest",
              "cost_total_before_subsidy", "power_subsidy", "cost_total", "sale_revenue_spot", "sale_revenue_ppa", "demand_charge_eur")
_PC_DICTS = ("levy_full_eur", "levy_actual_eur", "levy_privilege_eur")


@dataclass(frozen=True)
class NpvResult:
    rate: float
    lcoh_eur_per_kg: float
    pv_h2_kg: float               # Barwert der Wasserstoffmenge
    pv_costs: float               # Barwert aller Kosten inkl. CAPEX
    pv_revenue: float
    table: pd.DataFrame           # Jahrestabelle mit Abzinsungsfaktoren
    economics: Economics          # Jahresäquivalent (für Wasserfall und Tabellen)


def discount_rate(inp, wacc: float) -> float:
    return wacc if inp.discount_rate_mode == RATE_WACC else inp.discount_rate


def npv_lcoh(r: OperationResult, e_ann: Economics) -> NpvResult:
    inp = r.inputs
    life = int(inp.project_lifetime_years)
    rate = max(discount_rate(inp, e_ann.wacc), 0.0)
    h2avg = e_ann.h2_kg_per_year

    ys, df_list, h2_list, eco = [], [], [], []
    for y, eff in zip(range(1, life + 1), efficiency_by_year(r)):
        h2_kwh = r.ely_consumption_kwh * eff
        ry = replace(r, avg_efficiency=eff, h2_energy_kwh=h2_kwh, h2_kg_per_year=h2_kwh / k.HHV_KWH_PER_KG_H2)
        ys.append(y)
        eco.append(compute_economics(ry, y))
        df_list.append((1.0 + rate) ** -y)
        h2_list.append(ry.h2_kg_per_year)

    pv_h2 = sum(h * d for h, d in zip(h2_list, df_list))
    if not pv_h2 or not h2avg:
        return NpvResult(rate, 0.0, 0.0, 0.0, 0.0, pd.DataFrame(), e_ann)
    g = h2avg / pv_h2

    def pv(fn) -> float:
        return sum(fn(ey) * d for ey, d in zip(eco, df_list))

    # Stacktausch: Kosten je Tausch zum Zeitpunkt k x Intervall
    sc = e_ann.stack
    stack_pv = 0.0
    if sc.replacements > 0:
        each = sc.total_exchange_cost / sc.replacements
        stack_pv = sum(each * (1.0 + rate) ** -(n * sc.interval_years) for n in range(1, sc.replacements + 1))

    pv_power = pv(lambda x: x.power_cost)
    pv_opex = pv(lambda x: x.opex_total)
    pv_rev = pv(lambda x: x.revenue_total)
    capex_net = e_ann.capex_net
    lcoh = (capex_net + pv_power + pv_opex + stack_pv - pv_rev) / pv_h2

    # ---- Jahresäquivalent
    upd = {"power_cost": pv_power * g, "stack_cost_per_year": stack_pv * g}
    for name in _OPEX_FIELDS + _REV_FIELDS:
        upd[name] = pv(lambda x, n=name: getattr(x, n)) * g
    pc_upd = {name: pv(lambda x, n=name: getattr(x.power, n)) * g for name in _PC_FIELDS}
    for name in _PC_DICTS:
        keys = getattr(e_ann.power, name).keys()
        pc_upd[name] = {kk: pv(lambda x, n=name, q=kk: getattr(x.power, n)[q]) * g for kk in keys}
    financing = capex_net * g
    interest = financing - capex_net / life
    stack_eq = replace(sc, annual_cost=stack_pv * g)
    eq = replace(
        e_ann, **upd, power=replace(e_ann.power, **pc_upd), stack=stack_eq,
        financing_total=financing, debt_annuity=financing * inp.debt_share, equity_annuity=financing * (1 - inp.debt_share),
        interest_cost=interest)
    cost_eq = eq.stack.annual_cost + eq.opex_total + eq.power_cost + eq.financing_total
    lcoh_eq = (cost_eq - eq.revenue_total) / h2avg
    eq = replace(eq, lcoh_eur_per_kg=lcoh_eq, lcoh_ct_per_kwh=lcoh_eq * k.CT_PER_EUR / k.HHV_KWH_PER_KG_H2)

    table = pd.DataFrame({
        "Jahr": ys, "Abzinsungsfaktor": df_list, "Wasserstoff [t/a]": [h / 1000 for h in h2_list],
        "Strom [€/a]": [ey.power_cost for ey in eco], "Betrieb (OPEX) [€/a]": [ey.opex_total for ey in eco],
        "Erlöse [€/a]": [ey.revenue_total for ey in eco],
        "Barwert Nettokosten [€]": [(ey.power_cost + ey.opex_total - ey.revenue_total) * d for ey, d in zip(eco, df_list)],
        "Barwert Wasserstoff [t]": [h / 1000 * d for h, d in zip(h2_list, df_list)]})
    return NpvResult(rate, lcoh, pv_h2, capex_net + pv_power + pv_opex + stack_pv, pv_rev, table, eq)
