"""Aufbau der Oberfläche: welche Eingabe steht wo, und wann ist sie sichtbar."""
from __future__ import annotations

# --- Cockpit: die wichtigsten Angaben zum Elektrolysesystem
COCKPIT = [
    ("Elektrolyseur & Projekt", None, [
        "commissioning_year", "project_lifetime_years", "electrolyzer_power_kw",
        "capex_electrolyzer_eur_per_kw", "electrolyzer_efficiency", "min_part_load"]),
    ("Batterie", None, ["battery_enabled", "battery_capacity_hours", "battery_input_power_kw"]),
    ("Strombezug", None, [
        "ppa_baseload_enabled", "ppa_baseload_kw", "ppa_baseload_price_eur_per_mwh",
        "ppa_pap_enabled", "ppa_pv_kw", "ppa_pv_price_eur_per_mwh", "ppa_wind_kw", "ppa_wind_price_eur_per_mwh",
        "section7_enabled", "section13k_enabled", "spot_enabled"]),
]

# --- Eingabe-Seiten: (Seitenname, [(Abschnitt, Schalter-Eingabe oder None, [Eingaben])])
PAGES = [
    ("Anlage & Investitionen", [
        ("Investitionskosten (CAPEX)", None, [
            "capex_epc_eur_per_kw", "capex_bop_eur_per_kw", "capex_building_eur_per_kw", "capex_civil_eur_per_kw"]),
        ("Abwärme", None, ["waste_heat_enabled", "capex_waste_heat_eur_per_kw"]),
        ("Sauerstoff", None, [
            "oxygen_enabled", "capex_oxygen_eur_per_kw", "o2_compressor_pressure_bar", "o2_inlet_temperature_c",
            "o2_inlet_pressure_bar", "o2_compressor_efficiency"]),
        ("Wasserstoff-Aufbereitung", None, [
            "h2_processing_mode", "capex_h2_compression_eur_per_kw", "capex_h2_direct_eur_per_kw", "h2_processed_share",
            "h2_compressor_pressure_bar", "h2_inlet_temperature_c", "h2_inlet_pressure_bar", "h2_compressor_efficiency"]),
        ("Peripherie", None, ["peripherals_share_of_ely"]),
        ("Batteriesystem (Kosten)", "battery_enabled", ["battery_capex_eur_per_kwh", "battery_other_costs_eur"]),
        ("Stacktausch", None, [
            "stack_lifetime_h", "stack_degradation_per_year", "stack_replacement_cost_share",
            "stack_cost_degression", "stack_interest_rate"]),
        ("Individuelle CAPEX", None, ["capex_custom_1_eur_per_kw"]),
    ]),
    ("Strombezug & Nebenkosten", [
        ("Preisentwicklung PPA", None, ["ppa_baseload_price_escalation", "ppa_pap_price_escalation"]),
        ("Spotmarkt und Börsenpreise", None, [
            "spot_max_price_eur_per_mwh", "spot_price_escalation", "day_ahead_scenario_year",
            "spot_price_source", "spot_own_price_eur_per_mwh"]),
        ("Strombezug nach §7 der 37. BImSchV", "section7_enabled", [
            "section7_negative_prices", "co2_price_source", "co2_own_price_eur_per_t", "co2_price_escalation"]),
        ("Strombezug nach §13k EnWG", "section13k_enabled", [
            "section13k_price_eur_per_mwh", "section13k_price_escalation"]),
    ]),
    ("Betrieb (OPEX)", [
        ("Pauschale oder Einzelpositionen", None, [
            "opex_lump_sum_enabled", "opex_lump_sum_share_of_capex", "opex_lump_sum_escalation"]),
        ("Wartung & Instandhaltung", "_detail_opex", ["maintenance_share_of_capex", "maintenance_escalation"]),
        ("Personal", "_detail_opex", ["personnel_eur_per_year", "personnel_escalation"]),
        ("Rückstellungen (ohne Stacktausch)", "_detail_opex", [
            "replacement_reserve_share_of_capex", "decommissioning_share_of_capex", "reserves_escalation"]),
        ("Wasser", "_detail_opex", [
            "water_fresh_eur_per_m3", "water_treatment_eur_per_m3", "water_waste_eur_per_m3", "water_escalation"]),
        ("Sonstige OPEX", "_detail_opex", ["other_opex_share_of_capex", "other_opex_escalation"]),
    ]),
    ("Finanzierung & Förderungen", [
        ("Finanzierung", None, ["debt_share", "debt_interest_rate", "equity_interest_rate", "corporate_tax_rate"]),
        ("CAPEX-Förderung", None, ["capex_subsidy_mode", "capex_subsidy_percent", "capex_subsidy_eur_per_kw"]),
        ("OPEX-Förderung", None, [
            "opex_subsidy_mode", "opex_subsidy_eur_per_kg", "opex_subsidy_eur_per_full_load_hour"]),
        ("Strompreisförderung", None, [
            "power_subsidy_mode", "power_subsidy_eur_per_kg", "power_subsidy_eur_per_mwh"]),
        ("Strompreiskompensation", None, [
            "spk_mode", "spk_eua_price_eur_per_t", "spk_consumption_factor", "spk_escalation",
            "spk_separate_revenue_eur"]),
    ]),
]

REVENUE_PAGE = [
    ("THG-Quote", None, [
        "thg_enabled", "thg_price_eur_per_t", "thg_mobility_share", "thg_producer_share",
        "thg_h2_intensity_kgco2_per_gj", "thg_adjustment_factor", "thg_price_escalation"]),
    ("Verkauf von Überschussstrom", None, [
        "power_sale_enabled", "power_sale_mode", "power_sale_ppa_price_eur_per_mwh", "power_sale_ppa_escalation"]),
    ("Sauerstoff", None, ["oxygen_price_eur_per_t", "oxygen_price_escalation"]),
    ("Abwärme", None, ["heat_price_eur_per_mwh", "heat_usable_share", "heat_price_escalation"]),
    ("Regelenergie", None, ["balancing_enabled", "balancing_revenue_eur_per_year", "balancing_escalation"]),
    ("Sonstige Einnahmen", None, [
        "other_revenue_enabled", "other_revenue_1_eur_per_year", "other_revenue_1_escalation",
        "other_revenue_2_eur_per_year", "other_revenue_2_escalation"]),
]

# --- Sichtbarkeit: Eingabe wird nur gezeigt, wenn die Bedingung erfüllt ist
VISIBLE = {
    "battery_capacity_hours": lambda v: v["battery_enabled"],
    "battery_input_power_kw": lambda v: v["battery_enabled"],
    "ppa_baseload_kw": lambda v: v["ppa_baseload_enabled"],
    "ppa_baseload_price_eur_per_mwh": lambda v: v["ppa_baseload_enabled"],
    "ppa_baseload_price_escalation": lambda v: v["ppa_baseload_enabled"],
    "ppa_pv_kw": lambda v: v["ppa_pap_enabled"], "ppa_pv_price_eur_per_mwh": lambda v: v["ppa_pap_enabled"],
    "ppa_wind_kw": lambda v: v["ppa_pap_enabled"], "ppa_wind_price_eur_per_mwh": lambda v: v["ppa_pap_enabled"],
    "ppa_pap_price_escalation": lambda v: v["ppa_pap_enabled"],
    "spot_price_source": lambda v: v["spot_enabled"],
    "spot_own_price_eur_per_mwh": lambda v: v["spot_enabled"] and v["spot_price_source"] == "Eigene Preise",
    "co2_own_price_eur_per_t": lambda v: v["co2_price_source"] == "Eigener Preis",
    "capex_waste_heat_eur_per_kw": lambda v: v["waste_heat_enabled"],
    "capex_oxygen_eur_per_kw": lambda v: v["oxygen_enabled"],
    "o2_compressor_pressure_bar": lambda v: v["oxygen_enabled"], "o2_inlet_temperature_c": lambda v: v["oxygen_enabled"],
    "o2_inlet_pressure_bar": lambda v: v["oxygen_enabled"], "o2_compressor_efficiency": lambda v: v["oxygen_enabled"],
    "capex_h2_compression_eur_per_kw": lambda v: v["h2_processing_mode"] == "Verdichtung",
    "capex_h2_direct_eur_per_kw": lambda v: v["h2_processing_mode"] != "Verdichtung",
    "h2_processed_share": lambda v: v["h2_processing_mode"] == "Verdichtung",
    "h2_compressor_pressure_bar": lambda v: v["h2_processing_mode"] == "Verdichtung",
    "h2_inlet_temperature_c": lambda v: v["h2_processing_mode"] == "Verdichtung",
    "h2_inlet_pressure_bar": lambda v: v["h2_processing_mode"] == "Verdichtung",
    "h2_compressor_efficiency": lambda v: v["h2_processing_mode"] == "Verdichtung",
    "opex_lump_sum_share_of_capex": lambda v: v["opex_lump_sum_enabled"],
    "opex_lump_sum_escalation": lambda v: v["opex_lump_sum_enabled"],
    "capex_subsidy_percent": lambda v: v["capex_subsidy_mode"] == "Prozentual",
    "capex_subsidy_eur_per_kw": lambda v: v["capex_subsidy_mode"] == "Absolut",
    "opex_subsidy_eur_per_kg": lambda v: v["opex_subsidy_mode"] == "Pro kg",
    "opex_subsidy_eur_per_full_load_hour": lambda v: v["opex_subsidy_mode"] == "Pro Volllaststunde",
    "power_subsidy_eur_per_kg": lambda v: v["power_subsidy_mode"] == "Pro kg",
    "power_subsidy_eur_per_mwh": lambda v: v["power_subsidy_mode"] == "Pro MWh Strom",
    "spk_eua_price_eur_per_t": lambda v: v["spk_mode"] == "Rechner",
    "spk_consumption_factor": lambda v: v["spk_mode"] == "Rechner",
    "spk_escalation": lambda v: v["spk_mode"] != "Ohne",
    "spk_separate_revenue_eur": lambda v: v["spk_mode"] == "Separat",
    "thg_price_eur_per_t": lambda v: v["thg_enabled"], "thg_mobility_share": lambda v: v["thg_enabled"],
    "thg_producer_share": lambda v: v["thg_enabled"], "thg_h2_intensity_kgco2_per_gj": lambda v: v["thg_enabled"],
    "thg_adjustment_factor": lambda v: v["thg_enabled"], "thg_price_escalation": lambda v: v["thg_enabled"],
    "power_sale_mode": lambda v: v["power_sale_enabled"],
    "power_sale_ppa_price_eur_per_mwh": lambda v: v["power_sale_enabled"] and v["power_sale_mode"] == "PPA",
    "power_sale_ppa_escalation": lambda v: v["power_sale_enabled"],
    "oxygen_price_eur_per_t": lambda v: v["oxygen_enabled"], "oxygen_price_escalation": lambda v: v["oxygen_enabled"],
    "heat_price_eur_per_mwh": lambda v: v["waste_heat_enabled"], "heat_usable_share": lambda v: v["waste_heat_enabled"],
    "heat_price_escalation": lambda v: v["waste_heat_enabled"],
    "balancing_revenue_eur_per_year": lambda v: v["balancing_enabled"],
    "balancing_escalation": lambda v: v["balancing_enabled"],
    "other_revenue_1_eur_per_year": lambda v: v["other_revenue_enabled"],
    "other_revenue_1_escalation": lambda v: v["other_revenue_enabled"],
    "other_revenue_2_eur_per_year": lambda v: v["other_revenue_enabled"],
    "other_revenue_2_escalation": lambda v: v["other_revenue_enabled"],
}

# Abschnitte, deren Schalter kein einzelner Eingabewert ist
GATES = {"_detail_opex": lambda v: not v["opex_lump_sum_enabled"]}

LEVIES = [("grid_fee", "Netzentgelt"), ("electricity_tax", "Stromsteuer"), ("concession_fee", "Konzessionsabgabe"),
          ("kwk_levy", "KWK-Aufschlag"), ("stromnev19_levy", "StromNEV-§19-Umlage"),
          ("offshore_levy", "Offshore-Netzumlage")]

CHOICE_LABELS = {
    "thg_adjustment_factor": {0.4: "0,4 – Brennstoffzellen-Elektroantrieb", 1.0: "1,0 – Verbrennungsmotor"},
    "h2_processing_mode": {"direkt": "Direkt (ohne Verdichtung)", "Verdichtung": "Verdichtung"},
}

# Angepasste Feldbeschriftungen (ersetzen die Beschriftung aus der Eingabeliste)
LABEL_OVERRIDES = {
    "min_part_load": "Minimale Teillast",
    "capex_custom_1_eur_per_kw": "Individuelle CAPEX",
    "thg_adjustment_factor": "Anpassungsfaktor",
    "day_ahead_scenario_year": "Börsenpreis-Szenario (Jahr)",
}
# Prozentfelder mit feinerer Schrittweite (0,01 statt 0,1)
FINE_STEP = {"stack_degradation_per_year"}
