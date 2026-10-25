"""Prüft, dass die Eingaben des Tools mit den gelben Feldern der Excel übereinstimmen."""
import json
from pathlib import Path

import pytest

from lcoh.input_spec import SPECS
from lcoh.inputs import Inputs

REF = json.loads((Path(__file__).parent / "reference" / "excel_zellwerte.json").read_text(encoding="utf8"))
SHEET_PREFIX = {"Blatt 2": "B2", "Blatt 5": "B5"}


def test_defaults_are_valid():
    assert Inputs().validate() == []


def test_number_of_inputs():
    # 124 Eingaben aus Blatt 2 + 26 Stromnebenkosten aus Blatt 5 + 1 Marktpreis-Szenario aus Blatt 8 + 2 getrennte PPA-Schalter
    assert len(SPECS) == 153  # + je ein Schalter für PV- und Wind-PPA (Excel: ein gemeinsamer Schalter)


@pytest.mark.parametrize("spec", [s for s in SPECS if s.excel.startswith(("Blatt 2", "Blatt 5"))], ids=lambda s: s.key)
def test_default_matches_excel_value(spec):
    sheet, cell = spec.excel.split(", ")
    key = f"{SHEET_PREFIX[sheet]}!{cell}"
    if key not in REF:  # Textfelder (Auswahllisten) stehen nicht in den Zahlenreferenzen
        pytest.skip("Textfeld")
    assert getattr(Inputs(), spec.key) == pytest.approx(REF[key], rel=1e-12)


def test_roundtrip_and_defaults_for_missing_keys():
    original = Inputs(electrolyzer_power_kw=1234.0, thg_enabled=False)
    again = Inputs.from_dict(original.to_dict())
    assert again == original
    partial = Inputs.from_dict({"electrolyzer_power_kw": 5000, "unbekannter_schluessel": 1})
    assert partial.electrolyzer_power_kw == 5000.0
    assert partial.project_lifetime_years == 20


def test_validation_finds_problems():
    problems = Inputs(commissioning_year=2040, debt_share=1.5, electrolyzer_power_kw=-1.0).validate()
    assert len(problems) == 3
