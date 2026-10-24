"""Stromkosten, Stromnebenkosten und Stromerlöse (Excel: Blatt 5 "Strompreis", Blatt 3 C34-C45, Blatt 4 Kopfbereich)."""
from __future__ import annotations

from dataclasses import dataclass

from lcoh import constants as k
from lcoh.operation import OperationResult
from lcoh.prices import average_escalation_factor

LEVIES = ("grid_fee", "electricity_tax", "concession_fee", "kwk_levy", "stromnev19_levy", "offshore_levy")


@dataclass(frozen=True)
class PowerCosts:
    # Mengen in kWh pro Jahr (Blatt 4)
    ppa_pv_kwh: float
    ppa_wind_kwh: float
    baseload_kwh: float
    section13k_kwh: float
    section7_kwh: float
    spot_kwh: float
    total_procurement_kwh: float      # Blatt 4, P7
    consumption_total_kwh: float      # Blatt 4, AB5
    consumption_ely_kwh: float        # Blatt 4, Y4
    consumption_rest_kwh: float       # Peripherie + Verdichter
    surplus_kwh: float                # Blatt 4, AB6
    # mittlere Preise in EUR/MWh (Blatt 3 C34-C37, Blatt 4 AK4, Blatt 5 S9)
    price_pv: float
    price_wind: float
    price_baseload: float
    price_13k: float
    price_s7: float
    price_spot: float
    # Nebenkosten in EUR/MWh
    levies_ely: float
    levies_rest: float
    avg_procurement_price: float      # Blatt 5, H4
    # Kosten in EUR pro Jahr
    cost_pv: float
    cost_wind: float
    cost_baseload: float
    cost_13k: float
    cost_s7: float
    cost_spot: float
    cost_levies_ely: float
    cost_levies_rest: float
    cost_total_before_subsidy: float  # Blatt 5, V21
    power_subsidy: float              # Blatt 2, F179
    cost_total: float                 # Blatt 2, G59
    # Stromverkauf (Überschuss), Preise in EUR/MWh
    sale_price_spot: float            # Blatt 3, C44
    sale_price_ppa: float             # Blatt 3, C45
    sale_revenue_spot: float          # Blatt 5, V31
    sale_revenue_ppa: float           # Blatt 5, V32
    # Aufteilung der Nebenkosten (EUR pro Jahr) für Auswertungen
    levy_full_eur: dict               # Abgaben ohne Befreiung, je Komponente (Blatt 5, AI25.. x Mengen)
    levy_actual_eur: dict             # tatsächlich zu zahlende Abgaben je Komponente
    levy_privilege_eur: dict          # Wert der Befreiungen je Komponente (Blatt 5, AE38:AE53)
    demand_charge_eur: float          # tatsächlich zu zahlender Leistungspreis (beide Seiten)
    consumption_periphery_kwh: float
    consumption_o2_kwh: float
    consumption_h2_kwh: float


def power_costs(r: OperationResult) -> PowerCosts:
    inp, h, p = r.inputs, r.hourly, r.power
    years = inp.project_lifetime_years

    def esc(price: float, g: float) -> float:
        return price * average_escalation_factor(g, years)

    # --- Mengen
    pv = float(h["pv_kwh"].sum())
    wind = float(h["wind_kwh"].sum())
    base = float(h["baseload_kwh"].sum()) if inp.ppa_baseload_enabled else 0.0
    s13k = float(h["s13k_kwh"].sum())
    s7 = float(h["s7_kwh"].sum())
    spot = float(h["spot_kwh"].sum())
    ppa_total = float(h["ppa_kwh"].sum())
    procurement = ppa_total + s7 + s13k + spot
    cons = float(h["consumption_kwh"].sum())
    ely = cons * p.ely_kw / p.total_kw
    periph = cons * p.peripherals_kw / p.total_kw
    o2 = cons * p.o2_compressor_kw / p.total_kw
    h2c = cons * p.h2_compressor_kw / p.total_kw
    rest = periph + o2 + h2c
    surplus = float(h["surplus_kwh"].sum())

    # --- Preise
    pe = inp.ppa_pap_price_escalation
    price_pv = esc(inp.ppa_pv_price_eur_per_mwh, pe)
    price_wind = esc(inp.ppa_wind_price_eur_per_mwh, pe)
    price_base = esc(inp.ppa_baseload_price_eur_per_mwh, inp.ppa_baseload_price_escalation)
    price_13k = esc(inp.section13k_price_eur_per_mwh, inp.section13k_price_escalation)
    price_s7 = (float(h["s7_cost_eur"].sum()) / s7 * k.KWH_PER_MWH) if (inp.section7_enabled and s7 > 0) else 0.0
    if inp.spot_price_source == "Marktpreise":
        price_spot = (float(h["spot_cost_eur"].sum()) / spot * k.KWH_PER_MWH) if (inp.spot_enabled and spot > 0) else 0.0
    else:
        price_spot = esc(inp.spot_own_price_eur_per_mwh, inp.spot_price_escalation)

    # --- mittlerer Bezugspreis und Nebenkosten
    def share(x):
        return x / procurement if procurement else 0.0
    avg_price = (share(pv) * price_pv + share(wind) * price_wind + share(base) * price_base +
                 share(s13k) * price_13k + share(s7) * price_s7 + share(spot) * price_spot)

    def levies(side: str) -> float:
        total = 0.0
        for name in LEVIES:
            if not getattr(inp, f"levy_{side}_{name}_exempt"):
                total += getattr(inp, f"levy_{side}_{name}_ct_per_kwh") * k.KWH_PER_MWH / k.CT_PER_EUR
        return total

    ely_mwh, rest_mwh = ely / k.KWH_PER_MWH, rest / k.KWH_PER_MWH
    demand_ely = 0.0 if inp.demand_charge_ely_exempt or ely_mwh == 0 else (
        inp.demand_charge_ely_eur_per_kw_month * 12 * p.ely_kw / ely_mwh)
    demand_rest = 0.0 if inp.demand_charge_rest_exempt or rest_mwh == 0 else (
        inp.demand_charge_rest_eur_per_kw_month * 12 * (p.total_kw - p.ely_kw) / rest_mwh)
    levies_ely = levies("ely") + demand_ely
    levies_rest = levies("rest") + demand_rest

    # Aufteilung je Komponente (Befreiung = Differenz aus voller und tatsächlicher Abgabe)
    levy_full, levy_actual, levy_priv = {}, {}, {}
    for name in LEVIES:
        full = actual = 0.0
        for side, mwh in (("ely", ely_mwh), ("rest", rest_mwh)):
            rate = getattr(inp, f"levy_{side}_{name}_ct_per_kwh") * k.KWH_PER_MWH / k.CT_PER_EUR
            full += rate * mwh
            if not getattr(inp, f"levy_{side}_{name}_exempt"):
                actual += rate * mwh
        levy_full[name], levy_actual[name], levy_priv[name] = full, actual, full - actual
    demand_cost = demand_ely * ely_mwh + demand_rest * rest_mwh

    # --- Kosten
    m = k.KWH_PER_MWH
    c_pv, c_wind, c_base = pv / m * price_pv, wind / m * price_wind, base / m * price_base
    c_13k, c_s7, c_spot = s13k / m * price_13k, s7 / m * price_s7, spot / m * price_spot
    c_lely, c_lrest = ely_mwh * levies_ely, rest_mwh * levies_rest
    total = c_pv + c_wind + c_base + c_13k + c_s7 + c_spot + c_lely + c_lrest

    if inp.power_subsidy_mode == "Pro kg":
        subsidy = r.h2_kg_per_year * inp.power_subsidy_eur_per_kg
    elif inp.power_subsidy_mode == "Pro MWh Strom":
        subsidy = cons / m * inp.power_subsidy_eur_per_mwh
    else:
        subsidy = 0.0

    # --- Stromverkauf (Überschuss)
    if inp.power_sale_enabled and inp.power_sale_mode == "Spotmarkt" and surplus > 0:
        sale_spot_raw = float(h["surplus_revenue_eur"].sum()) / surplus * m
    else:
        sale_spot_raw = 0.0
    sale_spot = esc(sale_spot_raw, inp.power_sale_ppa_escalation)
    sale_ppa = (esc(inp.power_sale_ppa_price_eur_per_mwh, inp.power_sale_ppa_escalation)
                if inp.power_sale_enabled and inp.power_sale_mode == "PPA" else 0.0)
    surplus_mwh = (procurement - cons) / m  # Blatt 5, R31 (Bezug - Verbrauch)

    return PowerCosts(
        pv, wind, base, s13k, s7, spot, procurement, cons, ely, rest, surplus,
        price_pv, price_wind, price_base, price_13k, price_s7, price_spot,
        levies_ely, levies_rest, avg_price,
        c_pv, c_wind, c_base, c_13k, c_s7, c_spot, c_lely, c_lrest, total, subsidy, total - subsidy,
        sale_spot, sale_ppa, surplus_mwh * sale_spot, surplus_mwh * sale_ppa,
        levy_full, levy_actual, levy_priv, demand_cost, periph, o2, h2c)
