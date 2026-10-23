"""Erzeugt lcoh/input_spec.py und lcoh/inputs.py aus der Excel-Datei.

Aufruf:  python tools/build_input_spec.py  PFAD/ZUR/EXCEL.xlsx

Die Excel ist der Maßstab: Standardwerte, Einheiten und Auswahllisten werden
direkt aus ihr gelesen. Die Zuordnung der Zellen zu Schlüsseln steht in
tools/excel_mapping.py.
"""
from __future__ import annotations

import pickle
import re
import sys
import warnings
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from excel_mapping import BLATT2, NEBENKOSTEN, NICHT_UEBERNOMMEN  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
GELB = "FFFFFF00"

# Auswahllisten (aus den Datenprüfungen der Excel, Blatt 2)
CHOICES = {
    "C5": [2025, 2026, 2027, 2028, 2029, 2030],
    "C41": ["direkt", "Verdichtung"],
    "C80": ["Marktpreise", "Eigene Preise"],
    "C86": ["Jahresdaten", "Eigener Preis"],
    "C169": ["Ohne", "Prozentual", "Absolut"],
    "C174": ["Ohne", "Pro kg", "Pro Volllaststunde"],
    "C179": ["Ohne", "Pro kg", "Pro MWh Strom"],
    "C189": ["Ohne", "Rechner", "Separat"],
    "C203": [0.4, 1.0],
    "C208": ["Spotmarkt", "PPA"],
}
NEGATIV_ERLAUBT = {"h2_inlet_temperature_c", "o2_inlet_temperature_c", "stack_cost_degression"}


def clean(text) -> str:
    return re.sub(r"\s+", " ", str(text)).strip() if text is not None else ""


def kind_of(value, fmt: str, cell: str) -> str:
    if isinstance(value, bool):
        return "bool"
    if cell in CHOICES:
        return "choice"
    if isinstance(value, str):
        return "choice"
    if "%" in fmt:
        return "percent"
    return "number"


def main(excel_path: str) -> None:
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws2, ws5 = wb["2. Ein- und Ausgaben"], wb["5. Strompreis"]

    # Abdeckung prüfen: jede gelbe Zelle ist entweder übernommen oder bewusst ausgenommen
    gelb2 = [c.coordinate for r in ws2.iter_rows() for c in r
             if c.value is not None and c.fill.fill_type == "solid" and c.fill.fgColor.rgb == GELB]
    offen = [c for c in gelb2 if c not in BLATT2 and c not in NICHT_UEBERNOMMEN]
    assert not offen, f"Gelbe Zellen ohne Zuordnung: {offen}"

    specs = []

    def add(key, group, label, unit, hint, kind, default, choices, excel):
        minimum = maximum = None
        if kind == "number" and key not in NEGATIV_ERLAUBT:
            minimum = 0.0
        if kind == "percent":
            if "escalation" in key or "degression" in key:
                minimum, maximum = -0.5, 0.5
            else:
                minimum, maximum = 0.0, 1.0
        specs.append(dict(key=key, group=group, label=label, unit=unit, hint=hint, kind=kind,
                          default=default, choices=choices, minimum=minimum, maximum=maximum, excel=excel))

    for cell, (key, group, label) in BLATT2.items():
        c = ws2[cell]
        row = c.row
        label_text = label or clean(ws2.cell(row, 2).value)
        unit_cell = ws2.cell(row, c.column + 1).value if cell.startswith("C") else None
        unit_text = clean(unit_cell)
        if unit_text in ("Bitte auswählen", "None"):
            unit_text = ""
        kind = kind_of(c.value, c.number_format, cell)
        unit, hint = unit_text, ""
        if kind == "percent":
            unit = "%"
            hint = unit_text
        if kind in ("bool", "choice"):
            unit = ""
        unit = unit.replace("KW", "kW")
        default = c.value
        if kind == "percent":
            default = float(default)
        if kind == "number" and float(default).is_integer():
            default = int(default) if key in ("project_lifetime_years",) else float(default)
        add(key, group, label_text, unit, hint, kind, default, CHOICES.get(cell), f"Blatt 2, {cell}")

    # Stromnebenkosten aus Blatt 5
    for row, (k, name) in NEBENKOSTEN.items():
        for suffix, area, vcol, ecol in (("ely", "Elektrolyseur", "H", "J"), ("rest", "übrige Verbraucher", "M", "O")):
            add(f"levy_{suffix}_{k}_ct_per_kwh", "Stromnebenkosten", f"{name} {area}", "ct/kWh", "", "number",
                float(ws5[f"{vcol}{row}"].value), None, f"Blatt 5, {vcol}{row}")
            add(f"levy_{suffix}_{k}_exempt", "Stromnebenkosten", f"{name} {area}: befreit?", "", "", "bool",
                bool(ws5[f"{ecol}{row}"].value), None, f"Blatt 5, {ecol}{row}")
    add("demand_charge_ely_exempt", "Stromnebenkosten", "Leistungspreis Elektrolyseur: befreit?", "", "", "bool",
        bool(ws5["J17"].value), None, "Blatt 5, J17")
    add("demand_charge_rest_exempt", "Stromnebenkosten", "Leistungspreis übrige Verbraucher: befreit?", "", "", "bool",
        bool(ws5["O17"].value), None, "Blatt 5, O17")

    # Börsenpreis-Szenario (Blatt 8)
    ws8 = wb["8. Marktpreise"]
    add("day_ahead_scenario_year", "Strombezug: Spotmarkt", "Börsenpreis-Szenario (Jahr)", "", "", "choice",
        int(ws8["G6"].value), [2024, 2030, 2035, 2040, 2045], "Blatt 8, G6")

    # ---- input_spec.py schreiben
    lines = ['"""AUTOMATISCH ERZEUGT von tools/build_input_spec.py - nicht von Hand ändern.',
             "",
             "Alle Eingaben des Tools mit Standardwerten aus der Excel (Stand: Berechnungstool_Modell_Rev_10).",
             'Prozentwerte werden als Anteil gespeichert (0,2 = 20 %).',
             '"""',
             "from __future__ import annotations",
             "",
             "from dataclasses import dataclass",
             "",
             "",
             "@dataclass(frozen=True)",
             "class InputSpec:",
             "    key: str",
             "    group: str",
             "    label: str",
             "    unit: str",
             "    hint: str",
             "    kind: str  # number | percent | bool | choice",
             "    default: object",
             "    choices: tuple | None",
             "    minimum: float | None",
             "    maximum: float | None",
             "    excel: str",
             "",
             "",
             "SPECS: tuple[InputSpec, ...] = ("]
    for s in specs:
        ch = repr(tuple(s["choices"])) if s["choices"] else "None"
        lines.append(
            f"    InputSpec({s['key']!r}, {s['group']!r}, {s['label']!r}, {s['unit']!r}, {s['hint']!r}, "
            f"{s['kind']!r}, {s['default']!r}, {ch}, {s['minimum']!r}, {s['maximum']!r}, {s['excel']!r}),")
    lines += [")", "", "SPEC_BY_KEY = {s.key: s for s in SPECS}", "GROUPS = tuple(dict.fromkeys(s.group for s in SPECS))", ""]
    (ROOT / "lcoh" / "input_spec.py").write_text("\n".join(lines), encoding="utf8")

    # ---- inputs.py schreiben
    out = ['"""AUTOMATISCH ERZEUGT von tools/build_input_spec.py - nicht von Hand ändern.',
           "",
           "Die Klasse Inputs enthält alle Eingaben des Tools. Ohne Angaben gelten die Standardwerte der Excel.",
           '"""',
           "from __future__ import annotations",
           "",
           "from dataclasses import dataclass, asdict, fields",
           "",
           "from lcoh.input_spec import SPEC_BY_KEY, SPECS",
           "",
           "",
           "@dataclass",
           "class Inputs:"]
    group = None
    for s in specs:
        if s["group"] != group:
            group = s["group"]
            out.append(f"    # ---- {group}")
        typ = {"bool": "bool", "choice": type(s["default"]).__name__, "percent": "float", "number": "float"}[s["kind"]]
        if s["kind"] == "number" and isinstance(s["default"], int):
            typ = "int"
        unit = f" [{s['unit']}]" if s["unit"] else ""
        out.append(f"    {s['key']}: {typ} = {s['default']!r}  # {s['excel']}{unit}")
    out += [
        "",
        "    def to_dict(self) -> dict:",
        "        return asdict(self)",
        "",
        "    @classmethod",
        "    def from_dict(cls, data: dict) -> \"Inputs\":",
        "        \"\"\"Fehlende Schlüssel erhalten den Excel-Standardwert, unbekannte werden ignoriert.\"\"\"",
        "        values = {}",
        "        for f in fields(cls):",
        "            if f.name in data:",
        "                values[f.name] = _coerce(SPEC_BY_KEY[f.name], data[f.name])",
        "        return cls(**values)",
        "",
        "    def validate(self) -> list[str]:",
        "        \"\"\"Gibt eine Liste verständlicher Fehlermeldungen zurück (leer = alles in Ordnung).\"\"\"",
        "        problems = []",
        "        for s in SPECS:",
        "            value = getattr(self, s.key)",
        "            if s.choices is not None and value not in s.choices:",
        "                problems.append(f\"{s.label}: Wert {value!r} ist nicht erlaubt (erlaubt: {', '.join(map(str, s.choices))}).\")",
        "            elif s.kind in (\"number\", \"percent\"):",
        "                if s.minimum is not None and value < s.minimum:",
        "                    problems.append(f\"{s.label}: Wert {value} ist kleiner als {s.minimum}.\")",
        "                if s.maximum is not None and value > s.maximum:",
        "                    problems.append(f\"{s.label}: Wert {value} ist größer als {s.maximum}.\")",
        "        return problems",
        "",
        "",
        "def _coerce(spec, value):",
        "    if spec.kind == \"bool\":",
        "        if isinstance(value, str):",
        "            return value.strip().lower() in (\"1\", \"true\", \"ja\", \"wahr\")",
        "        return bool(value)",
        "    if spec.kind == \"choice\":",
        "        return type(spec.default)(value)",
        "    if isinstance(spec.default, int) and not isinstance(spec.default, bool):",
        "        return int(value)",
        "    return float(value)",
        "",
    ]
    (ROOT / "lcoh" / "inputs.py").write_text("\n".join(out), encoding="utf8")
    print(f"{len(specs)} Eingaben geschrieben ({len(gelb2)} gelbe Zellen in Blatt 2, davon {len(NICHT_UEBERNOMMEN)} bewusst ausgenommen).")


if __name__ == "__main__":
    main(sys.argv[1])
