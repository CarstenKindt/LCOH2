"""Viertelstundenwerte: Einlesen (Stunde, Viertelstunde, gemischt) und Rechnung in Viertelstunden."""
import datetime as dt

import numpy as np
import pytest

from lcoh.economics import compute_economics
from lcoh.inputs import Inputs
from lcoh.operation import run_operation
from lcoh.tool_defaults import tool_defaults
from lcoh.zeitreihen import QUARTERS_PER_YEAR, build_timeseries, read_series, to_grid


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
    assert ts4["day_ahead_2024_eur_per_mwh"].iloc[-1] == 60.0 and ts1["day_ahead_2045_eur_per_mwh"].iloc[0] == 50.0


def _rechne(over: dict, steps: int, series: dict | None = None):
    inp = Inputs.from_dict({**tool_defaults(), **over})
    r = run_operation(inp, build_timeseries(series or {}, steps), steps_per_hour=steps)
    return r, compute_economics(r)


def test_viertelstundenrechnung_mit_stundendaten_ohne_batterie_identisch():
    r1, e1 = _rechne({}, 1)
    r4, e4 = _rechne({}, 4)
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
