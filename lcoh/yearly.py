"""Gestehungskosten je Projektjahr: Preissteigerung, Degradation, Stacktausch und THG-Erlöse wirken im jeweiligen Jahr.

Die Betriebssimulation (Strommengen) bleibt über die Jahre gleich; es ändern sich Preise, Wirkungsgrad und damit die
Wasserstoffmenge. Kapitaldienst und Stackkosten werden wie im Hauptergebnis als gleichbleibende Jahresbeträge angesetzt.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from lcoh import constants as k
from lcoh.economics import Economics, compute_economics
from lcoh.operation import OperationResult


@dataclass(frozen=True)
class YearlyResult:
    table: pd.DataFrame
    lcoh_sum_ratio: float       # Summe der Nettokosten / Summe des Wasserstoffs über alle Jahre


def efficiency_by_year(r: OperationResult) -> list[float]:
    """Wirkungsgrad des Elektrolyseurs je Projektjahr (Jahresmitte): Degradation seit dem letzten Stacktausch."""
    inp = r.inputs
    interval = r.stack_interval_years
    out = []
    for y in range(1, int(inp.project_lifetime_years) + 1):
        age = (y - 0.5) % interval if interval > 0 else y - 0.5
        out.append(max(inp.electrolyzer_efficiency - inp.stack_degradation_per_year * age, 0.0))
    return out


def yearly_lcoh(r: OperationResult, e: Economics) -> YearlyResult:
    inp = r.inputs
    life = int(inp.project_lifetime_years)
    rows = []
    for y, eff in zip(range(1, life + 1), efficiency_by_year(r)):
        h2_kwh = r.ely_consumption_kwh * eff
        ry = replace(r, avg_efficiency=eff, h2_energy_kwh=h2_kwh, h2_kg_per_year=h2_kwh / k.HHV_KWH_PER_KG_H2)
        ey = compute_economics(ry, y)
        costs = ey.power_cost + ey.stack_cost_per_year + ey.opex_total + ey.financing_total
        net = costs - ey.revenue_total
        rows.append({"Jahr": y, "Kalenderjahr": inp.commissioning_year + y - 1, "Wirkungsgrad Elektrolyseur [%]": eff * 100,
                     "Wasserstoff [t/a]": ry.h2_kg_per_year / 1000, "Strom [€/a]": ey.power_cost,
                     "Stack [€/a]": ey.stack_cost_per_year, "Betrieb (OPEX) [€/a]": ey.opex_total,
                     "Kapitaldienst [€/a]": ey.financing_total, "Erlöse [€/a]": ey.revenue_total,
                     "Nettokosten [€/a]": net, "Gestehungskosten [€/kg]": ey.lcoh_eur_per_kg})
    table = pd.DataFrame(rows)
    total_h2 = table["Wasserstoff [t/a]"].sum() * 1000
    ratio = table["Nettokosten [€/a]"].sum() / total_h2 if total_h2 else 0.0
    return YearlyResult(table, ratio)
