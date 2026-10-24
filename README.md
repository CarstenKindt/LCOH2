# LCOH2 – Rechner für Wasserstoffgestehungskosten

Öffentliches Berechnungstool für die Gestehungskosten von grünem Wasserstoff (LCOH2).
Es bildet das Excel-Modell `Berechnungstool_Modell_Rev_10.xlsx` aus dem Norddeutschen Reallabor nach
und soll Unternehmen, die einen Elektrolyseur planen, eine schnelle Kostenabschätzung ermöglichen.

**Stand:** Die Berechnung und die Oberfläche sind fertig und gegen die Excel getestet. Offen sind Feinschliff
und die Veröffentlichung (siehe `docs/Veroeffentlichung.md`).

## Etappen

| Etappe | Inhalt | Stand |
|---|---|---|
| 1 | Projektgerüst, Eingaben (151) mit Excel-Standardwerten, Zeitreihen, Excel-Referenzwerte | fertig |
| 2 | Stündlicher Strombezug, Batterie, Auslastung | fertig |
| 3 | Stromkosten, Nebenkosten, Privilegierungen, Stacktausch | fertig |
| 4 | CAPEX, OPEX, Finanzierung, Förderungen, Einnahmen inkl. THG-Quote → LCOH | fertig |
| 5 | Oberfläche: Cockpit, Eingabemasken, Ergebnisse, Up- und Download | fertig |
| 6 | Sensitivitätsanalyse, Feinschliff, Veröffentlichung | in Arbeit |

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
pip install -r requirements-dev.txt
python -m pytest
```

## Grundsatz

Die Excel ist der Maßstab. Jede Rechengröße wird gegen die entsprechende Excel-Zelle getestet.


## Vorabversion starten

```
pip install -r requirements.txt
streamlit run app.py
```

Der Browser öffnet sich automatisch (sonst http://localhost:8501). Tests: `python -m pytest`.
