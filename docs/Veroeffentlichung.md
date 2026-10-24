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
