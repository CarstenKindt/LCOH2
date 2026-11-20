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

PARAMETERS = ["THG-Minderungsmenge", "Zinsen (FK + EK)", "OPEX", "Projektlaufzeit", "CAPEX", "Volllaststunden", "Strompreis"]


@dataclass(frozen=True)
class SensitivityRow:
    name: str
    lcoh_minus: float   # Einflussgröße um die Schrittweite verringert
    lcoh_plus: float    # Einflussgröße um die Schrittweite erhöht
    base: float
    block: str = ""           # betroffener Kostenblock mit Einheit
    v_minus: float = 0.0      # Wert des Kostenblocks bei verringerter Einflussgröße
    v_base: float = 0.0
    v_plus: float = 0.0
    setting: str = ""         # veränderte Einstellgröße (Text), falls sinnvoll

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
                o2=e.revenue_oxygen, heat=e.revenue_heat, spot=spot, thg=e.revenue_thg, bal=bal, h2=h2)

    def lcoh(**ch) -> float:
        v = {**base, **ch}
        cost = v["fin"] + v["opex"] + v["power"] + v["stack"]
        rev = v["o2"] + v["heat"] + v["spot"] + v["thg"] + v["bal"]
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

    def de(x: float, n: int = 1) -> str:
        return f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def add(name: str, fn, block: str, vfn, setting=None) -> None:
        rows.append(SensitivityRow(
            name, fn(-step), fn(+step), e.lcoh_eur_per_kg, block, vfn(-step), vfn(0.0), vfn(step),
            "" if setting is None else f"{setting(-step)} | {setting(0.0)} | {setting(step)}"))

    def fin_zins(s):
        return financing(e.capex_net, inp.debt_interest_rate * (1 + s), inp.equity_interest_rate * (1 + s), life)

    def fin_life(s):
        return financing(e.capex_net, inp.debt_interest_rate, inp.equity_interest_rate, life * (1 + s))

    add("THG-Minderungsmenge", lambda s: lcoh(thg=e.revenue_thg * (1 + s)), "THG-Erlöse [€/a]", lambda s: e.revenue_thg * (1 + s))
    add("Zinsen (FK + EK)", lambda s: lcoh(fin=fin_zins(s), stack=stack(rate=inp.stack_interest_rate * (1 + s))),
        "Kapitalkosten [€/a]", fin_zins,
        lambda s: f"FK {de(inp.debt_interest_rate * (1 + s) * 100)} % / EK {de(inp.equity_interest_rate * (1 + s) * 100)} %")
    add("OPEX", lambda s: lcoh(opex=e.opex_total * (1 + s)), "OPEX [€/a]", lambda s: e.opex_total * (1 + s))
    add("Projektlaufzeit", lambda s: lcoh(fin=fin_life(s), stack=stack(life=life * (1 + s))),
        "Kapitalkosten [€/a]", fin_life, lambda s: f"{de(life * (1 + s))} a")
    add("CAPEX", lambda s: lcoh(fin=financing(e.capex_net * (1 + s), inp.debt_interest_rate,
                                              inp.equity_interest_rate, life)),
        "CAPEX [€]", lambda s: e.capex_net * (1 + s))

    def flh_of(s: float) -> float:
        return min(r.full_load_hours * (1 + s), 8760.0)

    def full_load(s: float) -> float:
        flh = flh_of(s)
        f = flh / r.full_load_hours
        return lcoh(power=e.power_cost * f, stack=stack(flh=flh), o2=e.revenue_oxygen * f, heat=e.revenue_heat * f,
                    spot=spot * f, thg=e.revenue_thg * f, h2=h2 * f)

    add("Volllaststunden", full_load, "Stromkosten [€/a]", lambda s: e.power_cost * flh_of(s) / r.full_load_hours,
        lambda s: f"{de(flh_of(s), 0)} h/a")
    avg_price = e.power_cost / (e.power.total_procurement_kwh / 1000) if e.power.total_procurement_kwh else 0.0
    add("Strompreis", lambda s: lcoh(power=e.power_cost * (1 + s)),
        "Stromkosten [€/a]", lambda s: e.power_cost * (1 + s), lambda s: f"{de(avg_price * (1 + s), 2)} €/MWh")
    return rows


def sensitivity_npv(r: OperationResult, e: Economics, step: float) -> list[SensitivityRow]:
    """Sensitivität nach der Kapitalwertmethode.

    Je Einflussgröße wird nur diese Größe um +/- Schrittweite verändert. Barwerte von Strom, OPEX, THG-Erlösen und CAPEX
    werden direkt skaliert; Zinsen und Projektlaufzeit werden vollständig neu gerechnet (Abzinsung, Stacktausch, Jahre).
    Die Werte der Kostenblöcke sind Barwerte über die Projektlaufzeit."""
    from dataclasses import replace
    from lcoh.economics import compute_economics
    from lcoh.npv import npv_lcoh
    from lcoh.operation import stack_interval_years, stack_replacements
    from lcoh.stack import stack_costs

    inp = r.inputs
    n = npv_lcoh(r, e)
    if not n.pv_h2_kg:
        return []
    base = dict(capex=n.capex_net, power=n.pv_power, opex=n.pv_opex, stack=n.pv_stack, thg=n.pv_thg,
                rev_other=n.pv_revenue - n.pv_thg, h2=n.pv_h2_kg)

    def lc(**ch) -> float:
        v = {**base, **ch}
        return (v["capex"] + v["power"] + v["opex"] + v["stack"] - v["thg"] - v["rev_other"]) / v["h2"]

    def neu(**kw):
        inp2 = replace(inp, **kw)
        nrep = stack_replacements(inp2, r.full_load_hours)
        r2 = replace(r, inputs=inp2, stack_replacements=nrep, stack_interval_years=stack_interval_years(inp2, nrep))
        return npv_lcoh(r2, compute_economics(r2))

    def de(x: float, k: int = 1) -> str:
        return f"{x:,.{k}f}".replace(",", "X").replace(".", ",").replace("X", ".")

    rows = []

    def add(name, fn, block, vfn, setting=None):
        rows.append(SensitivityRow(name, fn(-step), fn(step), n.lcoh_eur_per_kg, block, vfn(-step), vfn(0.0), vfn(step),
                                   "" if setting is None else f"{setting(-step)} | {setting(0.0)} | {setting(step)}"))

    add("THG-Minderungsmenge", lambda s: lc(thg=n.pv_thg * (1 + s)), "Barwert THG-Erlöse [€]", lambda s: n.pv_thg * (1 + s))
    zins = {s: neu(debt_interest_rate=inp.debt_interest_rate * (1 + s), equity_interest_rate=inp.equity_interest_rate * (1 + s),
                   stack_interest_rate=inp.stack_interest_rate * (1 + s)) for s in (-step, step)}
    add("Zinsen (FK + EK)", lambda s: zins[s].lcoh_eur_per_kg, "Kapitalkostensatz [%]",
        lambda s: (zins[s].rate if s else n.rate) * 100,
        lambda s: f"FK {de(inp.debt_interest_rate * (1 + s) * 100)} % / EK {de(inp.equity_interest_rate * (1 + s) * 100)} %")
    add("OPEX", lambda s: lc(opex=n.pv_opex * (1 + s)), "Barwert OPEX [€]", lambda s: n.pv_opex * (1 + s))
    life = inp.project_lifetime_years
    lz = {s: neu(project_lifetime_years=max(1, round(life * (1 + s)))) for s in (-step, step)}
    add("Projektlaufzeit", lambda s: lz[s].lcoh_eur_per_kg, "Projektlaufzeit [a]",
        lambda s: float(max(1, round(life * (1 + s)))), lambda s: f"{max(1, round(life * (1 + s)))} a")
    add("CAPEX", lambda s: lc(capex=n.capex_net * (1 + s)), "CAPEX [€]", lambda s: n.capex_net * (1 + s))

    def flh_of(s: float) -> float:
        return min(r.full_load_hours * (1 + s), 8760.0)

    def full_load(s: float) -> float:
        f = flh_of(s) / r.full_load_hours
        stk = stack_costs(inp, flh_of(s)).annual_cost * n.discount_sum
        return lc(power=n.pv_power * f, thg=n.pv_thg * f, rev_other=base["rev_other"] * f, h2=n.pv_h2_kg * f, stack=stk)

    add("Volllaststunden", full_load, "Barwert Stromkosten [€]", lambda s: n.pv_power * flh_of(s) / r.full_load_hours,
        lambda s: f"{de(flh_of(s), 0)} h/a")
    avg_price = e.power_cost / (e.power.total_procurement_kwh / 1000) if e.power.total_procurement_kwh else 0.0
    add("Strompreis", lambda s: lc(power=n.pv_power * (1 + s)), "Barwert Stromkosten [€]", lambda s: n.pv_power * (1 + s),
        lambda s: f"{de(avg_price * (1 + s), 2)} €/MWh")
    return rows
