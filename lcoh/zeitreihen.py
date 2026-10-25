"""Standard-Zeitreihen (8760 Stunden) laden und prüfen.

Die mitgelieferte Datei lcoh/data/zeitreihen.csv stammt aus der Excel:
  wind_kwh_per_kw, pv_kwh_per_kw      Erzeugungsprofile je installiertem kW
                                      (Blatt "9. Energiedaten", Spalten P und AC)
  day_ahead_<Jahr>_eur_per_mwh        Börsenstrompreis-Szenarien (Blatt "8. Marktpreise")
  co2_eur_per_t                       CO2-Preis (Blatt "8. Marktpreise", Spalte H)
  section13k_kwh                      Redispatch-Energie nach §13k (Blatt "8. Marktpreise", Spalte Y)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

HOURS_PER_YEAR = 8760
DATA_FILE = Path(__file__).resolve().parent / "data" / "zeitreihen.csv"

COLUMNS = (
    "hour",
    "wind_kwh_per_kw",
    "pv_kwh_per_kw",
    "day_ahead_2024_eur_per_mwh",
    "day_ahead_2030_eur_per_mwh",
    "day_ahead_2035_eur_per_mwh",
    "day_ahead_2040_eur_per_mwh",
    "day_ahead_2045_eur_per_mwh",
    "co2_eur_per_t",
    "section13k_kwh",
)


def load_default_timeseries() -> pd.DataFrame:
    """Lädt die mitgelieferten Standard-Zeitreihen."""
    return pd.read_csv(DATA_FILE)


def check_timeseries(df: pd.DataFrame) -> list[str]:
    """Prüft eine (auch hochgeladene) Zeitreihentabelle. Leere Liste = in Ordnung."""
    problems = []
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        problems.append("Es fehlen Spalten: " + ", ".join(missing))
        return problems
    if len(df) != HOURS_PER_YEAR:
        problems.append(f"Erwartet werden {HOURS_PER_YEAR} Stundenwerte, vorhanden sind {len(df)}.")
    if df[list(COLUMNS)].isna().any().any():
        problems.append("Die Tabelle enthält leere Zellen.")
    return problems


SERIES_LABELS = {
    "wind_kwh_per_kw": "PPA 2: Erzeugungsprofil, Standard Wind [kWh je kW und Stunde]",
    "pv_kwh_per_kw": "PPA 1: Erzeugungsprofil, Standard PV [kWh je kW und Stunde]",
    "day_ahead": "Börsenstrompreise Day-Ahead [€/MWh]",
    "co2_eur_per_t": "CO₂-Preis [€/t]",
    "section13k_kwh": "§13k-Energie [kWh je Stunde]",
}


def parse_series(data: bytes) -> list[float]:
    """Liest eine hochgeladene Zeitreihe (CSV oder Textdatei) mit 8760 Werten.

    Erlaubt sind eine Spalte oder mehrere Spalten (dann wird die letzte Spalte verwendet), die Trennzeichen
    Semikolon, Tabulator oder Komma sowie Dezimalkomma. Eine Überschriftenzeile wird übersprungen.
    Wirft ValueError mit einer verständlichen Meldung, wenn die Datei nicht passt.
    """
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    values: list[float] = []
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        if ";" in line:
            cells = line.split(";")
        elif "\t" in line:
            cells = line.split("\t")
        elif line.count(",") >= 2:
            cells = line.split(",")
        else:
            cells = [line]
        cell = cells[-1].strip().replace(" ", "")
        if cell.count(",") == 1 and "." not in cell:
            cell = cell.replace(",", ".")
        try:
            values.append(float(cell))
        except ValueError:
            if values or number > 1:
                raise ValueError(f"Zeile {number}: „{cells[-1].strip()}“ ist keine Zahl.") from None
    if len(values) != HOURS_PER_YEAR:
        raise ValueError(f"Die Datei enthält {len(values)} Werte, erwartet werden {HOURS_PER_YEAR} Stundenwerte.")
    if any(v != v or v in (float("inf"), float("-inf")) for v in values):
        raise ValueError("Die Datei enthält ungültige Zahlenwerte.")
    return values
