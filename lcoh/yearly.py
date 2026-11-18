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


def yearly_lcoh(r: OperationResult, e: Economics, rate: float | None = None,
                capital_service: float | None = None, stack_service: float | None = None) -> YearlyResult:
    """Gestehungskosten je Projektjahr. Mit `rate` (Kapitalwertmethode) werden Kapitaldienst und Stackkosten als Annuität zum
    Diskontierungssatz angesetzt und das Gesamtergebnis abgezinst gewichtet."""
    inp = r.inputs
    life = int(inp.project_lifetime_years)
    rows = []
    for y, eff in zip(range(1, life + 1), efficiency_by_year(r)):
        h2_kwh = r.ely_consumption_kwh * eff
        ry = replace(r, avg_efficiency=eff, h2_energy_kwh=h2_kwh, h2_kg_per_year=h2_kwh / k.HHV_KWH_PER_KG_H2)
        ey = compute_economics(ry, y)
        fin = ey.financing_total if capital_service is None else capital_service
        stk = ey.stack_cost_per_year if stack_service is None else stack_service
        costs = ey.power_cost + stk + ey.opex_total + fin
        net = costs - ey.revenue_total
        rows.append({"Jahr": y, "Kalenderjahr": inp.commissioning_year + y - 1, "Wirkungsgrad Elektrolyseur [%]": eff * 100,
                     "Wasserstoff [t/a]": ry.h2_kg_per_year / 1000, "Strom [€/a]": ey.power_cost,
                     "Stack [€/a]": stk, "Betrieb (OPEX) [€/a]": ey.opex_total,
                     "Kapitaldienst [€/a]": fin, "Erlöse [€/a]": ey.revenue_total,
                     "Nettokosten [€/a]": net, "Gestehungskosten [€/kg]": net / ry.h2_kg_per_year if ry.h2_kg_per_year else 0.0})
    table = pd.DataFrame(rows)
    w = [1.0] * len(table) if rate is None else [(1.0 + rate) ** -y for y in table["Jahr"]]
    total_h2 = sum(h * d for h, d in zip(table["Wasserstoff [t/a]"], w)) * 1000
    ratio = sum(n * d for n, d in zip(table["Nettokosten [€/a]"], w)) / total_h2 if total_h2 else 0.0
    return YearlyResult(table, ratio)
