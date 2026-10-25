"""Tests der Oberfläche (Streamlit AppTest)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def leere_app() -> AppTest:
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=120)
    at.run()
    assert not at.exception
    return at


def neue_app() -> AppTest:
    """App mit geladenen Standardwerten."""
    at = leere_app()
    [b for b in at.button if b.label == "Standardwerte laden"][0].click().run()
    assert not at.exception
    return at


def test_start_ohne_werte():
    at = leere_app()
    assert at.text_input(key="w_electrolyzer_power_kw").value == ""
    assert not [m for m in at.metric if m.label == "Gestehungskosten"]
    assert any("fehlen noch" in i.value for i in at.info)


def test_leeren_nach_standardwerten():
    at = neue_app()
    [b for b in at.button if b.label == "Alle Felder leeren"][0].click().run()
    assert at.text_input(key="w_electrolyzer_power_kw").value == ""
    assert any("fehlen noch" in i.value for i in at.info)


def test_einzelnes_feld_leeren_blendet_ergebnis_aus():
    at = neue_app()
    at.text_input(key="w_electrolyzer_power_kw").set_value("").run()
    assert not [m for m in at.metric if m.label == "Gestehungskosten"]


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


def test_befreite_abgabe_ohne_wert_ist_nicht_noetig():
    at = neue_app()
    at.toggle(key="w_levy_ely_grid_fee_exempt").set_value(True).run()
    at.text_input(key="w_levy_ely_grid_fee_ct_per_kwh").set_value("").run()
    assert [m for m in at.metric if m.label == "Gestehungskosten"]
    at.toggle(key="w_levy_ely_grid_fee_exempt").set_value(False).run()
    assert not [m for m in at.metric if m.label == "Gestehungskosten"]


def test_bereichs_button_fuellt_nur_leere_felder():
    at = leere_app()
    at.text_input(key="w_electrolyzer_power_kw").set_value("10.000").run()
    [b for b in at.button if b.key == "fill_cockpit_ely"][0].click().run()
    assert at.text_input(key="w_electrolyzer_power_kw").value == "10.000"
    assert at.text_input(key="w_capex_electrolyzer_eur_per_kw").value == "1.000,00"
