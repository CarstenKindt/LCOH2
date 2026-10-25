"""AUTOMATISCH ERZEUGT von tools/build_input_spec.py - nicht von Hand ändern.

Die Klasse Inputs enthält alle Eingaben des Tools. Ohne Angaben gelten die Standardwerte der Excel.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, fields

from lcoh.input_spec import SPEC_BY_KEY, SPECS


@dataclass
class Inputs:
    # ---- System
    commissioning_year: int = 2026  # Blatt 2, C5
    electrolyzer_power_kw: float = 25000.0  # Blatt 2, C6 [kW]
    capex_electrolyzer_eur_per_kw: float = 1000.0  # Blatt 2, C7 [€ / kW]
    project_lifetime_years: int = 20  # Blatt 2, C8 [a]
    electrolyzer_efficiency: float = 0.7  # Blatt 2, C9 [%]
    min_part_load: float = 0.2  # Blatt 2, C10 [%]
    sensitivity_step: float = 0.3  # Blatt 2, C12 [%]
    # ---- CAPEX
    capex_epc_eur_per_kw: float = 120.0  # Blatt 2, C23 [€ / kW]
    capex_bop_eur_per_kw: float = 750.0  # Blatt 2, C26 [€ / kW]
    capex_building_eur_per_kw: float = 1000.0  # Blatt 2, C29 [€ / kW]
    capex_civil_eur_per_kw: float = 300.0  # Blatt 2, C30 [€ / kW]
    waste_heat_enabled: bool = True  # Blatt 2, C33
    capex_waste_heat_eur_per_kw: float = 10.0  # Blatt 2, C34 [€ / kW]
    oxygen_enabled: bool = True  # Blatt 2, C37
    capex_oxygen_eur_per_kw: float = 30.0  # Blatt 2, C38 [€ / kW]
    h2_processing_mode: str = 'Verdichtung'  # Blatt 2, C41
    capex_h2_compression_eur_per_kw: float = 30.0  # Blatt 2, C42 [€ / kW]
    capex_h2_direct_eur_per_kw: float = 10.0  # Blatt 2, C43 [€ / kW]
    capex_custom_1_eur_per_kw: float = 0.0  # Blatt 2, C54 [€ / kW]
    capex_custom_2_share_of_electrolyzer: float = 0.0  # Blatt 2, C55 [%]
    capex_custom_3_eur: float = 0.0  # Blatt 2, C56 [€]
    # ---- Batteriesystem
    battery_enabled: bool = True  # Blatt 2, C46
    battery_capacity_hours: float = 5.0  # Blatt 2, C47 [h]
    battery_input_power_kw: float = 50000.0  # Blatt 2, C48 [kW]
    battery_capex_eur_per_kwh: float = 220.0  # Blatt 2, C49 [€ / kWh]
    battery_other_costs_eur: float = 0.0  # Blatt 2, C50 [€]
    # ---- Strombezug: PPA
    ppa_baseload_enabled: bool = True  # Blatt 2, C62
    ppa_baseload_kw: float = 5000.0  # Blatt 2, C63 [kWh / h]
    ppa_baseload_price_eur_per_mwh: float = 85.0  # Blatt 2, C64 [€ / MWh]
    ppa_baseload_price_escalation: float = 0.03  # Blatt 2, C65 [%]
    ppa_pap_enabled: bool = True  # Blatt 2, C66
    ppa_pv_enabled: bool = True  # Blatt 2, C66 (in der Excel gemeinsam mit Wind)
    ppa_wind_enabled: bool = True  # Blatt 2, C66
    ppa_pv_kw: float = 10000.0  # Blatt 2, C67 [kWh / h]
    ppa_pv_price_eur_per_mwh: float = 40.0  # Blatt 2, C68 [€ / MWh]
    ppa_wind_kw: float = 30000.0  # Blatt 2, C69 [kWh / h]
    ppa_wind_price_eur_per_mwh: float = 75.0  # Blatt 2, C70 [€ / MWh]
    ppa_pap_price_escalation: float = 0.0  # Blatt 2, C71 [%]
    # ---- Strombezug: Spotmarkt
    spot_max_price_eur_per_mwh: float = 70.0  # Blatt 2, C76 [€ / MWh]
    spot_price_escalation: float = 0.0  # Blatt 2, C77 [%]
    spot_enabled: bool = False  # Blatt 2, C79
    spot_price_source: str = 'Marktpreise'  # Blatt 2, C80
    spot_own_price_eur_per_mwh: float = 0.0  # Blatt 2, C81 [€ / MWh]
    # ---- Strombezug: §7 37. BImSchV
    section7_enabled: bool = True  # Blatt 2, C83
    section7_negative_prices: bool = True  # Blatt 2, C84
    co2_price_source: str = 'Jahresdaten'  # Blatt 2, C86
    co2_own_price_eur_per_t: float = 0.0  # Blatt 2, C88 [€ / t_CO2]
    co2_price_escalation: float = 0.0  # Blatt 2, C89 [%]
    # ---- Strombezug: §13k EnWG
    section13k_enabled: bool = False  # Blatt 2, C91
    section13k_price_eur_per_mwh: float = 30.0  # Blatt 2, C93 [€ / MWh]
    section13k_price_escalation: float = 0.0  # Blatt 2, C94 [%]
    # ---- Stromnebenkosten
    demand_charge_ely_eur_per_kw_month: float = 2.0  # Blatt 2, C100 [€ / kW * Monat]
    demand_charge_rest_eur_per_kw_month: float = 2.0  # Blatt 2, C101 [€ / kW * Monat]
    # ---- Aufbereitung & Peripherie
    peripherals_share_of_ely: float = 0.2  # Blatt 2, C105 [%]
    h2_processed_share: float = 1.0  # Blatt 2, C108 [%]
    h2_compressor_pressure_bar: float = 300.0  # Blatt 2, C109 [bar]
    h2_inlet_temperature_c: float = 20.0  # Blatt 2, C110 [°C]
    h2_inlet_pressure_bar: float = 10.0  # Blatt 2, C111 [bar]
    h2_compressor_efficiency: float = 0.75  # Blatt 2, C112 [%]
    o2_compressor_pressure_bar: float = 300.0  # Blatt 2, C114 [bar]
    o2_inlet_temperature_c: float = 20.0  # Blatt 2, C115 [°C]
    o2_inlet_pressure_bar: float = 10.0  # Blatt 2, C116 [bar]
    o2_compressor_efficiency: float = 0.7  # Blatt 2, C117 [%]
    # ---- Stacktausch
    stack_lifetime_h: float = 80000.0  # Blatt 2, C124 [h]
    stack_degradation_per_year: float = 0.008  # Blatt 2, C125 [%]
    stack_replacement_cost_share: float = 0.5  # Blatt 2, C126 [%]
    stack_cost_degression: float = -0.05  # Blatt 2, C127 [%]
    stack_interest_rate: float = 0.05  # Blatt 2, C128 [%]
    # ---- OPEX
    opex_lump_sum_enabled: bool = False  # Blatt 2, C133
    opex_lump_sum_share_of_capex: float = 0.03  # Blatt 2, G133 [%]
    opex_lump_sum_escalation: float = 0.0  # Blatt 2, G134 [%]
    maintenance_share_of_capex: float = 0.005  # Blatt 2, C136 [%]
    maintenance_escalation: float = 0.0  # Blatt 2, C137 [%]
    personnel_eur_per_year: float = 85000.0  # Blatt 2, C140 [€ / a]
    personnel_escalation: float = 0.0  # Blatt 2, C141 [%]
    replacement_reserve_share_of_capex: float = 0.01  # Blatt 2, C144 [%]
    decommissioning_share_of_capex: float = 0.0025  # Blatt 2, C145 [%]
    reserves_escalation: float = 0.0  # Blatt 2, C146 [%]
    water_fresh_eur_per_m3: float = 4.0  # Blatt 2, C149 [€ / m³]
    water_treatment_eur_per_m3: float = 5.0  # Blatt 2, C150 [€ / m³]
    water_waste_eur_per_m3: float = 6.5  # Blatt 2, C151 [€ / m³]
    water_escalation: float = 0.0  # Blatt 2, C152 [%]
    other_opex_share_of_capex: float = 0.005  # Blatt 2, C155 [%]
    other_opex_escalation: float = 0.0  # Blatt 2, C156 [%]
    # ---- Finanzierung
    debt_share: float = 0.8  # Blatt 2, C161 [%]
    debt_interest_rate: float = 0.065  # Blatt 2, C162 [%]
    equity_interest_rate: float = 0.1  # Blatt 2, C163 [%]
    corporate_tax_rate: float = 0.3  # Blatt 2, C164 [%]
    # ---- Förderungen
    capex_subsidy_mode: str = 'Ohne'  # Blatt 2, C169
    capex_subsidy_percent: float = 0.1  # Blatt 2, C170 [%]
    capex_subsidy_eur_per_kw: float = 500.0  # Blatt 2, C171 [€ / kW]
    opex_subsidy_mode: str = 'Ohne'  # Blatt 2, C174
    opex_subsidy_eur_per_kg: float = 0.25  # Blatt 2, C175 [€ / kg]
    opex_subsidy_eur_per_full_load_hour: float = 0.0  # Blatt 2, C176 [€ / h]
    power_subsidy_mode: str = 'Ohne'  # Blatt 2, C179
    power_subsidy_eur_per_kg: float = 0.0  # Blatt 2, C180 [€ / kg_H2]
    power_subsidy_eur_per_mwh: float = 10.0  # Blatt 2, C181 [€ / MWh]
    # ---- Strompreiskompensation
    spk_mode: str = 'Ohne'  # Blatt 2, C189
    spk_eua_price_eur_per_t: float = 89.0  # Blatt 2, C190 [€ / t_CO2]
    spk_consumption_factor: float = 0.8  # Blatt 2, C191 [%]
    spk_escalation: float = 0.0  # Blatt 2, C192 [%]
    spk_separate_revenue_eur: float = 0.0  # Blatt 2, C193 [€ / a]
    # ---- THG-Quote
    thg_enabled: bool = True  # Blatt 2, C198
    thg_price_eur_per_t: float = 300.0  # Blatt 2, C199 [€ / t_CO2]
    thg_mobility_share: float = 0.75  # Blatt 2, C200 [%]
    thg_producer_share: float = 0.95  # Blatt 2, C201 [%]
    thg_h2_intensity_kgco2_per_gj: float = 10.0  # Blatt 2, C202 [kg_CO2/GJ]
    thg_adjustment_factor: float = 0.4  # Blatt 2, C203
    thg_price_escalation: float = 0.015  # Blatt 2, C204 [%]
    # ---- Weitere Einnahmen
    power_sale_enabled: bool = True  # Blatt 2, C207
    power_sale_mode: str = 'Spotmarkt'  # Blatt 2, C208
    power_sale_ppa_price_eur_per_mwh: float = 0.0  # Blatt 2, C209 [€ / MWh]
    power_sale_ppa_escalation: float = 0.0  # Blatt 2, C210 [%]
    oxygen_price_eur_per_t: float = 50.0  # Blatt 2, C213 [€ / t]
    oxygen_price_escalation: float = 0.0  # Blatt 2, C214 [%]
    heat_price_eur_per_mwh: float = 40.0  # Blatt 2, C217 [€ / MWh]
    heat_usable_share: float = 0.75  # Blatt 2, C218 [%]
    heat_price_escalation: float = 0.0  # Blatt 2, C219 [%]
    balancing_enabled: bool = True  # Blatt 2, C222
    balancing_revenue_eur_per_year: float = 100000.0  # Blatt 2, C223 [€ / a]
    balancing_escalation: float = 0.0  # Blatt 2, C224 [%]
    other_revenue_enabled: bool = False  # Blatt 2, C227
    other_revenue_1_eur_per_year: float = 50000.0  # Blatt 2, C228 [€ / a]
    other_revenue_1_escalation: float = 0.0  # Blatt 2, C229 [%]
    other_revenue_2_eur_per_year: float = 10000.0  # Blatt 2, C230 [€ / a]
    other_revenue_2_escalation: float = 0.0  # Blatt 2, C231 [%]
    # ---- Stromnebenkosten
    levy_ely_grid_fee_ct_per_kwh: float = 11.0  # Blatt 5, H6 [ct/kWh]
    levy_ely_grid_fee_exempt: bool = True  # Blatt 5, J6
    levy_rest_grid_fee_ct_per_kwh: float = 11.0  # Blatt 5, M6 [ct/kWh]
    levy_rest_grid_fee_exempt: bool = True  # Blatt 5, O6
    levy_ely_electricity_tax_ct_per_kwh: float = 0.5  # Blatt 5, H8 [ct/kWh]
    levy_ely_electricity_tax_exempt: bool = True  # Blatt 5, J8
    levy_rest_electricity_tax_ct_per_kwh: float = 0.5  # Blatt 5, M8 [ct/kWh]
    levy_rest_electricity_tax_exempt: bool = True  # Blatt 5, O8
    levy_ely_concession_fee_ct_per_kwh: float = 1.66  # Blatt 5, H10 [ct/kWh]
    levy_ely_concession_fee_exempt: bool = True  # Blatt 5, J10
    levy_rest_concession_fee_ct_per_kwh: float = 1.66  # Blatt 5, M10 [ct/kWh]
    levy_rest_concession_fee_exempt: bool = True  # Blatt 5, O10
    levy_ely_kwk_levy_ct_per_kwh: float = 0.275  # Blatt 5, H12 [ct/kWh]
    levy_ely_kwk_levy_exempt: bool = True  # Blatt 5, J12
    levy_rest_kwk_levy_ct_per_kwh: float = 0.275  # Blatt 5, M12 [ct/kWh]
    levy_rest_kwk_levy_exempt: bool = True  # Blatt 5, O12
    levy_ely_stromnev19_levy_ct_per_kwh: float = 1.56  # Blatt 5, H14 [ct/kWh]
    levy_ely_stromnev19_levy_exempt: bool = True  # Blatt 5, J14
    levy_rest_stromnev19_levy_ct_per_kwh: float = 1.56  # Blatt 5, M14 [ct/kWh]
    levy_rest_stromnev19_levy_exempt: bool = True  # Blatt 5, O14
    levy_ely_offshore_levy_ct_per_kwh: float = 0.82  # Blatt 5, H16 [ct/kWh]
    levy_ely_offshore_levy_exempt: bool = True  # Blatt 5, J16
    levy_rest_offshore_levy_ct_per_kwh: float = 0.82  # Blatt 5, M16 [ct/kWh]
    levy_rest_offshore_levy_exempt: bool = True  # Blatt 5, O16
    demand_charge_ely_exempt: bool = True  # Blatt 5, J17
    demand_charge_rest_exempt: bool = True  # Blatt 5, O17
    # ---- Strombezug: Spotmarkt
    day_ahead_scenario_year: int = 2024  # Blatt 8, G6

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Inputs":
        """Fehlende Schlüssel erhalten den Excel-Standardwert, unbekannte werden ignoriert."""
        values = {}
        for f in fields(cls):
            if f.name in data:
                values[f.name] = _coerce(SPEC_BY_KEY[f.name], data[f.name])
        return cls(**values)

    def validate(self) -> list[str]:
        """Gibt eine Liste verständlicher Fehlermeldungen zurück (leer = alles in Ordnung)."""
        problems = []
        for s in SPECS:
            value = getattr(self, s.key)
            if s.choices is not None and value not in s.choices:
                problems.append(f"{s.label}: Wert {value!r} ist nicht erlaubt (erlaubt: {', '.join(map(str, s.choices))}).")
            elif s.kind in ("number", "percent"):
                if s.minimum is not None and value < s.minimum:
                    problems.append(f"{s.label}: Wert {value} ist kleiner als {s.minimum}.")
                if s.maximum is not None and value > s.maximum:
                    problems.append(f"{s.label}: Wert {value} ist größer als {s.maximum}.")
        return problems


def _coerce(spec, value):
    if spec.kind == "bool":
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "ja", "wahr")
        return bool(value)
    if spec.kind == "choice":
        return type(spec.default)(value)
    if isinstance(spec.default, int) and not isinstance(spec.default, bool):
        return int(value)
    return float(value)
