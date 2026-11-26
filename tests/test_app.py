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
    assert not kpis(at, "Gestehungskosten")
    assert any("fehlen noch" in i.value for i in at.info)


def test_leeren_nach_standardwerten():
    at = neue_app()
    [b for b in at.button if b.label == "Alle Felder leeren"][0].click().run()
    assert at.text_input(key="w_electrolyzer_power_kw").value == ""
    assert any("fehlen noch" in i.value for i in at.info)


def test_einzelnes_feld_leeren_blendet_ergebnis_aus():
    at = neue_app()
    at.text_input(key="w_electrolyzer_power_kw").set_value("").run()
    assert not kpis(at, "Gestehungskosten")


def kpis(at: AppTest, label: str) -> list[str]:
    import re
    out = []
    for md in at.markdown:
        for m in re.finditer(r'data-kpi="([^"]*)" data-v="([^"]*)"', md.value):
            if m.group(1) == label:
                out.append(m.group(2))
    return out


def metrik(at: AppTest, label: str, unit: str | None = None) -> str:
    werte = kpis(at, label)
    if unit:
        werte = [w for w in werte if w.endswith(unit)]
    return werte[0]


def test_standardwerte():
    at = neue_app()
    # Kapitalwertmethode, Standardwerte = Szenario S1 der Veröffentlichung (⅔ Wind, ⅓ PV, nur Wasserstoff)
    assert metrik(at, "Gestehungskosten", "€/kg") == "9,48 €/kg"
    assert metrik(at, "Gestehungskosten", "ct/kWh") == "24,06 ct/kWh"
    assert metrik(at, "Stacktausche") == "1"
    assert metrik(at, "Anteil RFNBO-konformer Wasserstoff") == "100,0 %"


def test_thg_an():
    at = neue_app()
    at.toggle(key="w_thg_enabled").set_value(True).run()
    assert not at.exception
    assert metrik(at, "Gestehungskosten", "€/kg") == "5,23 €/kg"


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
    assert kpis(at, "Gestehungskosten")
    at.toggle(key="w_levy_ely_grid_fee_exempt").set_value(False).run()
    assert not kpis(at, "Gestehungskosten")


def test_bereichs_button_fuellt_nur_leere_felder():
    at = leere_app()
    at.text_input(key="w_electrolyzer_power_kw").set_value("10.000").run()
    [b for b in at.button if b.key == "fill_cockpit_ely"][0].click().run()
    assert at.text_input(key="w_electrolyzer_power_kw").value == "10.000"
    assert at.text_input(key="w_capex_electrolyzer_eur_per_kw").value == "1.000,00"


def test_batterie_anschlussleistung_zu_klein():
    at = neue_app()
    at.toggle(key="w_battery_enabled").set_value(True).run()
    assert not at.error
    at.text_input(key="w_battery_input_power_kw").set_value("20.000").run()
    assert not at.exception
    assert any("Anschlussleistung gesamt" in e.value for e in at.error)
    assert not kpis(at, "Gestehungskosten")
    at.text_input(key="w_battery_input_power_kw").set_value("35.000").run()
    assert not at.error
    assert kpis(at, "Gestehungskosten")


def test_berechnung_laeuft_in_viertelstunden():
    at = neue_app()
    assert kpis(at, "Gestehungskosten")
    assert not any("geht damit über die Excel hinaus" in c.value for c in at.caption)   # Hinweis entfällt
    assert not [r for r in at.radio if r.key == "res_mode"]


def test_batterie_optimierung_im_cockpit():
    at = neue_app()
    at.toggle(key="w_battery_enabled").set_value(True).run()
    assert not at.exception
    assert at.text_input(key="w_battery_efficiency").value                        # Wirkungsgrad gilt für beide Betriebsweisen
    at.toggle(key="w_battery_optimize").set_value(True).run()
    assert not at.exception, at.exception
    assert at.text_input(key="w_battery_efficiency").value
    assert kpis(at, "Gestehungskosten")


def test_impressum_und_datenschutz_oeffnen():
    at = neue_app()
    at.button(key="open_impressum").click().run()
    assert not at.exception
    at.button(key="open_datenschutz").click().run()
    assert not at.exception


def test_kapitalwertmethode_im_cockpit():
    at = neue_app()
    assert not at.exception
    assert not [x for x in at.radio if x.label == "Berechnungsmethode der Gestehungskosten"]
    assert any("Berechnungen nominal mit Kapitalwertmethode" in m.value for m in at.markdown)
    assert any("keine Steuern verrechnet" in m.value for m in at.markdown)
    assert not any("Annuitätenmethode" in c.value for c in at.caption)


def test_oekonomische_kennzahlen_ausgeblendet():
    """Der Bereich ist im Code vorhanden, aber bis zur Veröffentlichung ausgeblendet."""
    at = neue_app()
    assert not at.exception
    assert not any("Kapitalwert (NPV)" in m.value for m in at.markdown)
    assert "Weitere ökonomische Kennzahlen" not in [t.label for t in at.tabs]
    assert not [x for x in at.radio if x.label.startswith("Vorgabe des Wasserstoffpreises")]


def test_oekonomische_kennzahlen_eingeblendet(tmp_path):
    """Mit SHOW_FINANCE = True erscheint der Bereich und rechnet fehlerfrei (Kopie der App im selben Ordner)."""
    root = Path(__file__).resolve().parent.parent
    src = (root / "app.py").read_text(encoding="utf-8").replace("SHOW_FINANCE = False", "SHOW_FINANCE = True", 1)
    kopie = root / "_app_mit_kennzahlen_test.py"
    kopie.write_text(src, encoding="utf-8")
    try:
        at = AppTest.from_file(str(kopie), default_timeout=120)
        at.run()
        [b for b in at.button if b.label == "Standardwerte laden"][0].click().run()
        assert not at.exception
        assert "Weitere ökonomische Kennzahlen" in [t.label for t in at.tabs]
        assert any("Kapitalwert (NPV)" in m.value for m in at.markdown)
        r = [x for x in at.radio if x.label.startswith("Vorgabe des Wasserstoffpreises")][0]
        r.set_value("Zielverkaufspreis").run()
        assert not at.exception
    finally:
        kopie.unlink()
