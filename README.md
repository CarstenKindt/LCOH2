# LCOH2 – Rechner für Wasserstoffgestehungskosten

Öffentliches Berechnungstool für die Gestehungskosten von grünem Wasserstoff (LCOH2).
Es bildet das Excel-Modell `Berechnungstool_Modell_Rev_10.xlsx` aus dem Norddeutschen Reallabor nach
und soll Unternehmen, die einen Elektrolyseur planen, eine schnelle Kostenabschätzung ermöglichen.

**Stand:** Etappe 1 von 6 (Fundament). Das Tool rechnet noch nicht, die Eingaben und Standarddaten stehen.

## Etappen

| Etappe | Inhalt | Stand |
|---|---|---|
| 1 | Projektgerüst, Eingaben (151) mit Excel-Standardwerten, Zeitreihen, Excel-Referenzwerte | fertig |
| 2 | Stündlicher Strombezug, Batterie, Auslastung | offen |
| 3 | Stromkosten, Nebenkosten, Privilegierungen, Stacktausch | offen |
| 4 | CAPEX, OPEX, Finanzierung, Förderungen, Einnahmen inkl. THG-Quote → LCOH | offen |
| 5 | Oberfläche: Cockpit-Startseite, Eingabemasken, Ergebnisse, Up- und Download | offen |
| 6 | Sensitivitätsanalyse, Feinschliff, Veröffentlichung | offen |

## Aufbau

```
lcoh/            Rechenkern (ohne Oberfläche)
  input_spec.py  Beschreibung aller Eingaben (automatisch erzeugt)
  inputs.py      Klasse "Inputs" mit allen Eingaben (automatisch erzeugt)
  zeitreihen.py  Laden und Prüfen der 8760-Stunden-Zeitreihen
  data/          Standard-Zeitreihen aus der Excel
tests/           Automatische Tests gegen die Excel
  reference/     Rechenergebnisse der Excel für den Beispielfall
tools/           Hilfsprogramme, die Daten aus der Excel lesen
docs/            Dokumentation, u. a. Zuordnung Excel-Zelle zu Eingabe
```

## Tests starten

```
pip install -r requirements.txt
python -m pytest
```

## Grundsatz

Die Excel ist der Maßstab. Jede Rechengröße wird gegen die entsprechende Excel-Zelle getestet.
