"""Stündlicher Strombezug, Batterie und Auslastung (Excel: Blatt 4, Zeilen 14 bis 8773).

Die Excel rechnet jede Stunde nacheinander; der Batteriestand der Vorstunde geht in die
nächste Stunde ein. Die Rechenschritte stehen hier in derselben Reihenfolge wie in der Excel,
die Excel-Spalte steht jeweils als Kommentar dabei.

Hinweis zur Preisgrenze §7: Die Excel vergleicht den Preis der Stunde t mit der Preisgrenze der
Stunde t+1 (Spalte Q verweist auf Zeile R n+1). Das Tool übernimmt das, damit die Ergebnisse mit
der Excel übereinstimmen. Für die letzte Stunde wird die eigene Grenze verwendet.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lcoh import constants as k
from lcoh.inputs import Inputs
from lcoh.prices import MarketSeries
from lcoh.system import SystemPower

OUTPUT_COLUMNS = (
    "baseload_kwh", "pv_kwh", "wind_kwh", "ppa_kwh", "ppa_load_ratio", "battery_charge_ppa_kwh",
    "ppa_util_battery", "price_s7", "s7_kwh", "s7_cost_eur", "ppa_s7_kwh", "battery_charge_s7_kwh",
    "util_s7", "s13k_kwh", "supply_s13k_kwh", "battery_charge_s13k_kwh", "battery_charge_kwh",
    "battery_discharge_kwh", "battery_soc_kwh", "battery_soc", "util_before_spot", "spot_kwh",
    "util_total", "purchase_kwh", "consumption_kwh", "surplus_kwh", "surplus_revenue_eur",
    "spot_cost_eur",
)


def simulate_dispatch(inp: Inputs, ts: pd.DataFrame, market: MarketSeries, power: SystemPower) -> pd.DataFrame:
    n = len(ts)
    C5 = power.total_kw
    V3 = power.battery_capacity_kwh
    V4 = power.battery_power_kw
    F5 = inp.min_part_load
    J3, J4, J5 = inp.ppa_baseload_enabled, inp.ppa_pap_enabled, inp.section7_enabled
    J6, J7, J8 = inp.section13k_enabled, inp.spot_enabled, inp.battery_enabled

    pv_kw = 1e-7 if inp.ppa_pv_kw == 0 else inp.ppa_pv_kw  # Excel M4
    wind_kw = inp.ppa_wind_kw  # Excel M5
    baseload = inp.ppa_baseload_kw if J3 else 0.0  # Excel D

    pv_per_kw = ts["pv_kwh_per_kw"].to_numpy(dtype=float)
    wind_per_kw = ts["wind_kwh_per_kw"].to_numpy(dtype=float)
    price_s7, price_raw, price_sale = market.price_s7, market.price_raw, market.price_sale
    limit = market.section7_limit
    s13k_in = market.section13k_kwh
    spot_max = market.spot_max_price

    out = {c: np.zeros(n) for c in OUTPUT_COLUMNS}
    soc_prev = 0.0      # Excel AA (Vorstunde)
    soc_pct_prev = 0.0  # Excel AB (Vorstunde)

    for t in range(n):
        first = t == 0
        D = baseload
        H = pv_per_kw[t] * pv_kw if J4 else 0.0
        J = wind_per_kw[t] * wind_kw if J4 else 0.0
        L = D + H + J                                            # L: Gesamt PPA-Bezug
        M = L / C5                                               # M: Auslastung System PPA
        N = min(V4, (M - 1.0) * C5 if M > 1.0 else 0.0) if J8 else 0.0   # N: Batterie-Beladung aus PPA
        O = (min(L / V4, 1.0) if J8 else min(L / C5, 1.0))       # O: Auslastung (PPA neu)
        P = price_s7[t]                                          # P: Preis §7
        thr = limit[min(t + 1, n - 1)]                           # R der Folgestunde (Excel-Verhalten)

        # Q: Strom nach §7
        if J5:
            if J8:
                if P <= thr:
                    room = min(max((1.0 - O) * V4, 0.0), V4)
                    second = (V4 - L) if first else max(C5 + (1.0 - soc_pct_prev) * V3 - L, 0.0)
                    Q = min(max(room, 0.0), second)
                else:
                    Q = 0.0
            else:
                Q = max((1.0 - O) * C5, 0.0) if P <= thr else 0.0
        else:
            Q = 0.0
        R = P * Q / k.KWH_PER_MWH                                # R: Kosten §7
        S = L + Q if J5 else L                                   # S: PPA + §7
        T = (min(max(0.0, (S - C5) if L < C5 else (S - L)), V4) if J8 else 0.0)  # T: Beladung aus §7
        U = (min(S / V4, 1.0) if J8 else min(S / C5, 1.0))       # U: Auslastung PPA + §7

        # V: §13k
        if J6:
            if first:
                V = min(max(s13k_in[t], 0.0), V4) if J8 else min(max(s13k_in[t], 0.0), max(C5 - S, 0.0))
            elif J8:
                V = min(s13k_in[t], max(V4 - S, 0.0), max(S + V4 + V3 - soc_prev, 0.0),
                        max(C5 - S + V3 - soc_prev, 0.0))
            else:
                V = min(s13k_in[t], max(C5 - S, 0.0))
        else:
            V = 0.0
        W = S + V if J6 else S                                   # W: PPA + §7 + §13k
        if first:                                                # X: Beladung aus §13k
            X = max(0.0, 0.0 if V == 0 else W - C5)
        else:
            X = 0.0 if soc_pct_prev >= 1.0 else min(max(0.0, 0.0 if V < 1 else W - C5), V3 - soc_prev)

        # Z: Batterie-Entladung
        if first:
            Z = 0.0
        elif J7:
            Z = min(max(0.0, C5 - W), soc_prev, C5)
        elif soc_prev < F5 * C5 and W < F5 * C5:
            Z = 0.0
        else:
            Z = min(max(0.0, C5 - W), soc_prev, C5)

        AC = min((L + Z + Q + V) / C5, 1.0)                      # AC: Auslastung vor Spotmarkt
        AD = (1.0 - AC) * C5 if (J7 and price_raw[t] < spot_max) else 0.0   # AD: Spotmarkt-Strom
        AE = min((L + Z + Q + V + AD) / C5, 1.0)                 # AE: Auslastung gesamt
        AF = W + AD                                              # AF: Strombezug gesamt
        AG = C5 * AE if AE >= F5 else 0.0                        # AG: Stromverbrauch gesamt

        # Y: Batterie-Beladung (hängt von AE und AG derselben Stunde ab)
        if not J8:
            Y = 0.0
        elif first:
            Y = (L + N + T + X) if AG == 0 else (N + T + X)
        else:
            if AE < F5 and P < k.BATTERY_CHARGE_PRICE_LIMIT_EUR_PER_MWH:
                Y = L
            else:
                candidate = (L + N + T + X) if AG == 0 else min(V4 - C5, N + T + X)
                Y = (V3 - soc_prev) if candidate > V3 - soc_prev else min(V4 - C5, N + T + X)
        AA = Y if first else min(soc_prev + Y - Z, V3)           # AA: Ladezustand kWh
        AB = 0.0 if V3 == 0 else AA / V3                         # AB: Ladezustand %
        AH = max(AF - AG - Y, 0.0)                               # AH: Stromüberschuss
        AI = AH * price_sale[t] / k.KWH_PER_MWH if inp.power_sale_enabled else 0.0  # AI: Erlös Verkauf
        AJ = AD * price_raw[t] / k.KWH_PER_MWH                   # AJ: Kosten Spotmarkt

        values = (D, H, J, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z, AA, AB, AC, AD, AE, AF, AG, AH, AI, AJ)
        for col, v in zip(OUTPUT_COLUMNS, values):
            out[col][t] = v
        soc_prev, soc_pct_prev = AA, AB

    return pd.DataFrame(out)
