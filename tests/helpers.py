"""Rechenwege mit dem Excel-Verhalten der §7-Preisgrenze (Vergleich mit den Excel-Referenzwerten).

Die Excel vergleicht den Preis einer Stunde mit der Preisgrenze der Folgestunde (Zeilenversatz in der Formel, siehe
lcoh/dispatch.py). Das Tool selbst rechnet ohne diesen Versatz; für den Vergleich mit der Excel wird er hier nachgebildet.
"""
from dataclasses import replace

from lcoh.dispatch import simulate_dispatch as _simulate_dispatch
from lcoh.operation import run_operation as _run_operation


def _wie_excel(inp):
    """Die Excel kennt keine Batterieverluste: Wirkungsgrad 100 % (im Tool ist 90 % voreingestellt)."""
    return replace(inp, battery_efficiency=1.0)


def run_operation(inp, *args, **kwargs):
    kwargs.setdefault("excel_shift", True)
    return _run_operation(_wie_excel(inp), *args, **kwargs)


def simulate_dispatch(inp, *args, **kwargs):
    kwargs.setdefault("excel_shift", True)
    return _simulate_dispatch(_wie_excel(inp), *args, **kwargs)
