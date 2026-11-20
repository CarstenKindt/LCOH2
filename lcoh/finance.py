"""Weitere wirtschaftliche Kennzahlen bei einem vorgegebenen Wasserstoffpreis (Marge oder Zielverkaufspreis).

Grundlage sind dieselben Jahreswerte wie bei den Gestehungskosten (Kapitalwertmethode): Kosten, Erlöse und
Wasserstoffmengen jedes Projektjahres, nominal, ohne Steuern. Der Stacktausch geht als gleichbleibender Jahresbetrag ein.

- Projektsicht (Gesamtkapital): Investition in Jahr 0, danach operativer Cashflow (CFADS). Kapitalwert mit dem
  Kapitalkostensatz (WACC), interner Zinsfuß, statische und dynamische Amortisation.
- Eigenkapitalsicht: Das Fremdkapital wird als Annuitätendarlehen zum Fremdkapitalzins über die Projektlaufzeit getilgt.
  Eigenkapital-Cashflow = CFADS − Kapitaldienst Fremdkapital. Eigenkapitalrendite (IRR), Kapitalwert mit der
  geforderten Eigenkapitalrendite.
- Bankensicht: Schuldendienstdeckungsgrad DSCR = CFADS / Kapitaldienst Fremdkapital.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from lcoh import constants as k
from lcoh.economics import Economics, compute_economics
from lcoh.npv import NpvResult
from lcoh.operation import OperationResult
from lcoh.yearly import efficiency_by_year

MODE_MARGIN = "Marge auf die Gestehungskosten"
MODE_TARGET = "Zielverkaufspreis"


@dataclass(frozen=True)
class FinanceResult:
    price_year1: float            # Verkaufspreis Wasserstoff im ersten Betriebsjahr [€/kg]
    lcoh: float                   # Gestehungskosten [€/kg]
    table: pd.DataFrame           # Jahrestabelle (Jahr 0 = Investition)
    npv_project: float            # Kapitalwert Projekt bei WACC [€]
    irr_project: float | None
    npv_equity: float             # Kapitalwert Eigenkapital bei geforderter EK-Rendite [€]
    irr_equity: float | None
    payback_static: float | None  # Jahre bis zur Rückzahlung der Investition (nicht abgezinst)
    payback_dynamic: float | None  # Jahre bis zur Rückzahlung (abgezinst mit WACC)
    dscr_min: float | None
    dscr_avg: float | None
    debt_service: float           # Kapitaldienst Fremdkapital [€/a]
    equity: float                 # Eigenkapitaleinsatz [€]
    debt: float                   # Fremdkapital [€]
    wacc: float
    profit_total: float           # Summe der Überschüsse nach Kapitaldienst über die Laufzeit (nominal) [€]
    revenue_h2_avg: float         # mittlerer Wasserstoffumsatz [€/a]
    capital_service: float = 0.0  # Kapitaldienst als Annuität zum WACC [€/a] (nur für die Darstellung je kg)
    sign_changes_equity: int = 0  # Vorzeichenwechsel im Eigenkapital-Cashflow


def _npv(rate: float, cf: np.ndarray) -> float:
    return float(np.sum(cf / (1.0 + rate) ** np.arange(len(cf))))


def irr(cf: np.ndarray) -> float | None:
    """Interner Zinsfuß: kleinster Zinssatz zwischen −50 % und 200 %, bei dem der Kapitalwert von positiv nach negativ
    wechselt (bei mehrfachem Vorzeichenwechsel der Zahlungen der wirtschaftlich übliche Wert). None, wenn es keinen gibt."""
    grid = np.arange(-0.5, 2.0001, 0.0025)
    vals = np.array([_npv(x, cf) for x in grid])
    idx = np.where((vals[:-1] > 0) & (vals[1:] <= 0))[0]
    if len(idx) == 0:
        return None
    lo, hi = grid[idx[0]], grid[idx[0] + 1]
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if _npv(mid, cf) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _payback(cf: np.ndarray) -> float | None:
    """Zeitpunkt (in Jahren, linear interpoliert), zu dem der kumulierte Cashflow erstmals nicht mehr negativ ist."""
    cum = np.cumsum(cf)
    for t in range(1, len(cum)):
        if cum[t] >= 0 > cum[t - 1]:
            return t - 1 + (-cum[t - 1]) / (cum[t] - cum[t - 1])
    return None


def yearly_values(r: OperationResult) -> list[Economics]:
    """Ergebnisse je Projektjahr (Preissteigerungen, Degradation, THG-Erlöse des jeweiligen Jahres)."""
    out = []
    for y, eff in zip(range(1, int(r.inputs.project_lifetime_years) + 1), efficiency_by_year(r)):
        h2_kwh = r.ely_consumption_kwh * eff
        ry = replace(r, avg_efficiency=eff, h2_energy_kwh=h2_kwh, h2_kg_per_year=h2_kwh / k.HHV_KWH_PER_KG_H2)
        out.append(compute_economics(ry, y))
    return out


def compute_finance(r: OperationResult, e_ann: Economics, n: NpvResult, mode: str, margin: float,
                    target_price: float, price_escalation: float) -> FinanceResult:
    inp = r.inputs
    life = int(inp.project_lifetime_years)
    lcoh = n.lcoh_eur_per_kg
    price1 = lcoh * (1.0 + margin) if mode == MODE_MARGIN else target_price
    eco = yearly_values(r)
    years = np.arange(0, life + 1)

    h2 = np.r_[0.0, [x.h2_kg_per_year for x in eco]]
    price = np.r_[0.0, [price1 * (1.0 + price_escalation) ** (t - 1) for t in range(1, life + 1)]]
    rev_h2 = h2 * price
    rev_at_lcoh = h2 * lcoh
    margin_eur = rev_h2 - rev_at_lcoh
    rev_thg = np.r_[0.0, [x.revenue_thg for x in eco]]
    rev_other = np.r_[0.0, [x.revenue_total - x.revenue_thg for x in eco]]
    power = np.r_[0.0, [x.power_cost for x in eco]]
    opex = np.r_[0.0, [x.opex_total for x in eco]]
    capex = n.capex_net

    # Stacktausch: im Projekt-Cashflow im Jahr des Tauschs; für die Kostenansicht als gleichbleibender Jahresbetrag
    sc = e_ann.stack
    stack_actual = np.zeros(life + 1)
    for j in range(1, sc.replacements + 1):
        t_j = int(round(j * sc.interval_years))
        if 1 <= t_j <= life:
            stack_actual[t_j] += sc.total_exchange_cost / sc.replacements
    stack_smooth = np.r_[0.0, [n.stack_service] * life]
    # Finanzierung des Stacktauschs (Eigenkapitalsicht): Rücklage in der ersten Laufzeithälfte, danach Kredit zum Stackzins
    half = life / 2.0
    first = [t for t in range(1, life + 1) if t <= half]
    second = [t for t in range(1, life + 1) if t > half]
    reserve = np.zeros(life + 1)
    stack_loan = np.zeros(life + 1)
    if sc.replacements > 0:
        for t in first:
            reserve[t] = sc.provision_total / len(first)
        for t in second:
            stack_loan[t] = sc.annuity

    op_cf = rev_h2 + rev_thg + rev_other - power - opex          # operativer Cashflow vor Stacktausch
    cf_project = op_cf - stack_actual
    cf_project[0] = -capex

    debt = capex * inp.debt_share
    equity = capex - debt
    i_d = inp.debt_interest_rate
    ds = debt / life if i_d <= 0 else debt * i_d / (1.0 - (1.0 + i_d) ** -life)
    debt_service = np.r_[0.0, [ds] * life]
    cfads = op_cf - reserve                                      # verfügbar für den Schuldendienst
    total_ds = debt_service + stack_loan
    cf_equity = cfads - total_ds
    cf_equity[0] = -equity

    wacc = n.rate
    disc = (1.0 + wacc) ** -years.astype(float)
    dscr = cfads[1:] / total_ds[1:] if ds > 0 else None

    table = pd.DataFrame({
        "Jahr": years, "Kalenderjahr": [inp.commissioning_year + t - 1 if t else inp.commissioning_year for t in years],
        "Wasserstoff [t]": h2 / 1000, "Verkaufspreis [€/kg]": price,
        "Erlös Wasserstoff [€]": rev_h2, "Erlös Wasserstoff zu Gestehungskosten [€]": rev_at_lcoh, "Marge [€]": margin_eur,
        "Erlös THG-Quote [€]": rev_thg, "Weitere Erlöse [€]": rev_other,
        "Strom [€]": -power, "Betrieb (OPEX) [€]": -opex, "Stacktausch [€]": -stack_actual,
        "Stacktausch als Jahresbetrag [€]": -stack_smooth,
        "Investition [€]": np.r_[-capex, np.zeros(life)],
        "Cashflow Projekt [€]": cf_project, "Cashflow Projekt abgezinst [€]": cf_project * disc,
        "Kumuliert abgezinst [€]": np.cumsum(cf_project * disc),
        "Rücklage Stacktausch [€]": -reserve, "CFADS [€]": np.r_[0.0, cfads[1:]],
        "Kapitaldienst Fremdkapital [€]": -debt_service, "Kapitaldienst Stackkredit [€]": -stack_loan,
        "Cashflow Eigenkapital [€]": cf_equity,
        "DSCR": np.r_[np.nan, dscr] if dscr is not None else np.nan})

    return FinanceResult(
        price_year1=price1, lcoh=lcoh, table=table,
        npv_project=_npv(wacc, cf_project), irr_project=irr(cf_project),
        npv_equity=_npv(inp.equity_interest_rate, cf_equity), irr_equity=irr(cf_equity),
        payback_static=_payback(cf_project), payback_dynamic=_payback(cf_project * disc),
        dscr_min=float(np.min(dscr)) if dscr is not None else None,
        dscr_avg=float(np.mean(dscr)) if dscr is not None else None,
        debt_service=ds, equity=equity, debt=debt, wacc=wacc,
        profit_total=float(cf_equity[1:].sum()), revenue_h2_avg=float(rev_h2[1:].mean()), capital_service=n.capital_service,
        sign_changes_equity=int(np.sum(np.diff(np.sign(cf_equity[np.abs(cf_equity) > 1e-6])) != 0)))
