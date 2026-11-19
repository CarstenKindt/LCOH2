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

## Berechnungsmethode der Gestehungskosten (Schalter im Cockpit)

Das Cockpit bietet zwei Methoden; der jeweils andere Wert wird zum Vergleich angezeigt.

- **Annuitätenmethode** (Voreinstellung, wie im Excel-Modell): Die Investition wird mit den Zinsen für Fremd- und Eigenkapital in gleich hohe Jahresbeträge umgerechnet; Betriebskosten und Erlöse gehen als nicht abgezinster Mittelwert über die Laufzeit ein.
- **Kapitalwertmethode** (wie Fraunhofer ISE, Studie „Stromgestehungskosten Erneuerbare Energien“, Juli 2024): LCOH₂ = (I₀ + Σ (Kosten_t − Erlöse_t)/(1+i)^t + Σ Stacktausch_k/(1+i)^(k·Intervall)) / Σ H₂-Menge_t/(1+i)^t. Die Investition fällt in Jahr 0 an, alle übrigen Zahlungen am Ende des jeweiligen Projektjahres. Der Zinssatz i ist der Kapitalkostensatz (WACC) ohne Steuern: i = FK-Anteil · FK-Zins + EK-Anteil · EK-Zins. Gerechnet wird nominal (Preissteigerungen und Zinsen einschließlich Inflation).

Die Abzinsung der Wasserstoffmenge ist eine Folge der finanzmathematischen Umformung: Die Menge steht stellvertretend für die Erlöse aus ihrem Verkauf. Zeitlich ungleich verteilte Erlöse (insbesondere THG-Quote) werden bei der Kapitalwertmethode stärker gewichtet, wenn sie früh anfallen; deshalb weichen beide Methoden deutlich voneinander ab. Haben Fremd- und Eigenkapital denselben Zins und sind alle Jahre gleich, liefern beide Methoden dasselbe Ergebnis.

Die Jahresansicht zeigt die nominalen Gestehungskosten je Projektjahr (Kapitaldienst als gleichbleibende Annuität der gewählten Methode) sowie die Ergebnisse beider Methoden als gestrichelte Linien. Die Sensitivitätsanalyse rechnet mit der Annuitätenmethode. Der Unternehmenssteuersatz des Excel-Modells (Blatt 2, C164) wird nicht übernommen.
