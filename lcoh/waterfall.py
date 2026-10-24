"""Aufschlüsselung der Gestehungskosten für das Wasserfalldiagramm (Excel: Blatt 7, Wasserfall 1).

Alle Werte in EUR pro kg Wasserstoff. Kosten sind positiv, Förderungen, Befreiungen und Erlöse negativ.
Die Summe aller Posten ergibt die Gestehungskosten (LCOH).
"""
from __future__ import annotations

from dataclasses import dataclass

from lcoh import constants as k
from lcoh.economics import Economics
from lcoh.operation import OperationResult

LEVY_LABELS = {"grid_fee": "Netzentgelt", "electricity_tax": "Stromsteuer", "concession_fee": "Konzessionsabgabe",
               "kwk_levy": "KWK-Aufschlag", "stromnev19_levy": "StromNEV-§19-Umlage", "offshore_levy": "Offshore-Netzumlage"}

# Blöcke in der Reihenfolge des Diagramms
BLOCK_CAPEX, BLOCK_OPEX, BLOCK_STACK = "CAPEX", "OPEX", "Stacktausch"
BLOCK_POWER, BLOCK_INTEREST = "Stromkosten", "Zinskosten"
BLOCK_SUBSIDY, BLOCK_REVENUE = "Förderungen & Befreiungen", "Zusatzeinnahmen"


@dataclass(frozen=True)
class Item:
    block: str
    label: str
    eur_per_kg: float


def waterfall_items(r: OperationResult, e: Economics, power_view: str = "quelle",
                    netto: bool = False) -> list[Item]:
    """power_view: "quelle" = nach Bezugsquelle und Abgaben, "verbraucher" = nach Verbrauchern (wie Excel).
    netto: nur Ansicht "verbraucher": befreite Abgaben werden gar nicht erst als Kosten angesetzt."""
    inp, pc, life, h2 = r.inputs, e.power, r.inputs.project_lifetime_years, e.h2_kg_per_year
    d = h2 if h2 else float("nan")
    items: list[Item] = []

    def add(block: str, label: str, eur_per_year: float, sign: float = 1.0) -> None:
        items.append(Item(block, label, sign * eur_per_year / d))

    for name, value in e.capex_items.items():
        add(BLOCK_CAPEX, name, value / life)

    if inp.opex_lump_sum_enabled:
        add(BLOCK_OPEX, "OPEX pauschal", e.opex_total + e.opex_subsidy)
    else:
        add(BLOCK_OPEX, "Wartung & Instandhaltung", e.opex_maintenance)
        add(BLOCK_OPEX, "Personal", e.opex_personnel)
        add(BLOCK_OPEX, "Rückstellungen (ohne Stacktausch)", e.opex_provisions)
        add(BLOCK_OPEX, "Wasser", e.opex_water)
        add(BLOCK_OPEX, "Sonstige OPEX", e.opex_other)

    sc = e.stack
    stack_invest = sc.total_exchange_cost / life
    add(BLOCK_STACK, "Stack-Investition (Rückstellung + Finanzierung)", stack_invest)
    add(BLOCK_STACK, "Zinsen Stacktausch", sc.annual_cost - stack_invest)

    full_levies = sum(pc.levy_full_eur.values())
    if power_view == "verbraucher":
        m = k.KWH_PER_MWH
        ely_mwh, per_mwh = pc.consumption_ely_kwh / m, pc.consumption_periphery_kwh / m
        o2_mwh, h2_mwh = pc.consumption_o2_kwh / m, pc.consumption_h2_kwh / m
        total_mwh = pc.consumption_total_kwh / m
        purchase = pc.cost_pv + pc.cost_wind + pc.cost_baseload + pc.cost_13k + pc.cost_s7 + pc.cost_spot
        proc_mwh = pc.total_procurement_kwh / m
        avg = purchase / proc_mwh if proc_mwh else 0.0
        levy_rate = full_levies / total_mwh if total_mwh else 0.0
        # Befreiungen hängen an den Seiten Elektrolyseur und Rest; je Verbraucher gleicher Satz je Seite
        def cost_of(mwh: float, side: str) -> float:
            side_full = sum(getattr(inp, f"levy_{side}_{n}_ct_per_kwh") for n in pc.levy_full_eur
                            if not (netto and getattr(inp, f"levy_{side}_{n}_exempt"))) * 10.0
            return mwh * (avg + side_full)
        add(BLOCK_POWER, "Strom Elektrolyseur", cost_of(ely_mwh, "ely"))
        add(BLOCK_POWER, "Strom Peripherie", cost_of(per_mwh, "rest"))
        add(BLOCK_POWER, "Strom O2-Verdichter", cost_of(o2_mwh, "rest"))
        add(BLOCK_POWER, "Strom H2-Verdichter", cost_of(h2_mwh, "rest"))
        add(BLOCK_POWER, "Strom für Überschussverkauf", (proc_mwh - total_mwh) * avg)
        if pc.demand_charge_eur:
            add(BLOCK_POWER, "Leistungspreis", pc.demand_charge_eur)
    else:
        add(BLOCK_POWER, "Strombezug PPA PV", pc.cost_pv)
        add(BLOCK_POWER, "Strombezug PPA Wind", pc.cost_wind)
        add(BLOCK_POWER, "Strombezug PPA Grundlast", pc.cost_baseload)
        add(BLOCK_POWER, "Strombezug §7", pc.cost_s7)
        add(BLOCK_POWER, "Strombezug §13k", pc.cost_13k)
        add(BLOCK_POWER, "Strombezug Spotmarkt", pc.cost_spot)
        for name, label in LEVY_LABELS.items():
            add(BLOCK_POWER, label, pc.levy_full_eur[name])
        add(BLOCK_POWER, "Leistungspreis", pc.demand_charge_eur)

    add(BLOCK_INTEREST, "Zinsen Fremd- und Eigenkapital", e.interest_cost)

    add(BLOCK_SUBSIDY, "CAPEX-Förderung", e.capex_subsidy / life, -1)
    add(BLOCK_SUBSIDY, "OPEX-Förderung", e.opex_subsidy, -1)
    add(BLOCK_SUBSIDY, "Strompreisförderung", pc.power_subsidy, -1)
    for name, label in LEVY_LABELS.items():
        if not (netto and power_view == "verbraucher"):
            add(BLOCK_SUBSIDY, f"Befreiung {label}", pc.levy_privilege_eur[name], -1)
    add(BLOCK_SUBSIDY, "Strompreiskompensation", e.spk, -1)

    add(BLOCK_REVENUE, "Abwärme", e.revenue_heat, -1)
    add(BLOCK_REVENUE, "Sauerstoff", e.revenue_oxygen, -1)
    add(BLOCK_REVENUE, "Stromverkauf", e.revenue_power_spot + e.revenue_power_ppa, -1)
    add(BLOCK_REVENUE, "THG-Quote", e.revenue_thg, -1)
    add(BLOCK_REVENUE, "Regelenergie", e.revenue_balancing, -1)
    add(BLOCK_REVENUE, "Sonstige Einnahmen", e.revenue_other, -1)
    return items


def block_subtotal(items: list[Item], *blocks: str) -> float:
    return sum(i.eur_per_kg for i in items if i.block in blocks)


def net_power_items(items: list[Item]) -> list[Item]:
    """Verrechnet die Befreiungen von Stromnebenkosten mit den Stromkosten.

    Quellenansicht: jede Abgabe wird um ihre Befreiung gekürzt. Verbraucheransicht: eine Zeile
    "Befreiung Stromnebenkosten" im Stromkostenblock. Im Block Förderungen bleiben nur echte Förderungen."""
    exempt = {i.label: i.eur_per_kg for i in items if i.block == BLOCK_SUBSIDY and i.label.startswith("Befreiung ")}
    out: list[Item] = []
    power_labels = {i.label for i in items if i.block == BLOCK_POWER}
    for it in items:
        if it.block == BLOCK_SUBSIDY and it.label in exempt:
            continue
        if it.block == BLOCK_POWER and f"Befreiung {it.label}" in exempt:
            out.append(Item(it.block, it.label + " (nach Befreiung)", it.eur_per_kg + exempt[f"Befreiung {it.label}"]))
        else:
            out.append(it)
    if not any(label.replace("Befreiung ", "") in power_labels for label in exempt):
        total = sum(exempt.values())
        idx = max(n for n, i in enumerate(out) if i.block == BLOCK_POWER)
        out.insert(idx + 1, Item(BLOCK_POWER, "Befreiung Stromnebenkosten", total))
    return out
