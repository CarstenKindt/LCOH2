"""Erzeugt docs/excel_zuordnung.md: welche Eingabe im Tool zu welcher Excel-Zelle gehört."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lcoh.input_spec import GROUPS, SPECS  # noqa: E402
from tools.excel_mapping import NICHT_UEBERNOMMEN  # noqa: E402


def fmt(spec):
    v = spec.default
    if spec.kind == "percent":
        return f"{v * 100:g} %"
    if spec.kind == "bool":
        return "ja" if v else "nein"
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


lines = ["# Zuordnung Excel und Python-Tool", "",
         "Diese Datei wird automatisch erzeugt (`python tools/build_docs.py`). "
         "Alle Standardwerte stammen aus `Berechnungstool_Modell_Rev_10.xlsx`.", ""]
for g in GROUPS:
    lines += [f"## {g}", "", "| Bezeichnung | Schlüssel | Einheit | Standardwert | Excel |", "|---|---|---|---|---|"]
    for s in (x for x in SPECS if x.group == g):
        unit = s.unit + (f" ({s.hint})" if s.hint else "")
        lines.append(f"| {s.label} | `{s.key}` | {unit} | {fmt(s)} | {s.excel} |")
    lines.append("")
lines += ["## Gelbe Excel-Zellen, die bewusst nicht übernommen wurden", "", "| Zelle (Blatt 2) | Grund |", "|---|---|"]
lines += [f"| {c} | {why} |" for c, why in NICHT_UEBERNOMMEN.items()]
(ROOT / "docs" / "excel_zuordnung.md").write_text("\n".join(lines) + "\n", encoding="utf8")
print("docs/excel_zuordnung.md geschrieben")
