"""Standard-Zeitreihen (8760 Stunden) laden und prüfen.

Die mitgelieferte Datei lcoh/data/zeitreihen.csv stammt aus der Excel:
  wind_kwh_per_kw, pv_kwh_per_kw      Erzeugungsprofile je installiertem kW
                                      (Blatt "9. Energiedaten", Spalten P und AC)
  day_ahead_<Jahr>_eur_per_mwh        Börsenstrompreis-Szenarien (Blatt "8. Marktpreise")
  co2_eur_per_t                       CO₂-Preis (Blatt "8. Marktpreise", Spalte H)
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
    "wind_kwh_per_kw": "PPA 2: Erzeugungsprofil [kWh je kW]",
    "pv_kwh_per_kw": "PPA 1: Erzeugungsprofil [kWh je kW]",
    "day_ahead": "Börsenstrompreise Day-Ahead [€/MWh]",
    "co2_eur_per_t": "CO₂-Preis [€/t]",
    "section13k_kwh": "§13k-Energie [kWh]",
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


# ---------------------------------------------------------------------------------------------
# Eigene Zeitreihen in Stunden-, Viertelstunden- oder gemischter Auflösung
#
# Intern werden alle Reihen als „Raten“ je Stunde geführt (kWh je kW und Stunde, kWh je Stunde, €/MWh).
# Eine Stundenreihe (Energie je Stunde) und dieselbe Reihe als Viertelstundenreihe (Energie je Viertelstunde)
# ergeben dann dieselbe Rate. Für die Viertelstundenrechnung wird jede Rate auf 35.040 Viertelstunden gelegt,
# für die Stundenrechnung über je vier Viertelstunden gemittelt.
# ---------------------------------------------------------------------------------------------
import re
from dataclasses import dataclass

import numpy as np

QUARTERS_PER_YEAR = 4 * HOURS_PER_YEAR          # 35.040
_FEB29_HOURS = slice(59 * 24, 60 * 24)          # Index der Stunden des 29. Februar in einem Schaltjahr

#: Art der Reihe: "energie" = Energie je Zeitintervall (wird in eine Rate je Stunde umgerechnet),
#: "preis" = Preis (bleibt unverändert)
SERIES_KIND = {"wind_kwh_per_kw": "energie", "pv_kwh_per_kw": "energie", "section13k_kwh": "energie",
               "day_ahead": "preis", "co2_eur_per_t": "preis"}

_DATE = r"(?:\d{1,2}\.\d{1,2}\.\d{4}|\d{4}-\d{2}-\d{2})"
_TIME = r"\d{1,2}:\d{2}(?::\d{2})?"
_RE_DATETIME = re.compile(rf"^({_DATE})[ T]({_TIME})")
_RE_DATE = re.compile(rf"^({_DATE})$")
_RE_TIME = re.compile(rf"^({_TIME})$")


@dataclass(frozen=True)
class ParsedSeries:
    """Eine eingelesene Reihe als Rate je Viertelstunde (35.040 Werte) und ihre ursprüngliche Auflösung."""
    rate_quarter: np.ndarray
    resolution: str            # "Stunde", "Viertelstunde" oder "gemischt"
    note: str = ""             # Hinweis an den Nutzer (z. B. 29. Februar entfernt)


def _to_datetime(first: str, second: str | None) -> np.datetime64 | None:
    """Liest einen Zeitstempel aus einer Zelle („01.10.2025 00:15“, „2025-10-01T00:15“) oder aus Datum und Uhrzeit in zwei Zellen."""
    first = first.strip()
    m = _RE_DATETIME.match(first)
    if m:
        d, t = m.group(1), m.group(2)
    elif _RE_DATE.match(first) and second is not None and _RE_TIME.match(second.strip()):
        d, t = first, second.strip()
    else:
        return None
    if "." in d:
        day, month, year = d.split(".")
        d = f"{year}-{int(month):02d}-{int(day):02d}"
    hh, mm = t.split(":")[:2]
    return np.datetime64(f"{d}T{int(hh):02d}:{int(mm):02d}")


def _split_cells(line: str) -> list[str]:
    if ";" in line:
        return line.split(";")
    if "\t" in line:
        return line.split("\t")
    if line.count(",") >= 2:
        return line.split(",")
    return [line]


def read_series(data: bytes, kind: str) -> ParsedSeries:
    """Liest eine hochgeladene Reihe (Stunden, Viertelstunden oder beides gemischt).

    Ohne Zeitstempel: genau 8.760 (Stunden) oder 35.040 (Viertelstunden) Werte; bei Schaltjahren 8.784 bzw. 35.136
    (der 29. Februar wird entfernt). Mit Zeitstempel in den ersten ein oder zwei Spalten (Datum und Uhrzeit): auch gemischte
    Auflösung; die Dauer jedes Wertes ergibt sich aus dem Abstand zum nächsten Zeitstempel. Der Wert steht in der letzten Spalte.
    Energiereihen gelten je Zeitintervall (kWh je kW und Viertelstunde bei Viertelstundenwerten), Preise unverändert.
    Wirft ValueError mit verständlicher Meldung.
    """
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    values: list[float] = []
    stamps: list[np.datetime64 | None] = []
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        cells = _split_cells(line)
        cell = cells[-1].strip().replace(" ", "")
        if cell.count(",") == 1 and "." not in cell:
            cell = cell.replace(",", ".")
        try:
            value = float(cell)
        except ValueError:
            if values or number > 1:
                raise ValueError(f"Zeile {number}: „{cells[-1].strip()}“ ist keine Zahl.") from None
            continue
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(f"Zeile {number}: ungültiger Zahlenwert.")
        values.append(value)
        stamps.append(_to_datetime(cells[0], cells[1] if len(cells) > 2 else None) if len(cells) > 1 else None)
    n = len(values)
    if n == 0:
        raise ValueError("Die Datei enthält keine Zahlen.")
    has_stamps = all(s is not None for s in stamps)
    if any(s is not None for s in stamps) and not has_stamps:
        raise ValueError("Der Zeitstempel fehlt oder ist nicht lesbar (erwartet: „TT.MM.JJJJ hh:mm“ oder „JJJJ-MM-TT hh:mm“).")
    vals = np.array(values, dtype=float)
    note = ""

    if has_stamps:
        ts = np.array(stamps, dtype="datetime64[m]")
        diffs = np.diff(ts).astype(int)                    # Minuten bis zum nächsten Zeitstempel
        dur = np.empty(n, dtype=int)
        prev = int(diffs[0]) if n > 1 else 60
        for i in range(n):
            d = int(diffs[i]) if i < n - 1 else prev
            if d <= 0 or d > prev:                         # Zeitumstellung (doppelte oder fehlende Stunde): Dauer der Vorzeile
                d = prev
            dur[i] = d
            prev = d
        if any(d not in (15, 30, 60) for d in dur):
            bad = sorted({int(d) for d in dur if d not in (15, 30, 60)})
            raise ValueError(f"Die Zeitstempel haben unzulässige Abstände ({', '.join(str(b) + ' min' for b in bad)}). "
                             "Erlaubt sind 15, 30 oder 60 Minuten.")
        months_days = ts.astype("datetime64[D]")
        is_feb29 = np.array([(str(x)[5:10] == "02-29") for x in months_days])
        if is_feb29.any():
            vals, dur = vals[~is_feb29], dur[~is_feb29]
            note = "Der 29. Februar wurde entfernt."
    else:
        if n in (HOURS_PER_YEAR, HOURS_PER_YEAR + 24):
            dur = np.full(n, 60)
            if n != HOURS_PER_YEAR:
                keep = np.ones(n, dtype=bool); keep[_FEB29_HOURS] = False
                vals, dur, note = vals[keep], dur[keep], "Schaltjahr: Der 29. Februar wurde entfernt."
        elif n in (QUARTERS_PER_YEAR, QUARTERS_PER_YEAR + 96):
            dur = np.full(n, 15)
            if n != QUARTERS_PER_YEAR:
                keep = np.ones(n, dtype=bool); keep[4 * _FEB29_HOURS.start:4 * _FEB29_HOURS.stop] = False
                vals, dur, note = vals[keep], dur[keep], "Schaltjahr: Der 29. Februar wurde entfernt."
        else:
            raise ValueError(
                f"Die Datei enthält {n} Werte. Erwartet werden {HOURS_PER_YEAR:,} Stundenwerte oder {QUARTERS_PER_YEAR:,} "
                "Viertelstundenwerte (jeweils ein Jahr). Bei gemischter Auflösung (z. B. 2025) bitte eine Spalte mit dem "
                "Zeitstempel ergänzen.".replace(",", "."))

    quarters = dur // 15
    total = int(quarters.sum())
    if total != QUARTERS_PER_YEAR:
        raise ValueError(f"Die Werte decken {total / 4:,.2f} Stunden ab, erwartet werden {HOURS_PER_YEAR:,} (ein Jahr ohne "
                         "29. Februar).".replace(",", "#").replace(".", ",").replace("#", "."))
    rate = vals / (dur / 60.0) if kind == "energie" else vals
    rate_q = np.repeat(rate, quarters)
    if (quarters == 4).all():
        res = "Stunde"
    elif (quarters == 1).all():
        res = "Viertelstunde"
    else:
        res = "gemischt"
    return ParsedSeries(rate_q, res, note)



def to_grid(rate_quarter: np.ndarray, steps_per_hour: int) -> np.ndarray:
    """Rate je Viertelstunde auf das Rechenraster: Viertelstunde unverändert, Stunde als Mittel aus vier Viertelstunden."""
    arr = np.asarray(rate_quarter, dtype=float)
    return arr if steps_per_hour == 4 else arr.reshape(HOURS_PER_YEAR, 4).mean(axis=1)


def build_timeseries(series: dict, steps_per_hour: int = 1) -> pd.DataFrame:
    """Standard-Zeitreihen, ersetzt durch eigene Reihen (Rate je Viertelstunde, siehe read_series), im gewünschten Raster.

    Stundenraster: 8.760 Zeilen, Viertelstundenraster: 35.040 Zeilen. Hinterlegte Stundenreihen werden dafür auf vier
    Viertelstunden gelegt (Zero-Order-Hold, Raten und Preise bleiben gleich).
    """
    ts = load_default_timeseries().copy()
    if steps_per_hour == 4:
        ts = pd.DataFrame({c: np.repeat(ts[c].to_numpy(), 4) for c in ts.columns if c != "hour"})
    for name, values in series.items():
        grid = to_grid(np.asarray(values, dtype=float), steps_per_hour)
        if name == "day_ahead":
            for col in [c for c in ts.columns if c.startswith("day_ahead_")]:
                ts[col] = grid
        else:
            ts[name] = grid
    return ts
