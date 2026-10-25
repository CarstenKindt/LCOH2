import pytest

from lcoh.economics import compute_economics
from lcoh.inputs import Inputs
from lcoh.operation import run_operation
from lcoh.sensitivity import sensitivity
from lcoh.zeitreihen import load_default_timeseries

# Excel Blatt 7, E4:F10 (Schrittweite 30 %): (Wert bei -30 %, Wert bei +30 %)
EXCEL = {
    "THG-Minderungsmenge": (8.280447569854974, 6.199358183628219),
    "Zinsen (FK + EK)": (6.459020422436603, 8.071507727050419),
    "OPEX": (6.847513567144259, 7.632292186338936),
    "Projektlaufzeit": (8.028491035598897, 6.718697254721033),
    "CAPEX": (5.803999247280666, 8.675806506202528),
    "Volllaststunden": (9.635495420320481, 5.795121537579411),
    "Strompreis": (5.522262030046153, 8.957543723437041),
}


def test_sensitivitaet_wie_excel():
    r = run_operation(Inputs(), load_default_timeseries())
    e = compute_economics(r)
    rows = {z.name: z for z in sensitivity(r, e, 0.3)}
    assert set(rows) == set(EXCEL)
    for name, (minus, plus) in EXCEL.items():
        assert rows[name].lcoh_minus == pytest.approx(minus, rel=1e-9)
        assert rows[name].lcoh_plus == pytest.approx(plus, rel=1e-9)
        assert rows[name].base == pytest.approx(e.lcoh_eur_per_kg)


def test_schrittweite_null_ergibt_basiswert():
    r = run_operation(Inputs(), load_default_timeseries())
    e = compute_economics(r)
    for z in sensitivity(r, e, 0.0):
        assert z.lcoh_minus == pytest.approx(e.lcoh_eur_per_kg, rel=1e-3)
