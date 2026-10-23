"""Preisentwicklung und Marktpreis-Zeitreihen (Excel: Blatt 8, Spalten G bis AA)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from lcoh import constants as k
from lcoh.inputs import Inputs


def average_escalation_factor(escalation: float, years: int) -> float:
    """Mittelwert einer jährlich steigenden Preisreihe, bezogen auf den Preis im Jahr 0.

    Excel: Preis / Laufzeit * (((1 + i)^Laufzeit - 1) / i); ohne Preissteigerung der Preis selbst.
    """
    if escalation == 0:
        return 1.0
    return ((1.0 + escalation) ** years - 1.0) / escalation / years


@dataclass(frozen=True)
class MarketSeries:
    """Stundenreihen aus Blatt 8 (jeweils 8760 Werte)."""
    price_raw: np.ndarray        # Q: Börsenpreis mit Preisentwicklung, auch negativ (EUR/MWh)
    price_s7: np.ndarray         # P: Preis für den Bezug nach §7 (negative Preise je nach Eingabe)
    price_sale: np.ndarray       # T: Verkaufspreis Überschuss, nicht negativ
    section7_limit: np.ndarray   # R: Preisgrenze §7, in der Excel um eine Stunde nach hinten verschoben genutzt
    spot_max_price: float        # S: maximaler Nachfragepreis
    section13k_kwh: np.ndarray   # Y: Redispatch-Energie je Stunde


def build_market_series(inp: Inputs, ts: pd.DataFrame) -> MarketSeries:
    years = inp.project_lifetime_years
    scenario_column = f"day_ahead_{inp.day_ahead_scenario_year}_eur_per_mwh"
    base = ts[scenario_column].to_numpy(dtype=float)
    price_raw = base * average_escalation_factor(inp.spot_price_escalation, years)

    price_s7 = price_raw if inp.section7_negative_prices else np.maximum(price_raw, 0.0)
    price_sale = np.maximum(price_raw, 0.0)

    # Preisgrenze §7: 0,36 x CO2-Preis, mindestens 20 EUR/MWh, höchstens maximaler Nachfragepreis
    if inp.co2_price_source == "Jahresdaten":
        co2 = ts["co2_eur_per_t"].to_numpy(dtype=float) * average_escalation_factor(inp.co2_price_escalation, years)
    else:
        co2 = np.full(len(ts), inp.co2_own_price_eur_per_t * average_escalation_factor(inp.co2_price_escalation, years))
    limit = np.minimum(np.maximum(co2 * k.SECTION7_CO2_FACTOR, k.SECTION7_MIN_LIMIT_EUR_PER_MWH),
                       inp.spot_max_price_eur_per_mwh)

    return MarketSeries(price_raw, price_s7, price_sale, limit, inp.spot_max_price_eur_per_mwh,
                        ts["section13k_kwh"].to_numpy(dtype=float))
