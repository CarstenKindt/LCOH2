"""Sensitivitätsanalyse nach Excel Blatt 7 (B2:K10).

Je Einflussgröße wird genau diese Größe um +/- Schrittweite verändert und alle anderen Kostenblöcke
bleiben auf dem Basiswert (wie in der Excel). Das ist eine Block-Sensitivität: Bei "CAPEX" ändern sich also
nur die Kapitalkosten, nicht zugleich die prozentual vom CAPEX abhängigen OPEX.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from lcoh.economics import Economics
from lcoh.operation import OperationResult
from lcoh.stack import annuity_factor

PARAMETERS = ["THG-Quote", "Zinsen (FK + EK)", "OPEX", "Projektlaufzeit", "CAPEX", "Volllaststunden", "Strompreis"]


@dataclass(frozen=True)
class SensitivityRow:
    name: str
    lcoh_minus: float   # Einflussgröße um die Schrittweite verringert
    lcoh_plus: float    # Einflussgröße um die Schrittweite erhöht
    base: float

    @property
    def low(self) -> float:
        return min(self.lcoh_minus, self.lcoh_plus)

    @property
    def high(self) -> float:
        return max(self.lcoh_minus, self.lcoh_plus)


def _annuity(amount: float, rate: float, years: float) -> float:
    return amount / years if rate <= 0 else amount * rate / (1 - (1 + rate) ** -years)


def stack_annual_cost_excel(r: OperationResult, life: float, flh: float, rate: float) -> float:
    """Jährliche Stack-Kosten (Rückstellung + Zinsen) wie in den Szenarioblöcken von Excel Blatt 6 (G:K, P:S).

    Die Szenarien rechnen die Kostendegression mit der geschlossenen Formel 1-(1+d)^((Laufzeit-2)/2); die
    Basisrechnung mittelt dagegen eine 20-Jahres-Tabelle. Dieser kleine Unterschied ist in der Excel so angelegt
    und wird hier übernommen."""
    inp = r.inputs
    base_life = inp.project_lifetime_years
    n = math.floor(flh * life / inp.stack_lifetime_h) if life * flh > inp.stack_lifetime_h else 0
    learn = 1 - (1 + inp.stack_cost_degression) ** ((life - 2) / 2)
    total = n * inp.stack_replacement_cost_share * inp.capex_electrolyzer_eur_per_kw * (1 - learn) * inp.electrolyzer_power_kw
    t_prov = life / 2
    t_fin = life - t_prov
    provision = total / (base_life / t_prov)
    financed = total - provision
    af = annuity_factor(rate, t_fin)
    annuity = financed / t_fin if af == 0 else financed * af
    interest = annuity - financed / t_fin
    return provision / t_prov + interest * t_prov / life


def sensitivity(r: OperationResult, e: Economics, step: float) -> list[SensitivityRow]:
    inp, h2, life = r.inputs, e.h2_kg_per_year, r.inputs.project_lifetime_years
    if not h2:
        return []
    spot = e.revenue_power_spot + e.revenue_power_ppa
    bal = e.revenue_balancing + e.revenue_other
    base = dict(fin=e.financing_total, opex=e.opex_total, power=e.power_cost, stack=e.stack_cost_per_year,
                o2=e.revenue_oxygen, heat=e.revenue_heat, spot=spot, thg=e.revenue_thg, bal=bal, spk=e.spk, h2=h2)

    def lcoh(**ch) -> float:
        v = {**base, **ch}
        cost = v["fin"] + v["opex"] + v["power"] + v["stack"]
        rev = v["o2"] + v["heat"] + v["spot"] + v["thg"] + v["bal"] + v["spk"]
        return (cost - rev) / v["h2"]

    def financing(capex_net: float, rate_d: float, rate_e: float, years: float) -> float:
        debt = capex_net * inp.debt_share
        equity = capex_net * (1 - inp.debt_share)
        return _annuity(debt, rate_d, years) + _annuity(equity, rate_e, years)

    def stack(life=None, flh=None, rate=None) -> float:
        return stack_annual_cost_excel(r, life or life_base, r.full_load_hours if flh is None else flh,
                                       inp.stack_interest_rate if rate is None else rate)

    life_base = life
    rows = []

    def add(name: str, fn) -> None:
        rows.append(SensitivityRow(name, fn(-step), fn(+step), e.lcoh_eur_per_kg))

    add("THG-Quote", lambda s: lcoh(thg=e.revenue_thg * (1 + s)))
    add("Zinsen (FK + EK)", lambda s: lcoh(
        fin=financing(e.capex_net, inp.debt_interest_rate * (1 + s), inp.equity_interest_rate * (1 + s), life),
        stack=stack(rate=inp.stack_interest_rate * (1 + s))))
    add("OPEX", lambda s: lcoh(opex=e.opex_total * (1 + s)))
    add("Projektlaufzeit", lambda s: lcoh(
        fin=financing(e.capex_net, inp.debt_interest_rate, inp.equity_interest_rate, life * (1 + s)),
        stack=stack(life=life * (1 + s))))
    add("CAPEX", lambda s: lcoh(fin=financing(e.capex_net * (1 + s), inp.debt_interest_rate, inp.equity_interest_rate, life)))

    def full_load(s: float) -> float:
        flh = min(r.full_load_hours * (1 + s), 8760.0)
        f = flh / r.full_load_hours
        return lcoh(power=e.power_cost * f, stack=stack(flh=flh), o2=e.revenue_oxygen * f, heat=e.revenue_heat * f,
                    spot=spot * f, thg=e.revenue_thg * f, spk=e.spk * f, h2=h2 * f)

    add("Volllaststunden", full_load)
    add("Strompreis", lambda s: lcoh(power=e.power_cost * (1 + s), spk=e.spk * (1 + s)))
    return rows
