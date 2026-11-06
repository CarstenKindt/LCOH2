"""Rechenwege mit dem Excel-Verhalten der §7-Preisgrenze (Vergleich mit den Excel-Referenzwerten).

Die Excel vergleicht den Preis einer Stunde mit der Preisgrenze der Folgestunde (Zeilenversatz in der Formel, siehe
lcoh/dispatch.py). Das Tool selbst rechnet ohne diesen Versatz; für den Vergleich mit der Excel wird er hier nachgebildet.
"""
from lcoh.dispatch import simulate_dispatch as _simulate_dispatch
from lcoh.operation import run_operation as _run_operation


def run_operation(*args, **kwargs):
    kwargs.setdefault("excel_shift", True)
    return _run_operation(*args, **kwargs)


def simulate_dispatch(*args, **kwargs):
    kwargs.setdefault("excel_shift", True)
    return _simulate_dispatch(*args, **kwargs)
