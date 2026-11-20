# Veröffentlichung des Rechners

Das Tool besteht nur aus Dateien dieses Ordners. Es ist an keinen Anbieter gebunden.

## Variante A: Streamlit Community Cloud (kostenlos, ohne eigenen Server)

1. Auf https://share.streamlit.io mit dem GitHub-Konto anmelden.
2. „Create app“ wählen, dann „Deploy a public app from GitHub“.
3. Repository `CarstenKindt/LCOH2`, Branch `main`, Hauptdatei `app.py` eintragen.
4. Unter „Advanced settings“ Python 3.12 wählen und auf „Deploy“ klicken.
5. Nach einigen Minuten ist der Rechner unter einer Adresse der Form `https://<name>.streamlit.app` erreichbar.
   Änderungen am GitHub-Ordner (Branch `main`) werden automatisch übernommen.

Hinweis: Das Repository muss öffentlich sein. Der Dienst schläft nach einigen Tagen ohne Aufrufe ein
und startet beim nächsten Aufruf neu.

## Variante B: Hochschulserver

Die IT braucht dafür Folgendes:

**Mit Docker (empfohlen):**

```
git clone https://github.com/CarstenKindt/LCOH2.git
cd LCOH2
docker build -t lcoh-rechner .
docker run -d --restart unless-stopped -p 8501:8501 --name lcoh-rechner lcoh-rechner
```

Davor wird ein Webserver mit HTTPS gesetzt (zum Beispiel Nginx oder Apache als Reverse Proxy auf Port 8501).
Dabei müssen WebSocket-Verbindungen weitergeleitet werden (`Upgrade`-Header), sonst lädt die Seite nicht.

**Ohne Docker:**

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py --server.port 8501
```

Für den Dauerbetrieb den Befehl als Systemdienst (systemd) einrichten.

Ressourcen: etwa 1 GB Arbeitsspeicher; eine Berechnung dauert 1 bis 2 Sekunden.

## Fragen an die Hochschul-IT

- Dürfen dauerhaft laufende Python-/Docker-Dienste betrieben werden?
- Unter welcher Adresse soll der Rechner erreichbar sein (zum Beispiel unter hs-flensburg.de)?
- Wer betreut den Server und spielt Updates ein?

## Berechnungsmethode der Gestehungskosten

Das Tool berechnet die Gestehungskosten nach der **Kapitalwertmethode**:

LCOH₂ = (I₀ + Σ (Kosten_t + Stack − Erlöse_t)/(1+i)^t) / Σ H₂-Menge_t/(1+i)^t

Die Investition I₀ (nach Förderung) fällt in Jahr 0 an, alle übrigen Zahlungen am Ende des jeweiligen Projektjahres t. Kosten, Erlöse und Wasserstoffmenge werden für jedes Jahr einzeln berechnet (Preissteigerungen, Degradation, THG-Erlöse des jeweiligen Kalenderjahres). Der Zinssatz i ist der Kapitalkostensatz (WACC) ohne Steuern: i = FK-Anteil · FK-Zins + EK-Anteil · EK-Rendite. Die Abzinsung der Wasserstoffmenge ist eine Folge der finanzmathematischen Umformung: Die Menge steht stellvertretend für die Erlöse aus ihrem Verkauf.

Der Stacktausch geht als gleichbleibender Jahresbetrag ein: Bis zur Laufzeitmitte wird eine Rücklage gebildet, der Rest wird mit einem Kredit zum Stackzins finanziert; Tauschkosten und Kreditzinsen werden gleichmäßig auf die Laufzeit verteilt.

Gerechnet wird nominal: Zinssätze und Preissteigerungen enthalten die Inflation. Die Preissteigerungen sind je Kosten- und Erlösart getrennt einstellbar; eine Rate von 0 % bedeutet real sinkende Werte.

Die Jahresansicht zeigt die nominalen Gestehungskosten je Projektjahr (Kapitaldienst als Annuität zum Kapitalkostensatz) und das Gesamtergebnis als gestrichelte Linie. Die Sensitivitätsanalyse rechnet ebenfalls nach der Kapitalwertmethode; Zinsen und Projektlaufzeit werden dabei vollständig neu berechnet.

Das Excel-Modell verwendet eine vereinfachte Annuitätenmethode (Annuität nur auf die Investition, Kosten und Erlöse als nicht abgezinster Mittelwert). Sie ist im Rechenkern weiterhin enthalten und dient dem Abgleich mit der Excel, wird im Tool aber nicht mehr angezeigt.

## Weitere ökonomische Kennzahlen (Reiter „Ergebnisse“)

Der Reiter „Ergebnisse“ ist in „Allgemeine Ergebnisse“ und „Weitere ökonomische Kennzahlen“ gegliedert. Im zweiten Bereich wird ein Wasserstoffpreis vorgegeben, entweder als Marge auf die Gestehungskosten oder als Zielverkaufspreis, optional mit jährlicher Preissteigerung. Die allgemeinen Ergebnisse bleiben davon unberührt.

Grundlage sind dieselben Jahreswerte wie bei den Gestehungskosten (nominal, ohne Steuern). Der Wasserstofferlös wird in den Anteil zu Gestehungskosten und die Marge aufgeteilt. Im Projekt-Cashflow steht der Stacktausch im Jahr, in dem er stattfindet; in der Eigenkapitalsicht wird er wie bei den Gestehungskosten über eine Rücklage (erste Laufzeithälfte) und einen Kredit zum Stackzins (zweite Hälfte) finanziert. CFADS = operativer Cashflow abzüglich Rücklage für den Stacktausch. Weil die Gestehungskosten den Stacktausch einschließlich Kreditzinsen gleichmäßig verteilen, ist der Projekt-Kapitalwert bei 0 % Marge leicht positiv.

- **Projektsicht:** Investition in Jahr 0, danach CFADS. Kapitalwert mit dem Kapitalkostensatz (WACC), interner Zinsfuß (Projektrendite), statische und dynamische Amortisation.
- **Eigenkapitalsicht:** Fremdkapital als Annuitätendarlehen zum Fremdkapitalzins über die Projektlaufzeit. Eigenkapital-Cashflow = CFADS − Kapitaldienst Fremdkapital; Eigenkapitalrendite (IRR) und Kapitalwert mit der geforderten Eigenkapitalrendite.
- **Fremdkapitalsicht:** Schuldendienstdeckungsgrad DSCR = CFADS / Kapitaldienst aus Fremdkapital und Stackkredit (je Jahr, Minimum und Mittelwert).

Ohne Stacktausch ist bei einem Preis in Höhe der Gestehungskosten der Kapitalwert null und die Projektrendite gleich dem Kapitalkostensatz. Wechselt der Eigenkapital-Cashflow mehrfach das Vorzeichen, ist der interne Zinsfuß nur eingeschränkt aussagekräftig; das Tool weist darauf hin. Nicht berücksichtigt: Steuern und Abschreibungen, Restwert am Laufzeitende, Umlaufvermögen, abweichende Kreditlaufzeiten.

Die Sensitivitätsanalyse arbeitet mit einer festen Schrittweite von 25 %.

Die Zusammensetzung der Gestehungskosten lässt sich für den Durchschnitt über die Projektlaufzeit (Standard) oder für jedes einzelne Projektjahr anzeigen.
