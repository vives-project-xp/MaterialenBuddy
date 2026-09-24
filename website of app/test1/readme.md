# Eerste lokale test

## Installatie

Open PowerShell in deze map en voer uit:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Starten

```powershell
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

Open daarna http://127.0.0.1:8000 in de browser. De standaardmodus is `mock`: na een klik wordt na twee seconden de status `aangekomen` getoond.

## Wat is er gebouwd?

Deze testapp bestaat uit een FastAPI-server, een eenvoudige webpagina en `waypoints.json` met de locaties. De webpagina haalt de locaties op en stuurt bij een klik een navigatieopdracht naar de server. De server geeft de status `onderweg`, `aangekomen`, `geannuleerd` of `fout` terug.

Er zijn twee modi: `mock` om de software veilig te testen zonder robot, en `bluetooth` om de Create 3 echt te laten rijden met de officiële `irobot-edu-sdk`. Een nieuwe opdracht annuleert een vorige opdracht en vastgelopen navigatie krijgt een timeout.

Met `reset_origin.py` kan de huidige plek van de robot eenmalig als nieuw nulpunt `(0, 0)` worden ingesteld. De waypoints worden als absolute coördinaten in centimeters opgeslagen.

De robotconfiguratie staat standaard op `10.10.234.52`. Controleer eerst de netwerkverbinding:

```powershell
Test-Connection 10.10.234.52 -Count 1
Test-NetConnection 10.10.234.52 -Port 80
```

De standaardmodus is `mock`. Voor echte Bluetooth-navigatie start je de server met:

```powershell
$env:CREATE3_MODE = "bluetooth"
python -m uvicorn server:app --host 127.0.0.1 --port 8001 --reload
```

Daarna sturen de knoppen op http://127.0.0.1:8001 de Create 3 echt naar de gekozen waypoint. De server gebruikt een timeout van 60 seconden per opdracht.

## Eerste fysieke Bluetooth-test

Zet de Create 3 vrij op de vloer en zorg dat er minstens 1 meter ruimte rondom de robot is. Zet Bluetooth op de laptop aan en voer daarna uit:

```powershell
python bluetooth_test.py
```

## Nieuw nulpunt instellen

Zet de robot op de gewenste huidige startplek en voer dit eenmalig uit. De robot rijdt niet; zijn huidige plek wordt `(0, 0)`.

```powershell
python reset_origin.py
```

De robot rijdt 10 cm vooruit en daarna terug naar het startpunt. Je kunt eventueel de Bluetooth-naam meegeven:

```powershell
$env:CREATE3_BLUETOOTH_NAME = "Create 3"
python bluetooth_test.py
```