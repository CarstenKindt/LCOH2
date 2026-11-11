"""Viertelstundenwerte: Einlesen (Stunde, Viertelstunde, gemischt) und Rechnung in Viertelstunden."""
import datetime as dt

import numpy as np
import pytest

from lcoh.economics import compute_economics
from lcoh.inputs import Inputs
from lcoh.operation import run_operation
from lcoh.tool_defaults import tool_defaults
from lcoh.zeitreihen import QUARTERS_PER_YEAR, build_timeseries, load_default_profiles, read_series, to_grid


def _csv(values) -> bytes:
    return "\n".join(str(v) for v in values).encode()


def _gemischt_2025(hourly_value=50.0, quarter_value=60.0, trenner=";", datum_uhrzeit_getrennt=False) -> bytes:
    """Stundenwerte bis 30.09.2025, danach Viertelstundenwerte (so liegen die Day-Ahead-Daten 2025 vor)."""
    rows, t = [], dt.datetime(2025, 1, 1)
    while t < dt.datetime(2026, 1, 1):
        step = dt.timedelta(hours=1) if t < dt.datetime(2025, 10, 1) else dt.timedelta(minutes=15)
        val = hourly_value if t < dt.datetime(2025, 10, 1) else quarter_value
        stamp = f"{t:%d.%m.%Y}{trenner}{t:%H:%M}" if datum_uhrzeit_getrennt else f"{t:%d.%m.%Y %H:%M}"
        rows.append(f"{stamp}{trenner}{val}")
        t += step
    return "\n".join(rows).encode()


def test_stundenreihe_wird_auf_viertelstunden_gelegt():
    p = read_series(_csv(range(8760)), "preis")
    assert p.resolution == "Stunde" and len(p.rate_quarter) == QUARTERS_PER_YEAR
    assert list(p.rate_quarter[:8]) == [0, 0, 0, 0, 1, 1, 1, 1]


def test_viertelstundenreihe_energie_wird_zur_rate():
    p = read_series(_csv([0.25] * QUARTERS_PER_YEAR), "energie")
    assert p.resolution == "Viertelstunde"
    assert p.rate_quarter == pytest.approx(1.0)          # 0,25 kWh/kW je Viertelstunde = 1 kWh/kW je Stunde


def test_viertelstundenreihe_preis_bleibt():
    p = read_series(_csv([77.5] * QUARTERS_PER_YEAR), "preis")
    assert p.rate_quarter == pytest.approx(77.5)


def test_gemischte_reihe_mit_zeitstempel():
    p = read_series(_gemischt_2025(), "preis")
    assert p.resolution == "gemischt" and len(p.rate_quarter) == QUARTERS_PER_YEAR
    assert p.rate_quarter[0] == 50.0 and p.rate_quarter[-1] == 60.0
    e = read_series(_gemischt_2025(50.0, 15.0), "energie")   # 15 kWh je Viertelstunde = 60 kWh je Stunde
    assert e.rate_quarter[0] == 50.0 and e.rate_quarter[-1] == 60.0


def test_datum_und_uhrzeit_in_getrennten_spalten_und_dezimalkomma():
    daten = _gemischt_2025(datum_uhrzeit_getrennt=True).decode().replace(";50.0", ";50,5").replace(";60.0", ";60,5").encode()
    p = read_series(b"Datum;Uhrzeit;Preis\n" + daten, "preis")
    assert p.resolution == "gemischt" and p.rate_quarter[0] == 50.5


def test_schaltjahr_ohne_zeitstempel_entfernt_29_februar():
    werte = np.arange(8784, dtype=float)
    p = read_series(_csv(werte), "preis")
    assert len(p.rate_quarter) == QUARTERS_PER_YEAR and "29. Februar" in p.note
    assert 59 * 24 not in p.rate_quarter                  # Stunden 1416 bis 1439 fehlen
    assert p.rate_quarter[4 * 59 * 24] == 60 * 24         # nach dem 28. Februar folgt der 1. März


def test_falsche_anzahl_gibt_verstaendliche_meldung():
    with pytest.raises(ValueError, match="Zeitstempel"):
        read_series(_csv(range(15384)), "preis")
    with pytest.raises(ValueError, match="Zeile 3"):
        read_series(b"1\n2\nabc\n", "preis")


def test_raster_stunde_und_viertelstunde():
    p = read_series(_gemischt_2025(), "preis")
    assert len(to_grid(p.rate_quarter, 1)) == 8760 and len(to_grid(p.rate_quarter, 4)) == QUARTERS_PER_YEAR
    ts4 = build_timeseries({"day_ahead": p.rate_quarter.tolist()}, 4)
    ts1 = build_timeseries({"day_ahead": p.rate_quarter.tolist()}, 1)
    assert len(ts4) == QUARTERS_PER_YEAR and len(ts1) == 8760
    assert ts4["day_ahead_eur_per_mwh"].iloc[-1] == 60.0 and ts1["day_ahead_eur_per_mwh"].iloc[0] == 50.0


def _rechne(over: dict, steps: int, series: dict | None = None):
    inp = Inputs.from_dict({**tool_defaults(), **over})
    r = run_operation(inp, build_timeseries(series or {}, steps), steps_per_hour=steps)
    return r, compute_economics(r)


def _stundenprofile() -> dict:
    """Hinterlegte Erzeugungsprofile als Stundenmittel (je Stunde konstant), damit beide Raster dieselben Daten sehen."""
    prof = load_default_profiles()
    return {c: np.repeat(to_grid(prof[c].to_numpy(), 1), 4).tolist() for c in ("wind_kwh_per_kw", "pv_kwh_per_kw")}


def test_viertelstundenrechnung_mit_stundendaten_ohne_batterie_identisch():
    r1, e1 = _rechne({}, 1, _stundenprofile())
    r4, e4 = _rechne({}, 4, _stundenprofile())
    assert e4.lcoh_eur_per_kg == pytest.approx(e1.lcoh_eur_per_kg, rel=1e-9)
    assert r4.h2_kg_per_year == pytest.approx(r1.h2_kg_per_year, rel=1e-9)
    assert len(r4.hourly) == QUARTERS_PER_YEAR


def test_viertelstundenrechnung_mit_stundendaten_mit_batterie_nahezu_identisch():
    over = {"battery_enabled": True, "section7_enabled": True, "ppa_pv_enabled": True, "ppa_wind_enabled": True,
            "ppa_pv_kw": 20000, "ppa_wind_kw": 20000, "spot_enabled": True, "section13k_enabled": True,
            "power_sale_enabled": True}
    r1, e1 = _rechne(over, 1)
    r4, e4 = _rechne(over, 4)
    assert e4.lcoh_eur_per_kg == pytest.approx(e1.lcoh_eur_per_kg, rel=2e-3)
    assert r4.section7_hours == pytest.approx(r1.section7_hours, rel=2e-2)


def test_echte_viertelstundenpreise_senken_die_kosten_bei_spotbezug():
    """Schwankt der Preis innerhalb der Stunde, kann der flexible Elektrolyseur die günstigen Viertelstunden nutzen."""
    over = {"spot_enabled": True, "spot_max_price_eur_per_mwh": 100.0}
    preise = np.tile([60.0, 60.0, 140.0, 140.0], QUARTERS_PER_YEAR // 4)      # Stundenmittel 100 €/MWh
    s = {"day_ahead": preise.tolist()}
    r4, e4 = _rechne(over, 4, s)
    r1, e1 = _rechne(over, 1, s)
    # Stundenmittel 100 €/MWh liegt nicht unter dem Maximalpreis: In der Stundenrechnung gibt es keinen Spotbezug.
    assert e1.power.price_spot == 0.0 and e4.power.price_spot == pytest.approx(60.0)
    assert r4.h2_kg_per_year > r1.h2_kg_per_year
    assert e4.lcoh_eur_per_kg < e1.lcoh_eur_per_kg


def test_energiebilanz_geht_auf():
    from lcoh.energy_balance import energy_balance
    from lcoh.power_costs import power_costs
    inp = Inputs.from_dict({**tool_defaults(), "battery_enabled": True, "ppa_baseload_enabled": True, "ppa_baseload_kw": 5000.0,
                            "ppa_pv_kw": 10000.0, "ppa_wind_enabled": True, "ppa_wind_kw": 30000.0, "section7_enabled": True,
                            "waste_heat_enabled": True})
    r = run_operation(inp, build_timeseries({}, 4), steps_per_hour=4)
    b = energy_balance(r, power_costs(r))
    assert abs(sum(q for _, q in b.sources) - b.procurement) < 1e-3 * b.procurement
    assert abs(b.consumption + b.battery_loss + b.surplus - b.procurement) < 1e-6 * b.procurement
    assert abs(b.hydrogen + b.heat_ely - b.ely) < 1e-6 * b.ely
    assert abs(b.heat_used + b.heat_unused - b.heat_ely - b.heat_compressors) < 1e-6 * b.procurement
    assert b.heat_used > 0


def test_jahresrechnung_stimmt_ohne_degradation_mit_dem_hauptergebnis():
    """Ohne Degradation, THG und Förderung ist die Summe der Jahreskosten durch die Summe des Wasserstoffs das Hauptergebnis."""
    from lcoh.yearly import yearly_lcoh
    inp = Inputs.from_dict({**tool_defaults(), "stack_degradation_per_year": 0.0, "thg_enabled": False,
                            "ppa_pv_price_escalation": 0.0, "opex_lump_sum_enabled": False})
    r = run_operation(inp, build_timeseries({}, 4), steps_per_hour=4)
    e = compute_economics(r)
    y = yearly_lcoh(r, e)
    assert len(y.table) == inp.project_lifetime_years
    assert abs(y.lcoh_sum_ratio - e.lcoh_eur_per_kg) < 1e-6 * abs(e.lcoh_eur_per_kg)


def test_jahresrechnung_mit_preissteigerung_stimmt_im_mittel():
    from lcoh.yearly import yearly_lcoh
    inp = Inputs.from_dict({**tool_defaults(), "stack_degradation_per_year": 0.0, "thg_enabled": False,
                            "maintenance_escalation": 0.02, "personnel_escalation": 0.03, "spot_price_escalation": 0.02})
    r = run_operation(inp, build_timeseries({}, 4), steps_per_hour=4)
    e = compute_economics(r)
    y = yearly_lcoh(r, e)
    assert abs(y.lcoh_sum_ratio - e.lcoh_eur_per_kg) < 1e-3 * abs(e.lcoh_eur_per_kg)
    assert y.table["Betrieb (OPEX) [€/a]"].iloc[-1] > y.table["Betrieb (OPEX) [€/a]"].iloc[0]


def test_zeitstempel_und_wert_mit_komma_getrennt():
    """Typischer Export: „date_utc,capacity_factor“ mit „2023-12-31 23:00:00,0.65“ (ein Komma je Zeile, Schaltjahr 2024)."""
    import pandas as pd
    idx = pd.date_range("2023-12-31 23:00", "2024-12-31 22:00", freq="h")
    text = "date_utc,capacity_factor\r\n" + "\r\n".join(f"{t:%Y-%m-%d %H:%M:%S},{0.5:.4f}" for t in idx) + "\r\n"
    p = read_series(text.encode("utf-8"), "energie")
    assert p.resolution == "Stunde" and len(p.rate_quarter) == 35040
    assert abs(p.rate_quarter[0] - 0.5) < 1e-12 and "29. Februar" in p.note
    # Dezimalkomma bleibt Dezimalkomma
    assert read_series(("\n".join(["0,5"] * 8760)).encode(), "preis").rate_quarter[0] == 0.5


def test_fehlende_zeit_bis_eine_stunde_wird_aufgefuellt():
    ts = ["2025-01-01 %02d:%02d" % (m // 60, m % 60) for m in range(0, 24 * 60, 15)]
    # 8759,25 Stunden mit Zeitstempel: drei Viertelstunden fehlen am Jahresende
    stamps = np.arange(np.datetime64("2025-01-01T00:00"), np.datetime64("2026-01-01T00:00") - np.timedelta64(45, "m"),
                       np.timedelta64(15, "m"))
    data = "\n".join(f"{str(t).replace('T', ' ')};{0.1 + (i % 7) / 100:.3f}" for i, t in enumerate(stamps))
    p = read_series(data.encode(), "energie")
    assert len(p.rate_quarter) == QUARTERS_PER_YEAR
    assert (p.rate_quarter[-4:] == p.rate_quarter[-4]).all()     # letzter Wert fortgeschrieben
    assert "fortgeschrieben" in p.note
    # ohne Zeitstempel: 8759 Stundenwerte
    q = read_series("\n".join(["0,5"] * 8759).encode(), "preis")
    assert len(q.rate_quarter) == QUARTERS_PER_YEAR and q.rate_quarter[-1] == 0.5
    # mehr als eine Stunde fehlt: Fehler
    with pytest.raises(ValueError):
        read_series("\n".join(["0,5"] * 8758).encode(), "preis")
    with pytest.raises(ValueError):
        read_series("\n".join(["0,5"] * 35030).encode(), "preis")
