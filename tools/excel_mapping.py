"""Zuordnung: gelbe Eingabefelder der Excel -> Schlüssel im Python-Tool.

Format je Eintrag: Zelle: (Schlüssel, Gruppe, Bezeichnung oder None)
Ist die Bezeichnung None, wird sie aus der Excel übernommen.
Blatt 2 = "2. Ein- und Ausgaben", Blatt 5 = "5. Strompreis".
"""

# Zellen, die in der Excel gelb sind, aber keine Rechengröße (Schaltflächen, manuelle Hilfseingaben).
NICHT_UEBERNOMMEN = {
    "C72": "Schaltfläche für den Lastgang-Import; ersetzt durch Datei-Upload",
    "C87": "Schaltfläche für den CO2-Daten-Import; ersetzt durch Datei-Upload",
    "C92": "Schaltfläche für den §13k-Daten-Import; ersetzt durch Datei-Upload",
    "C185": "Schaltfläche zur Auswahl der Privilegierungen; ersetzt durch Eingabemaske",
    "F129": "Manuelle Hilfseingabe (Wert aus F127 von Hand eintragen); wird im Tool berechnet",
}

BLATT2 = {
    # System
    "C5":   ("commissioning_year", "System", None),
    "C6":   ("electrolyzer_power_kw", "System", None),
    "C7":   ("capex_electrolyzer_eur_per_kw", "System", None),
    "C8":   ("project_lifetime_years", "System", None),
    "C9":   ("electrolyzer_efficiency", "System", None),
    "C10":  ("min_part_load", "System", "Minimale Systemteillast"),
    "C12":  ("sensitivity_step", "System", "Schrittweite für Sensitivitätsanalyse"),
    # CAPEX
    "C23":  ("capex_epc_eur_per_kw", "CAPEX", "EPC (Engineering, Procurement, Construction)"),
    "C26":  ("capex_bop_eur_per_kw", "CAPEX", "Balance of Plant"),
    "C29":  ("capex_building_eur_per_kw", "CAPEX", "Kosten Hochbau"),
    "C30":  ("capex_civil_eur_per_kw", "CAPEX", "Kosten Tiefbau"),
    "C33":  ("waste_heat_enabled", "CAPEX", "Abwärme nutzbar?"),
    "C34":  ("capex_waste_heat_eur_per_kw", "CAPEX", "Abwärmesystem"),
    "C37":  ("oxygen_enabled", "CAPEX", "Sauerstoff nutzbar?"),
    "C38":  ("capex_oxygen_eur_per_kw", "CAPEX", "Sauerstoffsystem"),
    "C41":  ("h2_processing_mode", "CAPEX", "Art der Wasserstoff-Aufbereitung"),
    "C42":  ("capex_h2_compression_eur_per_kw", "CAPEX", "Verdichtersystem"),
    "C43":  ("capex_h2_direct_eur_per_kw", "CAPEX", "Direktsystem"),
    "C54":  ("capex_custom_1_eur_per_kw", "CAPEX", "Individuelle CAPEX 1 (z. B. Netzanschluss)"),
    "C55":  ("capex_custom_2_share_of_electrolyzer", "CAPEX", "Individuelle CAPEX 2 (z. B. H2-Speicher)"),
    "C56":  ("capex_custom_3_eur", "CAPEX", "Individuelle CAPEX 3"),
    # Batterie
    "C46":  ("battery_enabled", "Batteriesystem", "Batteriesystem berücksichtigen?"),
    "C47":  ("battery_capacity_hours", "Batteriesystem", "Faktor Speicherkapazität"),
    "C48":  ("battery_input_power_kw", "Batteriesystem", "Installierte Eingangsleistung"),
    "C49":  ("battery_capex_eur_per_kwh", "Batteriesystem", "Spezifische Investitionskosten"),
    "C50":  ("battery_other_costs_eur", "Batteriesystem", "Sonstige Kosten"),
    # Strombezug PPA
    "C62":  ("ppa_baseload_enabled", "Strombezug: PPA", "PPA Baseload aktiv"),
    "C63":  ("ppa_baseload_kw", "Strombezug: PPA", "Leistung Baseload-PPA"),
    "C64":  ("ppa_baseload_price_eur_per_mwh", "Strombezug: PPA", "Strompreis Baseload-PPA"),
    "C65":  ("ppa_baseload_price_escalation", "Strombezug: PPA", "Preisentwicklung Baseload-PPA pro Jahr"),
    "C66":  ("ppa_pap_enabled", "Strombezug: PPA", "PPA Pay-as-Produced aktiv"),
    "C67":  ("ppa_pv_kw", "Strombezug: PPA", "Installierte Leistung PPA PV"),
    "C68":  ("ppa_pv_price_eur_per_mwh", "Strombezug: PPA", "Strompreis PPA PV"),
    "C69":  ("ppa_wind_kw", "Strombezug: PPA", "Installierte Leistung PPA Wind"),
    "C70":  ("ppa_wind_price_eur_per_mwh", "Strombezug: PPA", "Strompreis PPA Wind"),
    "C71":  ("ppa_pap_price_escalation", "Strombezug: PPA", "Preisentwicklung Pay-as-Produced-PPA pro Jahr"),
    # Spotmarkt
    "C76":  ("spot_max_price_eur_per_mwh", "Strombezug: Spotmarkt", "Maximaler Preis Nachfrage"),
    "C77":  ("spot_price_escalation", "Strombezug: Spotmarkt", "Preisentwicklung Spotmarkt pro Jahr"),
    "C79":  ("spot_enabled", "Strombezug: Spotmarkt", "Spotmarkt generell / unspezifisch"),
    "C80":  ("spot_price_source", "Strombezug: Spotmarkt", "Strompreis Spotmarkt"),
    "C81":  ("spot_own_price_eur_per_mwh", "Strombezug: Spotmarkt", "Strompreis Spotmarkt (eigener Wert)"),
    # §7
    "C83":  ("section7_enabled", "Strombezug: §7 37. BImSchV", "Strombezug nach 37. BImSchV §7 Abs. 3"),
    "C84":  ("section7_negative_prices", "Strombezug: §7 37. BImSchV", "Negative Preise berücksichtigen?"),
    "C86":  ("co2_price_source", "Strombezug: §7 37. BImSchV", "CO2-Preis: Jahresdaten oder selbst gewählt"),
    "C88":  ("co2_own_price_eur_per_t", "Strombezug: §7 37. BImSchV", "Eigener CO2-Börsenpreis"),
    "C89":  ("co2_price_escalation", "Strombezug: §7 37. BImSchV", "Preisentwicklung CO2 pro Jahr"),
    # §13k
    "C91":  ("section13k_enabled", "Strombezug: §13k EnWG", "§13k „Nutzen statt Abregeln“ aktiv"),
    "C93":  ("section13k_price_eur_per_mwh", "Strombezug: §13k EnWG", "Strompreis §13k"),
    "C94":  ("section13k_price_escalation", "Strombezug: §13k EnWG", "Preisentwicklung §13k pro Jahr"),
    # Leistungspreis
    "C100": ("demand_charge_ely_eur_per_kw_month", "Stromnebenkosten", "Leistungspreis Elektrolyseur"),
    "C101": ("demand_charge_rest_eur_per_kw_month", "Stromnebenkosten", "Leistungspreis übrige Verbraucher"),
    # Aufbereitung & Peripherie
    "C105": ("peripherals_share_of_ely", "Aufbereitung & Peripherie", "Stromverbrauch Peripherie (Anteil am Elektrolyseur)"),
    "C108": ("h2_processed_share", "Aufbereitung & Peripherie", "Anteil aufbereiteter Wasserstoff an Jahresproduktion"),
    "C109": ("h2_compressor_pressure_bar", "Aufbereitung & Peripherie", "H2-Verdichter: Ausgangsdruck"),
    "C110": ("h2_inlet_temperature_c", "Aufbereitung & Peripherie", "H2-Verdichter: Eintrittstemperatur"),
    "C111": ("h2_inlet_pressure_bar", "Aufbereitung & Peripherie", "H2-Verdichter: Eingangsdruck"),
    "C112": ("h2_compressor_efficiency", "Aufbereitung & Peripherie", "H2-Verdichter: Wirkungsgrad"),
    "C114": ("o2_compressor_pressure_bar", "Aufbereitung & Peripherie", "O2-Verdichter: Ausgangsdruck"),
    "C115": ("o2_inlet_temperature_c", "Aufbereitung & Peripherie", "O2-Verdichter: Eintrittstemperatur"),
    "C116": ("o2_inlet_pressure_bar", "Aufbereitung & Peripherie", "O2-Verdichter: Eingangsdruck"),
    "C117": ("o2_compressor_efficiency", "Aufbereitung & Peripherie", "O2-Verdichter: Wirkungsgrad"),
    # Stacktausch
    "C124": ("stack_lifetime_h", "Stacktausch", None),
    "C125": ("stack_degradation_per_year", "Stacktausch", None),
    "C126": ("stack_replacement_cost_share", "Stacktausch", "Kosten Stacktausch Jahr 0 (Anteil der Elektrolyseur-Kosten)"),
    "C127": ("stack_cost_degression", "Stacktausch", "Kostendegression durch Skaleneffekte pro Jahr"),
    "C128": ("stack_interest_rate", "Stacktausch", "Zins Fremdkapital Stacktausch"),
    # OPEX
    "C133": ("opex_lump_sum_enabled", "OPEX", "OPEX Total pauschal vorgeben?"),
    "G133": ("opex_lump_sum_share_of_capex", "OPEX", "Pauschale OPEX (Anteil am CAPEX)"),
    "G134": ("opex_lump_sum_escalation", "OPEX", "Preisentwicklung pauschale OPEX pro Jahr"),
    "C136": ("maintenance_share_of_capex", "OPEX", "Wartung & Instandhaltung (Anteil am CAPEX)"),
    "C137": ("maintenance_escalation", "OPEX", "Preisentwicklung Wartung pro Jahr"),
    "C140": ("personnel_eur_per_year", "OPEX", "Personalkosten abzüglich Wartung & Instandhaltung"),
    "C141": ("personnel_escalation", "OPEX", "Preisentwicklung Personal pro Jahr"),
    "C144": ("replacement_reserve_share_of_capex", "OPEX", "Ersatzinvestition restliche Anlage (Anteil am CAPEX)"),
    "C145": ("decommissioning_share_of_capex", "OPEX", "Rückbau (Anteil am CAPEX)"),
    "C146": ("reserves_escalation", "OPEX", "Preisentwicklung Rückstellungen pro Jahr"),
    "C149": ("water_fresh_eur_per_m3", "OPEX", "Preis Frischwasser"),
    "C150": ("water_treatment_eur_per_m3", "OPEX", "Preis Aufbereitung Frischwasser"),
    "C151": ("water_waste_eur_per_m3", "OPEX", "Preis Abwasser"),
    "C152": ("water_escalation", "OPEX", "Preisentwicklung Wasser pro Jahr"),
    "C155": ("other_opex_share_of_capex", "OPEX", "Sonstige OPEX, z. B. Versicherung (Anteil am CAPEX)"),
    "C156": ("other_opex_escalation", "OPEX", "Preisentwicklung sonstige OPEX pro Jahr"),
    # Finanzierung
    "C161": ("debt_share", "Finanzierung", "Quote Fremdkapital"),
    "C162": ("debt_interest_rate", "Finanzierung", "Zins Fremdkapital"),
    "C163": ("equity_interest_rate", "Finanzierung", "Kalkulatorischer Zins Eigenkapital"),
    "C164": ("corporate_tax_rate", "Finanzierung", "Unternehmenssteuersatz (für WACC)"),
    # Förderungen
    "C169": ("capex_subsidy_mode", "Förderungen", "CAPEX-Förderung"),
    "C170": ("capex_subsidy_percent", "Förderungen", "CAPEX-Förderung prozentual (auf CAPEX Total)"),
    "C171": ("capex_subsidy_eur_per_kw", "Förderungen", "CAPEX-Förderung absolut"),
    "C174": ("opex_subsidy_mode", "Förderungen", "OPEX-Förderung"),
    "C175": ("opex_subsidy_eur_per_kg", "Förderungen", "OPEX-Förderung pro produziertem kg H2"),
    "C176": ("opex_subsidy_eur_per_full_load_hour", "Förderungen", "OPEX-Förderung pro Volllaststunde"),
    "C179": ("power_subsidy_mode", "Förderungen", "Strompreisförderung"),
    "C180": ("power_subsidy_eur_per_kg", "Förderungen", "Strompreisförderung pro produziertem kg H2"),
    "C181": ("power_subsidy_eur_per_mwh", "Förderungen", "Strompreisförderung pro verbrauchter MWh"),
    # Strompreiskompensation
    "C189": ("spk_mode", "Strompreiskompensation", "Strompreiskompensation"),
    "C190": ("spk_eua_price_eur_per_t", "Strompreiskompensation", "EUA-Preis"),
    "C191": ("spk_consumption_factor", "Strompreiskompensation", "Faktor zum Stromverbrauch"),
    "C192": ("spk_escalation", "Strompreiskompensation", "Jährliche Preisentwicklung SPK"),
    "C193": ("spk_separate_revenue_eur", "Strompreiskompensation", "Separat kalkulierter Ertrag durch SPK"),
    # THG
    "C198": ("thg_enabled", "THG-Quote", "THG-Quote berücksichtigen"),
    "C199": ("thg_price_eur_per_t", "THG-Quote", None),
    "C200": ("thg_mobility_share", "THG-Quote", "Anteil für Mobilitätssektor"),
    "C201": ("thg_producer_share", "THG-Quote", "Anteil an THG-Einnahmen (Erzeuger / Tankstelle)"),
    "C202": ("thg_h2_intensity_kgco2_per_gj", "THG-Quote", "THG-Intensität des Wasserstoffs"),
    "C203": ("thg_adjustment_factor", "THG-Quote", "Anpassungsfaktor (0,4 Brennstoffzellen-Elektroantrieb, 1 Verbrennungsmotor)"),
    "C204": ("thg_price_escalation", "THG-Quote", "Jährliche Preissteigerung THG-Quote"),
    # Weitere Einnahmen
    "C207": ("power_sale_enabled", "Weitere Einnahmen", "Verkauf übriger Strommenge"),
    "C208": ("power_sale_mode", "Weitere Einnahmen", "Vermarktung übriger Strommenge"),
    "C209": ("power_sale_ppa_price_eur_per_mwh", "Weitere Einnahmen", "PPA-Verkaufspreis heute"),
    "C210": ("power_sale_ppa_escalation", "Weitere Einnahmen", "Jährliche Preisentwicklung PPA-Verkaufspreis"),
    "C213": ("oxygen_price_eur_per_t", "Weitere Einnahmen", "Verkaufspreis Sauerstoff"),
    "C214": ("oxygen_price_escalation", "Weitere Einnahmen", "Jährliche Preissteigerung Sauerstoff"),
    "C217": ("heat_price_eur_per_mwh", "Weitere Einnahmen", "Verkaufspreis Abwärme"),
    "C218": ("heat_usable_share", "Weitere Einnahmen", "Anteil nutzbarer Abwärme"),
    "C219": ("heat_price_escalation", "Weitere Einnahmen", "Jährliche Preissteigerung Abwärme"),
    "C222": ("balancing_enabled", "Weitere Einnahmen", "Regelenergie berücksichtigen"),
    "C223": ("balancing_revenue_eur_per_year", "Weitere Einnahmen", "Kalkulierter Ertrag durch Regelenergie"),
    "C224": ("balancing_escalation", "Weitere Einnahmen", "Jährliche Preissteigerung Regelenergie"),
    "C227": ("other_revenue_enabled", "Weitere Einnahmen", "Sonstige Einnahmen berücksichtigen"),
    "C228": ("other_revenue_1_eur_per_year", "Weitere Einnahmen", "Sonstige Einnahmen 1"),
    "C229": ("other_revenue_1_escalation", "Weitere Einnahmen", "Jährliche Preissteigerung sonstige 1"),
    "C230": ("other_revenue_2_eur_per_year", "Weitere Einnahmen", "Sonstige Einnahmen 2"),
    "C231": ("other_revenue_2_escalation", "Weitere Einnahmen", "Jährliche Preissteigerung sonstige 2"),
}

# Stromnebenkosten (Blatt 5): Zeile -> Schlüsselteil, Bezeichnung
NEBENKOSTEN = {
    6:  ("grid_fee", "Netzentgelt"),
    8:  ("electricity_tax", "Stromsteuer"),
    10: ("concession_fee", "Konzessionsabgabe"),
    12: ("kwk_levy", "KWK-Aufschlag"),
    14: ("stromnev19_levy", "StromNEV-§19-Umlage"),
    16: ("offshore_levy", "Offshore-Netzumlage"),
}
# Spalten: Elektrolyseur (H = Wert in ct/kWh, J = Befreiung), übrige Verbraucher (M = Wert, O = Befreiung)
