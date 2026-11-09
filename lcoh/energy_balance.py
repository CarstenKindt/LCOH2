"""Energiebilanz des Jahres: Strombezug, Verbrauch, Verluste, Wärme und Wasserstoff (Grundlage für Tabelle und Sankey-Diagramm)."""
from __future__ import annotations

from dataclasses import dataclass

from lcoh.operation import OperationResult
from lcoh.power_costs import PowerCosts


@dataclass(frozen=True)
class EnergyBalance:
    """Alle Mengen in kWh pro Jahr."""
    sources: list[tuple[str, float]]       # Bezugsquellen
    procurement: float                     # Gesamtbezug
    ely: float                             # Stromverbrauch Elektrolyseur
    peripherals: float
    h2_compressor: float
    o2_compressor: float
    battery_loss: float                    # Verluste der Batterie (geladen minus entladen)
    surplus: float                         # verkaufter Überschussstrom
    hydrogen: float                        # chemische Energie des Wasserstoffs (Brennwert)
    heat_ely: float                        # Abwärme Elektrolyseur
    heat_compressors: float                # Abwärme Verdichter
    heat_used: float                       # genutzte Wärme
    heat_unused: float                     # ungenutzte Wärme
    compression_rest: float                # Verdichterstrom, der nicht als Wärme anfällt

    @property
    def consumption(self) -> float:
        return self.ely + self.peripherals + self.h2_compressor + self.o2_compressor


def energy_balance(r: OperationResult, pc: PowerCosts) -> EnergyBalance:
    inp, p = r.inputs, r.power
    cons = pc.consumption_total_kwh
    ely = cons * p.ely_share
    periph = cons * p.peripherals_share
    h2c = cons * p.h2_compressor_share
    o2c = cons * p.o2_compressor_share
    battery_loss = max(pc.total_procurement_kwh - cons - pc.surplus_kwh, 0.0)

    hydrogen = r.h2_energy_kwh
    heat_ely = max(ely - hydrogen, 0.0)
    heat_comp = h2c * (1 - inp.h2_compressor_efficiency) + o2c * (1 - inp.o2_compressor_efficiency)
    comp_rest = h2c + o2c - heat_comp
    heat_total = heat_ely + heat_comp
    used = heat_total * inp.heat_usable_share if inp.waste_heat_enabled else 0.0
    sources = [("PPA 1", pc.ppa_pv_kwh), ("PPA 2", pc.ppa_wind_kwh), ("PPA Grundlast", pc.baseload_kwh),
               ("§7 (37. BImSchV)", pc.section7_kwh), ("§13k EnWG", pc.section13k_kwh), ("Spotmarkt", pc.spot_kwh)]
    return EnergyBalance(sources, pc.total_procurement_kwh, ely, periph, h2c, o2c, battery_loss, pc.surplus_kwh,
                         hydrogen, heat_ely, heat_comp, used, heat_total - used, comp_rest)
