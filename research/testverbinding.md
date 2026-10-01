# Test voor het verbinden en besturen van de Create 3 via bluethooth
dit is een handleiding van een test om te proberen de **iRobot Create 3** te bestuen met bluethooth
Het doel van deze test is eenvoudig:

**Je drukt op Run in VS Code → de robot rijdt 3 seconden vooruit → de robot stopt.**

Voor deze test heb je geen ROS 2, WSL of Wi-Fi nodig.

---

## 1. Wat heb je nodig?

Voor deze test heb je nodig:

* Een Windows-pc
* Visual Studio Code
* Een iRobot Create 3
* Bluetooth op de pc
* Internetverbinding tijdens de installatie
* Python 3.11

De Create 3 wordt uiteindelijk rechtstreeks vanuit Python via Bluetooth bestuurd.

De verbinding ziet er zo uit:

**VS Code → Python → Bluetooth → Create 3**

---

## 2. Python 3.11 installeren

Voor deze test gebruiken we Python 3.11.

Open **PowerShell** en typ:

```powershell
py -3.11 --version
```

Als Python 3.11 geïnstalleerd is, krijg je bijvoorbeeld:

```text
Python 3.11.9
```

Als je een foutmelding krijgt dat Python 3.11 niet gevonden wordt, moet Python 3.11 eerst geïnstalleerd worden.

> Let op: als er al een andere Python-versie op de computer staat, hoef je die niet te verwijderen. Verschillende Python-versies kunnen naast elkaar bestaan.

---

## 3. Een projectmap maken

Maak bijvoorbeeld op het bureaublad een nieuwe map:

```text
Create3
```

Open deze map vervolgens in **Visual Studio Code**.

---

## 4. Een virtual environment maken

Open in VS Code:

**Terminal → New Terminal**

Typ:

```powershell
py -3.11 -m venv .venv
```

Hierdoor wordt in de projectmap een aparte Python-omgeving gemaakt.

Je krijgt nu bijvoorbeeld:

```text
Create3
├── .venv
```

Deze `.venv` zorgt ervoor dat de programma's en pakketten voor dit project apart blijven van andere Python-projecten.

---

## 5. De virtual environment activeren

Typ in dezelfde terminal:

```powershell
.venv\Scripts\Activate.ps1
```

Als dit gelukt is, begint de terminal met:

```text
(.venv)
```

---

## 6. De iRobot Python SDK installeren

De Python SDK is de software waarmee Python met de Create 3 kan communiceren.

Installeer deze met:

```powershell
pip install irobot-edu-sdk
```

Wacht tot de installatie volledig klaar is.

---

## 7. Een Python-bestand maken

Maak in VS Code een nieuw bestand met de naam:

```text
besturing.py
```

Zet daarin:

```python
from irobot_edu_sdk.backend.bluetooth import Bluetooth
from irobot_edu_sdk.robots import event, Root

robot = Root(Bluetooth())

@event(robot.when_play)
async def play(robot):
    await robot.set_wheel_speeds(20, 20)
    await robot.wait(3)
    await robot.set_wheel_speeds(0, 0)

robot.play()
```

### Wat doet deze code?

Deze regel maakt een Bluetooth-verbinding:

```python
robot = Root(Bluetooth())
```

Daarna wordt de functie gestart wanneer het programma begint:

```python
@event(robot.when_play)
```

Deze regel laat beide wielen met snelheid 20 draaien:

```python
await robot.set_wheel_speeds(20, 20)
```

Omdat beide wielen dezelfde snelheid hebben, rijdt de robot vooruit.

Daarna wacht Python 3 seconden:

```python
await robot.wait(3)
```

En uiteindelijk worden beide wielen gestopt:

```python
await robot.set_wheel_speeds(0, 0)
```

---

## 8. De Create 3 klaarmaken

Zet de Create 3 aan.

Zorg ervoor dat:

* de robot ingeschakeld is;
* Bluetooth beschikbaar is;
* niemand anders met de robot verbonden is;
* er voldoende vrije ruimte vóór de robot is.

Zet de robot bijvoorbeeld op de vloer met enkele meters vrije ruimte ervoor.

Je hoeft voor deze test **niet** verbonden te zijn met het Wi-Fi-netwerk van de robot.

Je hoeft de robot ook niet eerst handmatig toe te voegen via de gewone Windows Bluetooth-instellingen. De iRobot Python SDK zoekt de robot zelf via Bluetooth.

---

## 9. Het programma uitvoeren

Je kunt het programma rechtstreeks vanuit VS Code starten.

Open `besturing.py` en klik rechtsboven op:

**▶ Run Python File**

Je kunt het ook vanuit de terminal starten:

```powershell
python besturing.py
```

In de terminal verschijnt bijvoorbeeld:

```text
Run event loop.
Connecting to iRobot-XXXXXXXX
```

Als de verbinding gelukt is, wordt de code uitgevoerd.

De robot zal dan:

**3 seconden vooruit rijden → stoppen.**

---

## 10. Als het werkt

Als alles goed gaat, heb je nu een werkende verbinding:

```text
Visual Studio Code
        ↓
    Python 3.11
        ↓
 iRobot Python SDK
        ↓
     Bluetooth
        ↓
     Create 3
```

Vanaf hier kun je de code verder uitbreiden, bijvoorbeeld om:

* de robot achteruit te laten rijden;
* links en rechts te laten draaien;
* de robot met toetsen te besturen;
* sensoren uit te lezen;
* een bepaalde route te laten rijden;
* de robot onderdeel te maken van een groter programma.

---

## 11. Veelvoorkomende problemen

### Er staat `(.venv)` niet in de terminal

Activeer de omgeving opnieuw:

```powershell
.venv\Scripts\Activate.ps1
```

### Python gebruikt de verkeerde versie

Controleer:

```powershell
python --version
```

Voor deze test moet dit ongeveer zijn:

```text
Python 3.11.x
```

### De robot wordt niet gevonden

Controleer:

* staat de Create 3 aan?
* is iemand anders ermee verbonden?
* staat de robot dichtbij de computer?
* is `python.irobot.com` gesloten?
* is Bluetooth op de computer ingeschakeld?

Probeer daarna het programma opnieuw te starten.

### De robot rijdt te snel

Verlaag bijvoorbeeld:

```python
await robot.set_wheel_speeds(20, 20)
```

naar:

```python
await robot.set_wheel_speeds(10, 10)
```

### De robot rijdt te lang

Verlaag:

```python
await robot.wait(3)
```

bijvoorbeeld naar:

```python
await robot.wait(1)
```

---

## Belangrijk

Gebruik voor de eerste test altijd een **open ruimte**. De robot voert het rijcommando uit zonder rekening te houden met obstakels.

Deze eenvoudige test gebruikt alleen **Python + Bluetooth**. ROS 2, WSL en Wi-Fi zijn voor deze eerste test niet nodig.
