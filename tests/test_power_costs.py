"""Stromkosten gegen die Excel (Blatt 5 V21, Blatt 2 F179 und G59) für alle Testfälle."""
import json
from pathlib import Path

import pytest

from lcoh.inputs import Inputs
from lcoh.operation import run_operation
from lcoh.power_costs import power_costs
from lcoh.zeitreihen import load_default_timeseries

REF = Path(__file__).parent / "reference"
FAELLE = ["basis", "klein", "ohne_batterie", "s13k", "s13k_knapp", "s13k_batt", "v5", "mit_nk"]


def lade(name):
    if name == "basis":
        return Inputs(), json.loads((REF / "excel_zellwerte.json").read_text())
    d = REF / "varianten"
    return (Inputs.from_dict(json.loads((d / f"{name}_eingaben.json").read_text())),
            json.loads((d / f"{name}_zellwerte.json").read_text()))


@pytest.mark.parametrize("name", FAELLE)
def test_stromkosten(name):
    inp, ref = lade(name)
    pc = power_costs(run_operation(inp, load_default_timeseries()))
    assert pc.avg_procurement_price == pytest.approx(ref["B5!H4"], rel=1e-9, abs=1e-9)
    assert pc.cost_total_before_subsidy == pytest.approx(ref["B5!V21"], rel=1e-9, abs=1e-6)
    assert pc.power_subsidy == pytest.approx(ref["B2!F179"], rel=1e-9, abs=1e-6)
    assert pc.cost_total == pytest.approx(ref["B2!G59"], rel=1e-9, abs=1e-6)
    assert pc.sale_revenue_spot == pytest.approx(ref["B5!V31"], rel=1e-9, abs=1e-6)
    assert pc.sale_revenue_ppa == pytest.approx(ref["B5!V32"], rel=1e-9, abs=1e-6)


@pytest.mark.parametrize("name", FAELLE)
def test_privilegierungen(name):
    """Wert der Befreiungen (Blatt 5, AE38:AE53 und AE54) und Stromkosten ohne Privilegien (AE21)."""
    inp, ref = lade(name)
    pc = power_costs(run_operation(inp, load_default_timeseries()))
    assert sum(pc.levy_privilege_eur.values()) == pytest.approx(ref["B5!AE54"], rel=1e-9, abs=1e-6)
    zeilen = {"grid_fee": (38, 47), "electricity_tax": (39, 48), "concession_fee": (40, 49),
              "kwk_levy": (41, 50), "stromnev19_levy": (42, 51), "offshore_levy": (43, 52)}
    for komp, (z1, z2) in zeilen.items():
        assert pc.levy_privilege_eur[komp] == pytest.approx(ref[f"B5!AE{z1}"] + ref[f"B5!AE{z2}"], rel=1e-9, abs=1e-6)
