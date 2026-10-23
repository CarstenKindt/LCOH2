"""Feste Rechengrößen. Sie stammen aus dem Blatt "3. Nebenrechnungen" der Excel (nicht gelb, also keine Eingaben)."""

HHV_KWH_PER_KG_H2 = 39.4          # Brennwert Wasserstoff, kWh je kg (Nebenrechnungen C6)
KWH_PER_NM3_H2 = 3.5              # kWh je Nm³ (C7)
WATER_KG_PER_KG_H2 = 9.0          # Stöchiometrisch (C10)
WATER_REAL_FACTOR = 1.5           # Faktor realer Wasserverbrauch (C11)
O2_KG_PER_KG_H2 = 8.0             # (C12)
H2_DENSITY_KG_PER_NM3 = 0.08988   # (C13)
KWH_PER_MWH = 1000.0              # (C14)
LITER_PER_M3 = 1000.0             # (C15)
KG_PER_TONNE = 1000.0             # (C16)
CT_PER_EUR = 100.0                # (C18)
J_PER_KWH = 3_600_000.0           # (C19)
HOURS_PER_YEAR = 8760

# Verdichter (Nebenrechnungen G18/G19 und G38/G39)
H2_ISENTROPIC_EXPONENT = 1.41
H2_GAS_CONSTANT = 4124.0          # J/(kg*K)
O2_ISENTROPIC_EXPONENT = 1.4
O2_GAS_CONSTANT = 259.8           # J/(kg*K)

# §7 37. BImSchV (Blatt 8): Faktor auf den CO2-Preis und Untergrenze der Preisgrenze
SECTION7_CO2_FACTOR = 0.36
SECTION7_MIN_LIMIT_EUR_PER_MWH = 20.0

# In der Excel verweist die Batterie-Ladebedingung auf eine leere Zelle ('5. Strompreis'!V4), der Wert ist 0.
BATTERY_CHARGE_PRICE_LIMIT_EUR_PER_MWH = 0.0
