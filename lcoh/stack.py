"""Stacktausch: Kosten, Rückstellungen und Finanzierung (Excel: Blatt 6, Spalte C, und Blatt 2 G120/G121)."""
from __future__ import annotations

from dataclasses import dataclass

from lcoh.inputs import Inputs
from lcoh.operation import stack_interval_years, stack_replacements

LEARNING_TABLE_YEARS = 20  # Die Excel mittelt die Kostendegression immer über die Projektjahre 1 bis 20


def learning_average(cost_degression: float) -> float:
    """Durchschnittliche kumulierte Kostendegression (Blatt 6, AP70).

    Hinweis: Die Excel-Tabelle hat feste 20 Spalten und mittelt immer über 20 Jahre,
    unabhängig von der eingestellten Projektlaufzeit. Das Tool übernimmt das.
    """
    vals = [1.0 if cost_degression == -1.0 else 1.0 - (1.0 + cost_degression) ** (n - 1)
            for n in range(1, LEARNING_TABLE_YEARS + 1)]
    return sum(vals) / len(vals)


def annuity_factor(rate: float, years: float) -> float:
    if rate == 0:
        return 0.0
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1)


@dataclass(frozen=True)
class StackCosts:
    replacements: int                 # Blatt 6, C4
    interval_years: float             # Blatt 6, C5
    learning_average: float           # Blatt 6, C6
    cost_per_kw: float                # Blatt 6, C7
    total_exchange_cost: float        # Blatt 6, C8
    provision_total: float            # Blatt 6, C12
    financed_amount: float            # Blatt 6, C13
    annuity: float                    # Blatt 6, C16
    interest_per_year: float          # Blatt 6, C17
    total_with_interest: float        # Blatt 6, C19 = Blatt 2 G120
    annual_cost: float                # Blatt 6, C20 = Blatt 2 G121


def stack_costs(inp: Inputs, full_load_hours: float) -> StackCosts:
    n = stack_replacements(inp, full_load_hours)
    interval = stack_interval_years(inp, n)
    lear = learning_average(inp.stack_cost_degression)
    per_kw = inp.stack_replacement_cost_share * inp.capex_electrolyzer_eur_per_kw * (1 - lear)
    total = per_kw * n * inp.electrolyzer_power_kw
    life = inp.project_lifetime_years
    t_prov = life / 2
    t_fin = life - t_prov
    prov = total / (life / t_prov)
    financed = total - prov
    rate = inp.stack_interest_rate
    af = annuity_factor(rate, t_fin)
    annuity = financed / t_fin if af == 0 else financed * af
    interest = annuity - financed / t_fin
    total_int = prov + annuity * t_fin
    return StackCosts(n, interval, lear, per_kw, total, prov, financed, annuity, interest,
                      total_int, total_int / (t_prov + t_fin))
