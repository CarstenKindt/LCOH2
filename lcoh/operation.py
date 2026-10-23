"""Betriebsrechnung: Wirkungsgrad, Stack-Tauschintervall, Wasserstoffmenge und Kennzahlen.

Die Excel löst den Kreisbezug (Wirkungsgrad <-> Stack-Intervall <-> Auslastung) von Hand über die
gelbe Hilfszelle F129. Das Tool iteriert automatisch, bis das Intervall sich nicht mehr ändert.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from lcoh import constants as k
from lcoh.dispatch import simulate_dispatch
from lcoh.inputs import Inputs
from lcoh.prices import MarketSeries, build_market_series
from lcoh.system import SystemPower, system_power


def stack_replacements(inp: Inputs, full_load_hours: float) -> int:
    """Anzahl Stacktausche in der Projektlaufzeit (Blatt 6, C4)."""
    total_hours = inp.project_lifetime_years * full_load_hours
    if total_hours > inp.stack_lifetime_h:
        return math.floor(total_hours / inp.stack_lifetime_h)
    return 0


def stack_interval_years(inp: Inputs, replacements: int) -> float:
    """Jahre zwischen zwei Stacktauschen (Blatt 6, C5)."""
    return 0.0 if replacements == 0 else inp.project_lifetime_years / (replacements + 1)


def average_efficiency(inp: Inputs, interval_years: float) -> float:
    """Mittlerer Wirkungsgrad über die Laufzeit (Blatt 3, C24 bis C29).

    Hinweis: Ohne Stacktausch zieht die Excel die Degradation der vollen Laufzeit ab
    (nicht die halbe, wie bei einem Tausch). Das Tool übernimmt das.
    """
    eff0 = inp.electrolyzer_efficiency
    deg = inp.stack_degradation_per_year
    if interval_years == 0:
        return eff0 - deg * inp.project_lifetime_years
    end = max(eff0 - deg * interval_years, 0.0)
    return (eff0 + end) / 2.0


@dataclass(frozen=True)
class OperationResult:
    inputs: Inputs
    power: SystemPower
    hourly: pd.DataFrame
    market: MarketSeries
    avg_efficiency: float
    stack_interval_years: float
    stack_replacements: int
    ely_consumption_kwh: float        # Blatt 4, Y4
    full_load_hours: float            # Blatt 2, F13
    h2_energy_kwh: float              # Blatt 2, F7
    h2_kg_per_year: float             # Blatt 2, F8
    section7_hours: int
    section13k_hours: int
    battery_cycles: int
    iterations: int


def run_operation(inp: Inputs, ts: pd.DataFrame, max_iter: int = 20) -> OperationResult:
    market = build_market_series(inp, ts)
    interval = 0.0
    seen: list[float] = []
    for i in range(1, max_iter + 1):
        eff = average_efficiency(inp, interval)
        power = system_power(inp, eff)
        hourly = simulate_dispatch(inp, ts, market, power)
        ely_kwh = float(hourly["consumption_kwh"].sum() * power.ely_kw / power.total_kw)
        flh = ely_kwh / power.ely_kw
        new_interval = stack_interval_years(inp, stack_replacements(inp, flh))
        if new_interval == interval:
            break
        if new_interval in seen:  # Zyklus: den größeren (vorsichtigeren) Wert nehmen und beenden
            interval = max(interval, new_interval)
            eff = average_efficiency(inp, interval)
            power = system_power(inp, eff)
            hourly = simulate_dispatch(inp, ts, market, power)
            ely_kwh = float(hourly["consumption_kwh"].sum() * power.ely_kw / power.total_kw)
            flh = ely_kwh / power.ely_kw
            break
        seen.append(interval)
        interval = new_interval

    h2_energy = ely_kwh * eff
    cycles = 0
    if inp.battery_enabled and power.battery_capacity_kwh > 0:
        soc_end = hourly["battery_soc_kwh"].iloc[-1]
        cycles = math.ceil((hourly["battery_charge_kwh"].sum() - soc_end) / power.battery_capacity_kwh - 1e-12)
    return OperationResult(
        inputs=inp, power=power, hourly=hourly, market=market, avg_efficiency=eff,
        stack_interval_years=interval, stack_replacements=stack_replacements(inp, flh),
        ely_consumption_kwh=ely_kwh, full_load_hours=flh, h2_energy_kwh=h2_energy,
        h2_kg_per_year=h2_energy / k.HHV_KWH_PER_KG_H2,
        section7_hours=int((hourly["s7_kwh"] > 0).sum()),
        section13k_hours=int((hourly["s13k_kwh"] > 0).sum()),
        battery_cycles=cycles, iterations=i)
