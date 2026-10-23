"""Anlagenleistung: Elektrolyseur, Peripherie und Verdichter (Excel: Blatt 3 G11-G46 und Blatt 4 C3-G5)."""
from __future__ import annotations

import math
from dataclasses import dataclass

from lcoh import constants as k
from lcoh.inputs import Inputs


def isentropic_work_j_per_kg(alpha: float, gas_constant: float, temperature_k: float,
                             pressure_out_bar: float, pressure_in_bar: float) -> float:
    """Spezifische isentrope Verdichterarbeit in J/kg (Blatt 3, G14 und G34)."""
    return (alpha / (alpha - 1.0)) * gas_constant * temperature_k * (
        (pressure_out_bar / pressure_in_bar) ** ((alpha - 1.0) / alpha) - 1.0)


def h2_compressor_work_kwh_per_kg(inp: Inputs) -> float:
    """Reale Verdichterarbeit je kg Wasserstoff in kWh/kg (Blatt 3, G22)."""
    work = isentropic_work_j_per_kg(k.H2_ISENTROPIC_EXPONENT, k.H2_GAS_CONSTANT,
                                    inp.h2_inlet_temperature_c + 273.15,
                                    inp.h2_compressor_pressure_bar, inp.h2_inlet_pressure_bar)
    return work / k.J_PER_KWH / inp.h2_compressor_efficiency


def o2_compressor_work_kwh_per_kg(inp: Inputs) -> float:
    """Reale Verdichterarbeit je kg Sauerstoff in kWh/kg (Blatt 3, G42)."""
    work = isentropic_work_j_per_kg(k.O2_ISENTROPIC_EXPONENT, k.O2_GAS_CONSTANT,
                                    inp.o2_inlet_temperature_c + 273.15,
                                    inp.o2_compressor_pressure_bar, inp.o2_inlet_pressure_bar)
    return work / k.J_PER_KWH / inp.o2_compressor_efficiency


@dataclass(frozen=True)
class SystemPower:
    """Installierte Leistungen in kW und ihre Anteile an der Gesamtleistung."""
    ely_kw: float
    peripherals_kw: float
    h2_compressor_kw: float
    o2_compressor_kw: float
    total_kw: float
    battery_capacity_kwh: float
    battery_power_kw: float

    @property
    def ely_share(self) -> float:
        return self.ely_kw / self.total_kw

    @property
    def peripherals_share(self) -> float:
        return self.peripherals_kw / self.total_kw

    @property
    def h2_compressor_share(self) -> float:
        return self.h2_compressor_kw / self.total_kw

    @property
    def o2_compressor_share(self) -> float:
        return self.o2_compressor_kw / self.total_kw


def system_power(inp: Inputs, avg_efficiency: float) -> SystemPower:
    """Gesamtleistung des Elektrolysesystems (Blatt 4, C5) bei gegebenem mittleren Wirkungsgrad."""
    ely = inp.electrolyzer_power_kw
    peripherals = ely * inp.peripherals_share_of_ely
    # Wasserstoff und Sauerstoff je Stunde bei 100 % Elektrolyseur-Auslastung (Blatt 3, G25 und G26)
    h2_kg_per_h = ely * avg_efficiency / k.HHV_KWH_PER_KG_H2
    o2_kg_per_h = h2_kg_per_h * k.O2_KG_PER_KG_H2
    h2_comp = (h2_compressor_work_kwh_per_kg(inp) * h2_kg_per_h * inp.h2_processed_share
               if inp.h2_processing_mode == "Verdichtung" else 0.0)
    o2_comp = o2_compressor_work_kwh_per_kg(inp) * o2_kg_per_h if inp.oxygen_enabled else 0.0
    total = ely + peripherals + h2_comp + o2_comp

    if inp.battery_enabled:
        capacity = math.ceil(total) * inp.battery_capacity_hours  # Excel: ROUNDUP(C5, 0) * Faktor
        power = inp.battery_input_power_kw
    else:
        capacity = power = 0.0
    return SystemPower(ely, peripherals, h2_comp, o2_comp, total, capacity, power)
