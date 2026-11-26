"""Standardwerte des Online-Tools. Sie weichen bewusst von der Excel ab (Excel-Werte stehen in `Inputs`).

Stand 26.11.2026: Die Standardwerte entsprechen Szenario S1 der Veröffentlichung „Gestehungskosten grünen
Wasserstoffs – Strombezugsportfolios und Vermarktungsoptionen im Szenarienvergleich“ (⅔ Wind, ⅓ PV; nur Wasserstoff).
"""
from __future__ import annotations

from lcoh.inputs import Inputs


def tool_defaults() -> dict:
    d = Inputs().to_dict()
    d.update({
        "battery_enabled": False, "ppa_baseload_enabled": False, "section7_enabled": True,
        "waste_heat_enabled": False, "oxygen_enabled": False, "spot_enabled": False, "ppa_wind_enabled": True, "ppa_pv_enabled": True,
        "balancing_enabled": False,
        "h2_processing_mode": "direkt",
        "capex_building_eur_per_kw": 500.0,
        "spot_max_price_eur_per_mwh": 100.0,
        "water_fresh_eur_per_m3": 2.0, "water_treatment_eur_per_m3": 2.0, "water_waste_eur_per_m3": 2.0,
        "equity_interest_rate": 0.12,
        "thg_mobility_share": 0.80,
        # Szenario S1
        "ppa_pv_kw": 15000.0,
        "debt_share": 0.70,
        "debt_interest_rate": 0.06,
        "opex_lump_sum_enabled": True,
        "thg_enabled": False,
    })
    for k in d:
        if k.endswith("escalation"):
            d[k] = 0.0
    return d
