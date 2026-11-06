"""Batterie nach Preissignalen (Optimierung): Bilanz, Grenzen und das erwartete Verhalten an einfachen Beispielen."""
import numpy as np
import pytest

from lcoh.economics import compute_economics
from lcoh.inputs import Inputs
from lcoh.operation import run_operation
from lcoh.tool_defaults import tool_defaults
from lcoh.zeitreihen import build_timeseries

BASIS = {"battery_enabled": True, "battery_optimize": True, "ppa_baseload_enabled": False, "ppa_pv_enabled": True,
         "ppa_wind_enabled": False, "ppa_pv_kw": 20000.0, "section7_enabled": False, "section13k_enabled": False,
         "spot_enabled": False, "power_sale_enabled": True, "power_sale_mode": "Spotmarkt", "battery_input_power_kw": 40000.0,
         "electrolyzer_power_kw": 10000.0, "min_part_load": 0.1}


def _tag(werte_je_stunde):
    """24 Stundenwerte als Reihe für das ganze Jahr (Rate je Viertelstunde, 35.040 Werte)."""
    return np.repeat(np.tile(np.asarray(werte_je_stunde, dtype=float), 365), 4).tolist()


def _lauf(over, series=None, optimize=True):
    inp = Inputs.from_dict({**tool_defaults(), **BASIS, **over, "battery_optimize": optimize})
    r = run_operation(inp, build_timeseries(series or {}, 1), steps_per_hour=1)
    return inp, r


def _bilanz(inp, r):
    h, dt = r.hourly, 1.0
    C5 = r.power.total_kw * dt
    Pb = (r.power.battery_power_kw - r.power.total_kw) * dt
    eta = np.sqrt(inp.battery_efficiency)
    bal = (h.ppa_kwh + h.s7_kwh + h.s13k_kwh + h.spot_kwh + h.battery_discharge_kwh
           - h.consumption_kwh - h.battery_charge_kwh - h.surplus_kwh)
    assert abs(bal).max() < 1e-6
    soc = h.battery_soc_kwh.to_numpy()
    dyn = soc - np.r_[0.0, soc[:-1]] - eta * h.battery_charge_kwh + h.battery_discharge_kwh / eta
    assert abs(dyn).max() < 1e-6
    assert h.battery_charge_kwh.max() <= Pb + 1e-6 and h.battery_discharge_kwh.max() <= Pb + 1e-6
    assert h.consumption_kwh.max() <= C5 + 1e-6 and soc.max() <= r.power.battery_capacity_kwh + 1e-6
    low = (h.consumption_kwh > 0) & (h.consumption_kwh < inp.min_part_load * C5 - 1e-6)
    assert not low.any()


def test_bilanz_und_grenzen_mit_allen_quellen():
    over = {"ppa_baseload_enabled": True, "ppa_wind_enabled": True, "ppa_wind_kw": 20000.0, "section7_enabled": True,
            "section13k_enabled": True, "spot_enabled": True}
    inp, r = _lauf(over)
    _bilanz(inp, r)
    h = r.hourly
    assert (h.battery_charge_kwh <= h.pv_kwh + h.wind_kwh + h.s7_kwh + h.s13k_kwh + 1e-6).all()   # nie aus Grundlast oder Spot
    assert (h.surplus_kwh <= h.ppa_kwh + h.battery_discharge_kwh + 1e-6).all()                     # kein Direktverkauf von Netzstrom


def test_laedt_billig_und_verkauft_teuer():
    """PV liefert gleichmäßig mehr als der Elektrolyseur braucht; Verkaufspreis nachts 20, tagsüber 200 €/MWh."""
    preise = [20.0] * 12 + [200.0] * 12
    over = {"battery_capacity_hours": 2.0, "electrolyzer_power_kw": 4000.0, "ppa_pv_kw": 5000.0, "battery_efficiency": 0.9}
    inp, r = _lauf(over, {"pv_kwh_per_kw": _tag([1.0] * 24), "day_ahead": _tag(preise)})
    _bilanz(inp, r)
    h = r.hourly
    stunde = np.arange(len(h)) % 24
    assert h.battery_charge_kwh[stunde < 12].sum() > 5 * h.battery_charge_kwh[stunde >= 12].sum()
    assert h.battery_discharge_kwh[stunde >= 12].sum() > 5 * h.battery_discharge_kwh[stunde < 12].sum()
    assert h.battery_discharge_kwh.sum() > 0


def test_ohne_preisunterschied_kein_handel_bei_verlusten():
    """Bei konstantem Preis lohnt Laden und Entladen mit Verlusten nicht."""
    over = {"battery_efficiency": 0.8, "ppa_pv_kw": 5000.0, "electrolyzer_power_kw": 4000.0}
    inp, r = _lauf(over, {"pv_kwh_per_kw": _tag([1.0] * 24), "day_ahead": _tag([100.0] * 24)})
    assert r.hourly.battery_charge_kwh.sum() == pytest.approx(0.0, abs=1e-6)


def test_hoeherer_wirkungsgrad_nie_schlechter():
    preise = [20.0] * 12 + [200.0] * 12
    s = {"pv_kwh_per_kw": _tag([1.0] * 24), "day_ahead": _tag(preise)}
    over = {"battery_capacity_hours": 2.0, "electrolyzer_power_kw": 4000.0, "ppa_pv_kw": 5000.0}
    erloes = []
    for eta in (0.7, 0.9, 1.0):
        inp, r = _lauf({**over, "battery_efficiency": eta}, s)
        erloes.append(compute_economics(r).revenue_power_spot)
    assert erloes[0] <= erloes[1] <= erloes[2]


def test_elektrolyseur_hat_vorrang_vor_verkauf():
    """Reicht das PPA für den Elektrolyseur, geht nur der Rest in Batterie oder Verkauf, auch bei hohem Verkaufspreis."""
    over = {"ppa_pv_kw": 12000.0, "electrolyzer_power_kw": 8000.0, "peripherals_share_of_ely": 0.0, "oxygen_enabled": False,
            "h2_processing_mode": "Direkt"}
    inp, r = _lauf(over, {"pv_kwh_per_kw": _tag([1.0] * 24), "day_ahead": _tag([500.0] * 24)})
    h = r.hourly
    assert h.consumption_kwh.min() == pytest.approx(r.power.total_kw)       # in jeder Stunde Volllast
    assert h.surplus_kwh.max() > 0


def test_schalter_aus_aendert_die_alte_rechnung_nicht():
    over = {"ppa_pv_kw": 12000.0}
    _, r0 = _lauf(over, optimize=False)
    inp = Inputs.from_dict({**tool_defaults(), **BASIS, **over, "battery_optimize": False})
    r1 = run_operation(inp, build_timeseries({}, 1), steps_per_hour=1)
    assert r0.h2_kg_per_year == r1.h2_kg_per_year and (r0.hourly.values == r1.hourly.values).all()


def test_netzbezug_fuellt_nur_auf_und_bleibt_unter_batterieleistung():
    """Grundlast 5 MW, PV 10 MW, Wind 30 MW, §7 an: PPA versorgt zuerst, Netz füllt auf, Gesamtbezug <= Eingangsleistung."""
    over = {"ppa_baseload_enabled": True, "ppa_baseload_kw": 5000.0, "ppa_pv_kw": 10000.0, "ppa_wind_enabled": True,
            "ppa_wind_kw": 30000.0, "section7_enabled": True, "electrolyzer_power_kw": 25000.0,
            "battery_input_power_kw": 50000.0}
    inp, r = _lauf(over)
    _bilanz(inp, r)
    h, c5 = r.hourly, r.power.total_kw
    grid = h.s7_kwh + h.s13k_kwh + h.spot_kwh
    assert (h.ppa_kwh + grid <= r.power.battery_power_kw + 1e-6).all()           # Bezug nie über Batterieeingangsleistung
    assert (grid[h.ppa_kwh >= c5 - 1e-6] <= 1e-9).all()                          # PPA allein reicht: kein Netzbezug
    assert (h.surplus_kwh <= (h.ppa_kwh - c5).clip(lower=0) + h.battery_discharge_kwh + 1e-6).all()  # nur Überschuss wird verkauft
