"""Batterie nach Preissignalen optimieren (Erweiterung über die Excel hinaus).

Die Excel steuert die Batterie nach festen Regeln chronologisch (siehe dispatch.py). Hier plant die Batterie dagegen
vorausschauend: Für jeden Tag wird mit Day-Ahead-Wissen (Preise und PPA-Erzeugung als bekannt angenommen) ein lineares
Optimierungsproblem über den Tag plus einen Vorlauf in die Folgetage gelöst. Der Batteriestand am Tagesende geht in den
nächsten Tag über.

Rangfolge (Ziel): 1. Auslastung des Elektrolysesystems maximieren, 2. Stromkosten minimieren bzw. Verkaufserlöse maximieren.

Energieflüsse je Zeitschritt (alle Mengen in kWh je Schritt):
  Quellen   Grundlast-PPA (fest), Pay-as-Produced-PPA 1 und 2 (fest, werden immer bezogen und bezahlt), §7-Bezug, §13k-Bezug,
            Spotbezug (nur für das Elektrolysesystem), Batterieentladung
  Senken    Elektrolysesystem (höchstens Systemleistung), Batterieladung, Verkauf
  Regeln    Die Batterie lädt nur aus PPA 1/2, §7 und §13k (nicht aus Grundlast-PPA, nicht aus dem Spotmarkt).
            Verkauft wird nur Strom aus PPA (durchgeleitet) oder aus der Batterie; §7-, §13k- und Spotbezug gehen nie direkt
            in den Verkauf. Laden und Entladen sind auf die Batterieleistung (Anschlussleistung minus Systemleistung) begrenzt.
            Der Rundlaufwirkungsgrad wird je zur Hälfte auf Laden und Entladen verteilt.
  Mindestlast Die Optimierung rechnet ohne Mindestlast. Schritte mit einer Last unter der Mindestlast werden danach auf null
            gesetzt; der freiwerdende Strom geht direkt in den Verkauf (Spotbezug und überflüssiger §7-/§13k-Bezug entfallen).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog

from lcoh.dispatch import OUTPUT_COLUMNS
from lcoh.inputs import Inputs
from lcoh.prices import MarketSeries, average_escalation_factor
from lcoh.system import SystemPower

PRIORITY_EUR_PER_KWH = 50.0      # Gewicht der Elektrolyseurauslastung (weit über jedem Strompreis)
LOOKAHEAD_HOURS = 12             # Vorlauf über das Tagesende hinaus
ELY, CH, DIS, SELL, S7, S13, SPOT, SOC = range(8)


def _structure(h: int, eta_c: float, eta_d: float, a):
    """Nebenbedingungen eines Fensters mit h Schritten (hängen nur von h und den Wirkungsgraden ab)."""
    I = sparse.identity(h, format="csr")
    Z = sparse.csr_matrix((h, h))
    A = sparse.diags(a, format="csr")
    sub = sparse.diags([-np.ones(h - 1)], [-1], shape=(h, h), format="csr") if h > 1 else Z
    eq = sparse.vstack([
        sparse.hstack([-I, -I, I, -I, I, I, I, Z]),                       # Energiebilanz
        sparse.hstack([Z, -eta_c * I, (1.0 / eta_d) * I, Z, Z, Z, Z, I + sub]),   # Ladezustand
    ], format="csr")
    ub = sparse.vstack([
        sparse.hstack([Z, I, Z, Z, -I, -I, Z, Z]),                        # Laden <= PAP + §7 + §13k
        sparse.hstack([-I, Z, Z, Z, Z, Z, I, Z]),                         # Spot <= Verbrauch
        sparse.hstack([Z, Z, -I, I, A, A, A, Z]),                         # Verkauf + Netzbezug <= PPA-Überschuss + Entladung
        sparse.hstack([Z, Z, Z, Z, I, I, I, Z]),                          # Netzbezug (§7 + §13k + Spot) <= Restleistung
    ], format="csr")
    return eq, ub


def simulate_dispatch_optimized(inp: Inputs, ts: pd.DataFrame, market: MarketSeries, power: SystemPower,
                                steps_per_hour: int = 1) -> pd.DataFrame:
    n = len(ts)
    dt = 1.0 / steps_per_hour
    years = inp.project_lifetime_years
    C5 = power.total_kw * dt                      # Systemleistung je Schritt
    V3 = power.battery_capacity_kwh
    Pb = max(power.battery_power_kw - power.total_kw, 0.0) * dt   # Batterieleistung je Schritt
    F5 = inp.min_part_load
    eta_rt = min(max(inp.battery_efficiency, 1e-6), 1.0)
    eta_c = eta_d = float(np.sqrt(eta_rt))

    base = np.full(n, inp.ppa_baseload_kw * dt if inp.ppa_baseload_enabled else 0.0)
    pv_kw = 1e-7 if inp.ppa_pv_kw == 0 else inp.ppa_pv_kw
    pv = ts["pv_kwh_per_kw"].to_numpy(dtype=float) * dt * pv_kw if (inp.ppa_pap_enabled and inp.ppa_pv_enabled) else np.zeros(n)
    wind = ts["wind_kwh_per_kw"].to_numpy(dtype=float) * dt * inp.ppa_wind_kw if (inp.ppa_pap_enabled and inp.ppa_wind_enabled) else np.zeros(n)
    pap = pv + wind
    L = base + pap

    price_raw, price_s7, price_sale = market.price_raw, market.price_s7, market.price_sale
    p7 = price_s7 / 1000.0
    praw = price_raw / 1000.0
    cap7 = np.where(inp.section7_enabled & (price_s7 <= market.section7_limit), C5 + Pb, 0.0)
    cap13 = np.maximum(market.section13k_kwh * dt, 0.0) if inp.section13k_enabled else np.zeros(n)
    p13 = inp.section13k_price_eur_per_mwh * average_escalation_factor(inp.section13k_price_escalation, years) / 1000.0
    capspot = np.where(inp.spot_enabled & (price_raw < market.spot_max_price), C5, 0.0)

    if not inp.power_sale_enabled:
        psale = np.zeros(n)
    elif inp.power_sale_mode == "PPA":
        psale = np.full(n, inp.power_sale_ppa_price_eur_per_mwh / 1000.0)
    else:
        psale = price_sale / 1000.0
    psale = psale * average_escalation_factor(inp.power_sale_ppa_escalation, years)

    # PPA-Strom versorgt zuerst den Elektrolyseur; nur der Überschuss darüber kann verkauft oder geladen werden.
    # Netzstrom füllt nur auf und nur bis zur Batterieeingangsleistung (Bezug insgesamt <= P_in); ist die PPA allein
    # bereits ausreichend, gibt es keinen Netzbezug, damit kein PPA-Strom gegen Netzstrom getauscht wird.
    surplus = np.maximum(L - C5, 0.0)
    gridcap = np.maximum(C5 + Pb - L, 0.0)
    grid_in_sale_row = np.where(L >= C5 - 1e-9, 1.0, 0.0)    # reicht die PPA allein, mindert Netzbezug den verkaufbaren Überschuss

    steps_day = 24 * steps_per_hour
    look = LOOKAHEAD_HOURS * steps_per_hour
    out = {c: np.zeros(n) for c in OUTPUT_COLUMNS}
    ely = np.zeros(n); ch = np.zeros(n); dis = np.zeros(n); sell = np.zeros(n)
    s7 = np.zeros(n); s13 = np.zeros(n); spot = np.zeros(n); soc = np.zeros(n)
    soc0 = 0.0

    for start in range(0, n, steps_day):
        keep = min(steps_day, n - start)
        h = min(steps_day + look, n - start)
        A_eq, A_ub = _structure(h, eta_c, eta_d, grid_in_sale_row[start:start + h])
        w = slice(start, start + h)
        nv = 8 * h
        c = np.zeros(nv)
        c[ELY * h:(ELY + 1) * h] = -PRIORITY_EUR_PER_KWH
        c[SELL * h:(SELL + 1) * h] = -psale[w]
        c[S7 * h:(S7 + 1) * h] = p7[w]
        c[S13 * h:(S13 + 1) * h] = p13
        c[SPOT * h:(SPOT + 1) * h] = praw[w]
        c[(SOC + 1) * h - 1] = -float(np.mean(np.maximum(price_raw[w], 0.0))) / 1000.0 * eta_d   # Endwert des Batteriestands
        lo = np.zeros(nv)
        hi = np.empty(nv)
        hi[ELY * h:(ELY + 1) * h] = C5
        lo[ELY * h:(ELY + 1) * h] = np.minimum(L[w], C5)               # PPA-Strom versorgt zuerst den Elektrolyseur
        hi[CH * h:(CH + 1) * h] = Pb
        hi[DIS * h:(DIS + 1) * h] = Pb
        hi[SELL * h:(SELL + 1) * h] = np.inf
        hi[S7 * h:(S7 + 1) * h] = cap7[w]
        hi[S13 * h:(S13 + 1) * h] = cap13[w]
        hi[SPOT * h:(SPOT + 1) * h] = capspot[w]
        hi[SOC * h:(SOC + 1) * h] = V3
        b_eq = np.concatenate([-L[w], np.r_[soc0, np.zeros(h - 1)]])
        b_ub = np.concatenate([pap[w], np.zeros(h), surplus[w], gridcap[w]])
        res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=np.column_stack([lo, hi]), method="highs")
        if res.status != 0:
            raise RuntimeError(f"Batterie-Optimierung fehlgeschlagen (Tag {start // steps_day + 1}): {res.message}")
        x = res.x
        k = slice(start, start + keep)
        ely[k] = x[ELY * h:ELY * h + keep]; ch[k] = x[CH * h:CH * h + keep]; dis[k] = x[DIS * h:DIS * h + keep]
        sell[k] = x[SELL * h:SELL * h + keep]; s7[k] = x[S7 * h:S7 * h + keep]; s13[k] = x[S13 * h:S13 * h + keep]
        spot[k] = x[SPOT * h:SPOT * h + keep]; soc[k] = x[SOC * h:SOC * h + keep]
        soc0 = float(soc[start + keep - 1])

    # Mindestlast: Schritte unter der Mindestlast abschalten, Strom direkt in den Verkauf
    low = (ely > 1e-9) & (ely < F5 * C5 - 1e-9)
    for t in np.where(low)[0]:
        freed = ely[t]
        ely[t] = 0.0
        d = min(freed, spot[t]); spot[t] -= d; freed -= d
        reducible = max(pap[t] + s7[t] + s13[t] - ch[t], 0.0)         # Bezug, der nicht für das Laden gebraucht wird
        for name, price in sorted((("s7", p7[t]), ("s13", p13)), key=lambda x: -x[1]):
            arr = s7 if name == "s7" else s13
            d = min(freed, arr[t], reducible)
            arr[t] -= d; freed -= d; reducible -= d
        sell[t] += freed

    out["baseload_kwh"], out["pv_kwh"], out["wind_kwh"], out["ppa_kwh"] = base, pv, wind, L
    out["ppa_load_ratio"] = L / C5 if C5 else np.zeros(n)
    out["battery_charge_ppa_kwh"] = np.minimum(ch, pap)
    out["ppa_util_battery"] = np.minimum(L / max(Pb, 1e-9), 1.0)
    out["price_s7"] = price_s7
    out["s7_kwh"] = s7
    out["s7_cost_eur"] = price_s7 * s7 / 1000.0
    out["ppa_s7_kwh"] = L + s7
    out["battery_charge_s7_kwh"] = np.minimum(np.maximum(ch - pap, 0.0), s7)
    out["util_s7"] = np.minimum((L + s7) / C5, 1.0) if C5 else np.zeros(n)
    out["s13k_kwh"] = s13
    out["supply_s13k_kwh"] = L + s7 + s13
    out["battery_charge_s13k_kwh"] = np.maximum(ch - pap - out["battery_charge_s7_kwh"], 0.0)
    out["battery_charge_kwh"], out["battery_discharge_kwh"], out["battery_soc_kwh"] = ch, dis, soc
    out["battery_soc"] = soc / V3 if V3 else np.zeros(n)
    out["util_before_spot"] = np.minimum((ely - spot) / C5, 1.0) if C5 else np.zeros(n)
    out["spot_kwh"] = spot
    out["util_total"] = ely / C5 if C5 else np.zeros(n)
    out["purchase_kwh"] = L + s7 + s13 + spot
    out["consumption_kwh"] = ely
    out["surplus_kwh"] = sell
    out["surplus_revenue_eur"] = sell * price_sale / 1000.0 if inp.power_sale_enabled else np.zeros(n)
    out["spot_cost_eur"] = spot * price_raw / 1000.0
    return pd.DataFrame(out)
