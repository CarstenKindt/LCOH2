# Zuordnung Excel und Python-Tool

Diese Datei wird automatisch erzeugt (`python tools/build_docs.py`). Alle Standardwerte stammen aus `Berechnungstool_Modell_Rev_10.xlsx`.

## System

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| Jahr der Inbetriebnahme | `commissioning_year` |  | 2026 | Blatt 2, C5 |
| Leistung Elektrolyseur (Ely) | `electrolyzer_power_kw` | kW | 25000 | Blatt 2, C6 |
| Spez. Investitionskosten Ely | `capex_electrolyzer_eur_per_kw` | € / kW | 1000 | Blatt 2, C7 |
| Projektlaufzeit | `project_lifetime_years` | a | 20 | Blatt 2, C8 |
| Effizienz Elektrolyse | `electrolyzer_efficiency` | % | 70 % | Blatt 2, C9 |
| Minimale Systemteillast | `min_part_load` | % | 20 % | Blatt 2, C10 |
| Schrittweite für Sensitivitätsanalyse | `sensitivity_step` | % | 30 % | Blatt 2, C12 |

## CAPEX

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| EPC (Engineering, Procurement, Construction) | `capex_epc_eur_per_kw` | € / kW | 120 | Blatt 2, C23 |
| Balance of Plant | `capex_bop_eur_per_kw` | € / kW | 750 | Blatt 2, C26 |
| Kosten Hochbau | `capex_building_eur_per_kw` | € / kW | 1000 | Blatt 2, C29 |
| Kosten Tiefbau | `capex_civil_eur_per_kw` | € / kW | 300 | Blatt 2, C30 |
| Abwärme nutzbar? | `waste_heat_enabled` |  | ja | Blatt 2, C33 |
| Abwärmesystem | `capex_waste_heat_eur_per_kw` | € / kW | 10 | Blatt 2, C34 |
| Sauerstoff nutzbar? | `oxygen_enabled` |  | ja | Blatt 2, C37 |
| Sauerstoffsystem | `capex_oxygen_eur_per_kw` | € / kW | 30 | Blatt 2, C38 |
| Art der Wasserstoff-Aufbereitung | `h2_processing_mode` |  | Verdichtung | Blatt 2, C41 |
| Verdichtersystem | `capex_h2_compression_eur_per_kw` | € / kW | 30 | Blatt 2, C42 |
| Direktsystem | `capex_h2_direct_eur_per_kw` | € / kW | 10 | Blatt 2, C43 |
| Individuelle CAPEX 1 (z. B. Netzanschluss) | `capex_custom_1_eur_per_kw` | € / kW | 0 | Blatt 2, C54 |
| Individuelle CAPEX 2 (z. B. H2-Speicher) | `capex_custom_2_share_of_electrolyzer` | % (von spez. Kosten Ely) | 0 % | Blatt 2, C55 |
| Individuelle CAPEX 3 | `capex_custom_3_eur` | € | 0 | Blatt 2, C56 |

## Batteriesystem

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| Batteriesystem berücksichtigen? | `battery_enabled` |  | ja | Blatt 2, C46 |
| Faktor Speicherkapazität | `battery_capacity_hours` | h | 5 | Blatt 2, C47 |
| Installierte Eingangsleistung | `battery_input_power_kw` | kW | 50000 | Blatt 2, C48 |
| Spezifische Investitionskosten | `battery_capex_eur_per_kwh` | € / kWh | 220 | Blatt 2, C49 |
| Sonstige Kosten | `battery_other_costs_eur` | € | 0 | Blatt 2, C50 |

## Strombezug: PPA

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| PPA Baseload aktiv | `ppa_baseload_enabled` |  | ja | Blatt 2, C62 |
| Leistung Baseload-PPA | `ppa_baseload_kw` | kWh / h | 5000 | Blatt 2, C63 |
| Strompreis Baseload-PPA | `ppa_baseload_price_eur_per_mwh` | € / MWh | 85 | Blatt 2, C64 |
| Preisentwicklung Baseload-PPA pro Jahr | `ppa_baseload_price_escalation` | % | 3 % | Blatt 2, C65 |
| PPA Pay-as-Produced aktiv | `ppa_pap_enabled` |  | ja | Blatt 2, C66 |
| Installierte Leistung PPA PV | `ppa_pv_kw` | kWh / h | 10000 | Blatt 2, C67 |
| Strompreis PPA PV | `ppa_pv_price_eur_per_mwh` | € / MWh | 40 | Blatt 2, C68 |
| Installierte Leistung PPA Wind | `ppa_wind_kw` | kWh / h | 30000 | Blatt 2, C69 |
| Strompreis PPA Wind | `ppa_wind_price_eur_per_mwh` | € / MWh | 75 | Blatt 2, C70 |
| Preisentwicklung Pay-as-Produced-PPA pro Jahr | `ppa_pap_price_escalation` | % | 0 % | Blatt 2, C71 |

## Strombezug: Spotmarkt

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| Maximaler Preis Nachfrage | `spot_max_price_eur_per_mwh` | € / MWh | 70 | Blatt 2, C76 |
| Preisentwicklung Spotmarkt pro Jahr | `spot_price_escalation` | % | 0 % | Blatt 2, C77 |
| Spotmarkt generell / unspezifisch | `spot_enabled` |  | nein | Blatt 2, C79 |
| Strompreis Spotmarkt | `spot_price_source` |  | Marktpreise | Blatt 2, C80 |
| Strompreis Spotmarkt (eigener Wert) | `spot_own_price_eur_per_mwh` | € / MWh | 0 | Blatt 2, C81 |
| Börsenpreis-Szenario (Jahr) | `day_ahead_scenario_year` |  | 2024 | Blatt 8, G6 |

## Strombezug: §7 37. BImSchV

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| Strombezug nach 37. BImSchV §7 Abs. 3 | `section7_enabled` |  | ja | Blatt 2, C83 |
| Negative Preise berücksichtigen? | `section7_negative_prices` |  | ja | Blatt 2, C84 |
| CO2-Preis: Jahresdaten oder selbst gewählt | `co2_price_source` |  | Jahresdaten | Blatt 2, C86 |
| Eigener CO2-Börsenpreis | `co2_own_price_eur_per_t` | € / t_CO2 | 0 | Blatt 2, C88 |
| Preisentwicklung CO2 pro Jahr | `co2_price_escalation` | % | 0 % | Blatt 2, C89 |

## Strombezug: §13k EnWG

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| §13k „Nutzen statt Abregeln“ aktiv | `section13k_enabled` |  | nein | Blatt 2, C91 |
| Strompreis §13k | `section13k_price_eur_per_mwh` | € / MWh | 30 | Blatt 2, C93 |
| Preisentwicklung §13k pro Jahr | `section13k_price_escalation` | % | 0 % | Blatt 2, C94 |

## Stromnebenkosten

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| Leistungspreis Elektrolyseur | `demand_charge_ely_eur_per_kw_month` | € / kW * Monat | 2 | Blatt 2, C100 |
| Leistungspreis übrige Verbraucher | `demand_charge_rest_eur_per_kw_month` | € / kW * Monat | 2 | Blatt 2, C101 |
| Netzentgelt Elektrolyseur | `levy_ely_grid_fee_ct_per_kwh` | ct/kWh | 11 | Blatt 5, H6 |
| Netzentgelt Elektrolyseur: befreit? | `levy_ely_grid_fee_exempt` |  | ja | Blatt 5, J6 |
| Netzentgelt übrige Verbraucher | `levy_rest_grid_fee_ct_per_kwh` | ct/kWh | 11 | Blatt 5, M6 |
| Netzentgelt übrige Verbraucher: befreit? | `levy_rest_grid_fee_exempt` |  | ja | Blatt 5, O6 |
| Stromsteuer Elektrolyseur | `levy_ely_electricity_tax_ct_per_kwh` | ct/kWh | 0.5 | Blatt 5, H8 |
| Stromsteuer Elektrolyseur: befreit? | `levy_ely_electricity_tax_exempt` |  | ja | Blatt 5, J8 |
| Stromsteuer übrige Verbraucher | `levy_rest_electricity_tax_ct_per_kwh` | ct/kWh | 0.5 | Blatt 5, M8 |
| Stromsteuer übrige Verbraucher: befreit? | `levy_rest_electricity_tax_exempt` |  | ja | Blatt 5, O8 |
| Konzessionsabgabe Elektrolyseur | `levy_ely_concession_fee_ct_per_kwh` | ct/kWh | 1.66 | Blatt 5, H10 |
| Konzessionsabgabe Elektrolyseur: befreit? | `levy_ely_concession_fee_exempt` |  | ja | Blatt 5, J10 |
| Konzessionsabgabe übrige Verbraucher | `levy_rest_concession_fee_ct_per_kwh` | ct/kWh | 1.66 | Blatt 5, M10 |
| Konzessionsabgabe übrige Verbraucher: befreit? | `levy_rest_concession_fee_exempt` |  | ja | Blatt 5, O10 |
| KWK-Aufschlag Elektrolyseur | `levy_ely_kwk_levy_ct_per_kwh` | ct/kWh | 0.275 | Blatt 5, H12 |
| KWK-Aufschlag Elektrolyseur: befreit? | `levy_ely_kwk_levy_exempt` |  | ja | Blatt 5, J12 |
| KWK-Aufschlag übrige Verbraucher | `levy_rest_kwk_levy_ct_per_kwh` | ct/kWh | 0.275 | Blatt 5, M12 |
| KWK-Aufschlag übrige Verbraucher: befreit? | `levy_rest_kwk_levy_exempt` |  | ja | Blatt 5, O12 |
| StromNEV-§19-Umlage Elektrolyseur | `levy_ely_stromnev19_levy_ct_per_kwh` | ct/kWh | 1.56 | Blatt 5, H14 |
| StromNEV-§19-Umlage Elektrolyseur: befreit? | `levy_ely_stromnev19_levy_exempt` |  | ja | Blatt 5, J14 |
| StromNEV-§19-Umlage übrige Verbraucher | `levy_rest_stromnev19_levy_ct_per_kwh` | ct/kWh | 1.56 | Blatt 5, M14 |
| StromNEV-§19-Umlage übrige Verbraucher: befreit? | `levy_rest_stromnev19_levy_exempt` |  | ja | Blatt 5, O14 |
| Offshore-Netzumlage Elektrolyseur | `levy_ely_offshore_levy_ct_per_kwh` | ct/kWh | 0.82 | Blatt 5, H16 |
| Offshore-Netzumlage Elektrolyseur: befreit? | `levy_ely_offshore_levy_exempt` |  | ja | Blatt 5, J16 |
| Offshore-Netzumlage übrige Verbraucher | `levy_rest_offshore_levy_ct_per_kwh` | ct/kWh | 0.82 | Blatt 5, M16 |
| Offshore-Netzumlage übrige Verbraucher: befreit? | `levy_rest_offshore_levy_exempt` |  | ja | Blatt 5, O16 |
| Leistungspreis Elektrolyseur: befreit? | `demand_charge_ely_exempt` |  | ja | Blatt 5, J17 |
| Leistungspreis übrige Verbraucher: befreit? | `demand_charge_rest_exempt` |  | ja | Blatt 5, O17 |

## Aufbereitung & Peripherie

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| Stromverbrauch Peripherie (Anteil am Elektrolyseur) | `peripherals_share_of_ely` | % (Stromverbrauch Ely) | 20 % | Blatt 2, C105 |
| Anteil aufbereiteter Wasserstoff an Jahresproduktion | `h2_processed_share` | % | 100 % | Blatt 2, C108 |
| H2-Verdichter: Ausgangsdruck | `h2_compressor_pressure_bar` | bar | 300 | Blatt 2, C109 |
| H2-Verdichter: Eintrittstemperatur | `h2_inlet_temperature_c` | °C | 20 | Blatt 2, C110 |
| H2-Verdichter: Eingangsdruck | `h2_inlet_pressure_bar` | bar | 10 | Blatt 2, C111 |
| H2-Verdichter: Wirkungsgrad | `h2_compressor_efficiency` | % | 75 % | Blatt 2, C112 |
| O2-Verdichter: Ausgangsdruck | `o2_compressor_pressure_bar` | bar | 300 | Blatt 2, C114 |
| O2-Verdichter: Eintrittstemperatur | `o2_inlet_temperature_c` | °C | 20 | Blatt 2, C115 |
| O2-Verdichter: Eingangsdruck | `o2_inlet_pressure_bar` | bar | 10 | Blatt 2, C116 |
| O2-Verdichter: Wirkungsgrad | `o2_compressor_efficiency` | % | 70 % | Blatt 2, C117 |

## Stacktausch

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| Lebenszeit Stacks | `stack_lifetime_h` | h | 80000 | Blatt 2, C124 |
| Degradation Stacks | `stack_degradation_per_year` | % (pro Jahr) | 0.8 % | Blatt 2, C125 |
| Kosten Stacktausch Jahr 0 (Anteil der Elektrolyseur-Kosten) | `stack_replacement_cost_share` | % (von Kosten Ely) | 50 % | Blatt 2, C126 |
| Kostendegression durch Skaleneffekte pro Jahr | `stack_cost_degression` | % (durch Skaleneffekte p.a.) | -5 % | Blatt 2, C127 |
| Zins Fremdkapital Stacktausch | `stack_interest_rate` | % | 5 % | Blatt 2, C128 |

## OPEX

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| OPEX Total pauschal vorgeben? | `opex_lump_sum_enabled` |  | nein | Blatt 2, C133 |
| Pauschale OPEX (Anteil am CAPEX) | `opex_lump_sum_share_of_capex` | % | 3 % | Blatt 2, G133 |
| Preisentwicklung pauschale OPEX pro Jahr | `opex_lump_sum_escalation` | % | 0 % | Blatt 2, G134 |
| Wartung & Instandhaltung (Anteil am CAPEX) | `maintenance_share_of_capex` | % (von Capex Total) | 0.5 % | Blatt 2, C136 |
| Preisentwicklung Wartung pro Jahr | `maintenance_escalation` | % | 0 % | Blatt 2, C137 |
| Personalkosten abzüglich Wartung & Instandhaltung | `personnel_eur_per_year` | € / a | 85000 | Blatt 2, C140 |
| Preisentwicklung Personal pro Jahr | `personnel_escalation` | % | 0 % | Blatt 2, C141 |
| Ersatzinvestition restliche Anlage (Anteil am CAPEX) | `replacement_reserve_share_of_capex` | % (von Capex Total) | 1 % | Blatt 2, C144 |
| Rückbau (Anteil am CAPEX) | `decommissioning_share_of_capex` | % (von Capex Total) | 0.25 % | Blatt 2, C145 |
| Preisentwicklung Rückstellungen pro Jahr | `reserves_escalation` | % | 0 % | Blatt 2, C146 |
| Preis Frischwasser | `water_fresh_eur_per_m3` | € / m³ | 4 | Blatt 2, C149 |
| Preis Aufbereitung Frischwasser | `water_treatment_eur_per_m3` | € / m³ | 5 | Blatt 2, C150 |
| Preis Abwasser | `water_waste_eur_per_m3` | € / m³ | 6.5 | Blatt 2, C151 |
| Preisentwicklung Wasser pro Jahr | `water_escalation` | % | 0 % | Blatt 2, C152 |
| Sonstige OPEX, z. B. Versicherung (Anteil am CAPEX) | `other_opex_share_of_capex` | % (von Capex Total) | 0.5 % | Blatt 2, C155 |
| Preisentwicklung sonstige OPEX pro Jahr | `other_opex_escalation` | % | 0 % | Blatt 2, C156 |

## Finanzierung

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| Quote Fremdkapital | `debt_share` | % | 80 % | Blatt 2, C161 |
| Zins Fremdkapital | `debt_interest_rate` | % | 6.5 % | Blatt 2, C162 |
| Kalkulatorischer Zins Eigenkapital | `equity_interest_rate` | % | 10 % | Blatt 2, C163 |
| Unternehmenssteuersatz (für WACC) | `corporate_tax_rate` | % | 30 % | Blatt 2, C164 |

## Förderungen

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| CAPEX-Förderung | `capex_subsidy_mode` |  | Ohne | Blatt 2, C169 |
| CAPEX-Förderung prozentual (auf CAPEX Total) | `capex_subsidy_percent` | % (auf Capex Total) | 10 % | Blatt 2, C170 |
| CAPEX-Förderung absolut | `capex_subsidy_eur_per_kw` | € / kW | 500 | Blatt 2, C171 |
| OPEX-Förderung | `opex_subsidy_mode` |  | Ohne | Blatt 2, C174 |
| OPEX-Förderung pro produziertem kg H2 | `opex_subsidy_eur_per_kg` | € / kg | 0.25 | Blatt 2, C175 |
| OPEX-Förderung pro Volllaststunde | `opex_subsidy_eur_per_full_load_hour` | € / h | 0 | Blatt 2, C176 |
| Strompreisförderung | `power_subsidy_mode` |  | Ohne | Blatt 2, C179 |
| Strompreisförderung pro produziertem kg H2 | `power_subsidy_eur_per_kg` | € / kg_H2 | 0 | Blatt 2, C180 |
| Strompreisförderung pro verbrauchter MWh | `power_subsidy_eur_per_mwh` | € / MWh | 10 | Blatt 2, C181 |

## Strompreiskompensation

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| Strompreiskompensation | `spk_mode` |  | Ohne | Blatt 2, C189 |
| EUA-Preis | `spk_eua_price_eur_per_t` | € / t_CO2 | 89 | Blatt 2, C190 |
| Faktor zum Stromverbrauch | `spk_consumption_factor` | % | 80 % | Blatt 2, C191 |
| Jährliche Preisentwicklung SPK | `spk_escalation` | % | 0 % | Blatt 2, C192 |
| Separat kalkulierter Ertrag durch SPK | `spk_separate_revenue_eur` | € / a | 0 | Blatt 2, C193 |

## THG-Quote

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| THG-Quote berücksichtigen | `thg_enabled` |  | ja | Blatt 2, C198 |
| Preis THG-Quote | `thg_price_eur_per_t` | € / t_CO2 | 300 | Blatt 2, C199 |
| Anteil für Mobilitätssektor | `thg_mobility_share` | % | 75 % | Blatt 2, C200 |
| Anteil an THG-Einnahmen (Erzeuger / Tankstelle) | `thg_producer_share` | % ((Erzeuger / Tankstelle)) | 95 % | Blatt 2, C201 |
| THG-Intensität des Wasserstoffs | `thg_h2_intensity_kgco2_per_gj` | kg_CO2/GJ | 10 | Blatt 2, C202 |
| Anpassungsfaktor (0,4 Brennstoffzellen-Elektroantrieb, 1 Verbrennungsmotor) | `thg_adjustment_factor` |  | 0.4 | Blatt 2, C203 |
| Jährliche Preissteigerung THG-Quote | `thg_price_escalation` | % | 1.5 % | Blatt 2, C204 |

## Weitere Einnahmen

| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |
|---|---|---|---|---|
| Verkauf übriger Strommenge | `power_sale_enabled` |  | ja | Blatt 2, C207 |
| Vermarktung übriger Strommenge | `power_sale_mode` |  | Spotmarkt | Blatt 2, C208 |
| PPA-Verkaufspreis heute | `power_sale_ppa_price_eur_per_mwh` | € / MWh | 0 | Blatt 2, C209 |
| Jährliche Preisentwicklung PPA-Verkaufspreis | `power_sale_ppa_escalation` | % | 0 % | Blatt 2, C210 |
| Verkaufspreis Sauerstoff | `oxygen_price_eur_per_t` | € / t | 50 | Blatt 2, C213 |
| Jährliche Preissteigerung Sauerstoff | `oxygen_price_escalation` | % | 0 % | Blatt 2, C214 |
| Verkaufspreis Abwärme | `heat_price_eur_per_mwh` | € / MWh | 40 | Blatt 2, C217 |
| Anteil nutzbarer Abwärme | `heat_usable_share` | % (der gesamt Abwärme) | 75 % | Blatt 2, C218 |
| Jährliche Preissteigerung Abwärme | `heat_price_escalation` | % | 0 % | Blatt 2, C219 |
| Regelenergie berücksichtigen | `balancing_enabled` |  | ja | Blatt 2, C222 |
| Kalkulierter Ertrag durch Regelenergie | `balancing_revenue_eur_per_year` | € / a | 100000 | Blatt 2, C223 |
| Jährliche Preissteigerung Regelenergie | `balancing_escalation` | % | 0 % | Blatt 2, C224 |
| Sonstige Einnahmen berücksichtigen | `other_revenue_enabled` |  | nein | Blatt 2, C227 |
| Sonstige Einnahmen 1 | `other_revenue_1_eur_per_year` | € / a | 50000 | Blatt 2, C228 |
| Jährliche Preissteigerung sonstige 1 | `other_revenue_1_escalation` | % | 0 % | Blatt 2, C229 |
| Sonstige Einnahmen 2 | `other_revenue_2_eur_per_year` | € / a | 10000 | Blatt 2, C230 |
| Jährliche Preissteigerung sonstige 2 | `other_revenue_2_escalation` | % | 0 % | Blatt 2, C231 |

## Gelbe Excel-Zellen, die bewusst nicht übernommen wurden

| Zelle (Blatt 2) | Grund |
|---|---|
| C72 | Schaltfläche für den Lastgang-Import; ersetzt durch Datei-Upload |
| C87 | Schaltfläche für den CO2-Daten-Import; ersetzt durch Datei-Upload |
| C92 | Schaltfläche für den §13k-Daten-Import; ersetzt durch Datei-Upload |
| C185 | Schaltfläche zur Auswahl der Privilegierungen; ersetzt durch Eingabemaske |
| F129 | Manuelle Hilfseingabe (Wert aus F127 von Hand eintragen); wird im Tool berechnet |
