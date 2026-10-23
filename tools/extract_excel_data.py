"""Liest Zeitreihen und Referenzwerte aus der Excel.

Aufruf:  python tools/extract_excel_data.py  PFAD/ZUR/EXCEL.xlsx

Erzeugt:
  lcoh/data/zeitreihen.csv                 Standard-Zeitreihen (8760 Stunden)
  tests/reference/excel_zellwerte.json     Rechenergebnisse der Excel für den Beispielfall
  tests/reference/excel_stunden.csv.gz     Stundenwerte des Blatts "4. Bezüge und Verbräuche"
"""
from __future__ import annotations

import gzip
import json
import sys
import warnings
from pathlib import Path

import openpyxl
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
HOURS = 8760


def column(ws, col: str, first_row: int, n: int = HOURS) -> list:
    return [ws[f"{col}{first_row + i}"].value for i in range(n)]


def main(path: str) -> None:
    wb = openpyxl.load_workbook(path, data_only=True)

    # ---- Zeitreihen (Standort 1 = Wind, Standort 2 = PV: "Eigene Eingaben", Spalten P und AC)
    ws9, ws8 = wb["9. Energiedaten"], wb["8. Marktpreise"]
    data = {
        "hour": list(range(1, HOURS + 1)),
        "wind_kwh_per_kw": column(ws9, "P", 6),
        "pv_kwh_per_kw": column(ws9, "AC", 6),
    }
    for year, col in ((2024, "B"), (2030, "C"), (2035, "D"), (2040, "E"), (2045, "F")):
        data[f"day_ahead_{year}_eur_per_mwh"] = column(ws8, col, 7)
    data["co2_eur_per_t"] = column(ws8, "H", 7)
    data["section13k_kwh"] = column(ws8, "Y", 7)
    df = pd.DataFrame(data)
    assert not df.isna().any().any(), "Lücken in den Zeitreihen"
    df.to_csv(ROOT / "lcoh" / "data" / "zeitreihen.csv", index=False)
    print("Zeitreihen:", df.shape)

    # ---- Zellwerte der Rechenblätter (nur Zahlen/Wahrheitswerte/Text, ohne die 8760-Zeilen-Tabelle)
    ref = {}
    for name, short in (("2. Ein- und Ausgaben", "B2"), ("3. Nebenrechnungen", "B3"),
                        ("5. Strompreis", "B5"), ("6. Stacktausch", "B6")):
        ws = wb[name]
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, (int, float, bool)):
                    ref[f"{short}!{c.coordinate}"] = c.value
    ws4 = wb["4. Bezüge und Verbräuche"]
    for row in ws4.iter_rows(min_row=1, max_row=13):
        for c in row:
            if isinstance(c.value, (int, float, bool)):
                ref[f"B4!{c.coordinate}"] = c.value
    (ROOT / "tests" / "reference" / "excel_zellwerte.json").write_text(
        json.dumps(ref, ensure_ascii=False, indent=0), encoding="utf8")
    print("Referenzzellen:", len(ref))

    # ---- Stundenwerte aus Blatt 4 (Zeilen 14 bis 8773)
    from openpyxl.utils import get_column_letter, column_index_from_string as ci
    cols = [get_column_letter(i) for i in range(ci("C"), ci("AO") + 1)]
    names = {c: " ".join(str(ws4[f"{c}11"].value).split()) for c in cols}
    rows = {c: column(ws4, c, 14) for c in cols}
    hourly = pd.DataFrame(rows)
    # Spalten AK, AL, AO sind in der Excel sortierte Kopien; sie werden nicht benötigt
    hourly = hourly.drop(columns=["AK", "AL", "AO"])
    hourly.to_csv(ROOT / "tests" / "reference" / "excel_stunden.csv.gz", index=False, compression="gzip")
    (ROOT / "tests" / "reference" / "excel_stunden_spalten.json").write_text(
        json.dumps({c: names[c] for c in hourly.columns}, ensure_ascii=False, indent=1), encoding="utf8")
    print("Stundenwerte:", hourly.shape)


if __name__ == "__main__":
    main(sys.argv[1])
