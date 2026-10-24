"""Tests der Oberfläche (Streamlit AppTest)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def neue_app() -> AppTest:
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=120)
    at.run()
    assert not at.exception
    return at


def metrik(at: AppTest, label: str) -> str:
    return [m.value for m in at.metric if m.label == label][0]


def test_standardwerte():
    at = neue_app()
    assert metrik(at, "Gestehungskosten") == "7,24 €/kg"
    assert metrik(at, "in ct/kWh") == "18,38 ct/kWh"
    assert metrik(at, "Stacktausche") == "1"
    assert metrik(at, "Anteil grüner Wasserstoff") == "100,0 %"


def test_thg_aus():
    at = neue_app()
    at.toggle(key="w_thg_enabled").set_value(False).run()
    assert not at.exception
    assert metrik(at, "Gestehungskosten") == "10,71 €/kg"


def test_zahlenformat_deutsch():
    at = neue_app()
    feld = at.text_input(key="w_electrolyzer_power_kw")
    assert feld.value == "25.000"
    feld.set_value("30.000").run()
    assert not at.exception
    assert at.session_state["S"]["electrolyzer_power_kw"] == 30000
    assert at.text_input(key="w_electrolyzer_power_kw").value == "30.000"
    assert at.text_input(key="w_capex_electrolyzer_eur_per_kw").value == "1.000,00"


def test_ungueltige_eingabe_wird_abgelehnt():
    at = neue_app()
    at.text_input(key="w_electrolyzer_power_kw").set_value("abc").run()
    assert at.session_state["S"]["electrolyzer_power_kw"] == 25000
    assert at.text_input(key="w_electrolyzer_power_kw").value == "25.000"


def test_prozent_mit_komma():
    at = neue_app()
    at.text_input(key="w_electrolyzer_efficiency").set_value("65,5").run()
    assert abs(at.session_state["S"]["electrolyzer_efficiency"] - 0.655) < 1e-12
