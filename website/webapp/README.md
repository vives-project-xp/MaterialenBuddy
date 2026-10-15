# MaterialenBuddy webapp

## Doel

De webapp ondersteunt een medicijnlevering vanuit centrale locatie B303 naar een bestemming zoals B301 of B302. De gebruiker kiest een bestemming, voegt medicijnen toe en vraagt een levering aan.

## Hoe werkt de website?

1. De browser opent de webapp via `http://127.0.0.1:8000`.
2. De pagina vraagt de actuele voorraad op via `GET /voorraad`.
3. De voorraad wordt getoond met het aantal stuks per medicijn.
4. De gebruiker kiest een bestemming en voegt een of meerdere medicijnen toe.
5. Bij `Levering aanvragen` stuurt de browser een `POST /leveringen` naar de FastAPI-server.
6. De server controleert of de medicijnen bestaan en of er genoeg voorraad is.
7. Bij voldoende voorraad wordt de levering opgeslagen in MySQL.
8. De voorraad wordt verminderd en de wijziging wordt opgeslagen in `voorraad_mutaties`.
9. De webpagina haalt de voorraad opnieuw op, zodat de nieuwe aantallen zichtbaar worden.
10. Bij onvoldoende voorraad of een serverfout wordt een foutmelding getoond.

## Handmatig voorraad aanvullen

Voorraad wordt nooit automatisch aangevuld. Een gebruiker kiest in het onderdeel `Voorraad aanvullen` een medicijn en geeft een aantal in. De browser stuurt dan:

```text
POST /voorraad/{medicijn_id}
```

De server verhoogt de voorraad en registreert de positieve wijziging in `voorraad_mutaties` met de reden `Handmatig aangevuld`.

## Onderdelen

### Frontend: `index.html`

De frontend bestaat uit HTML, CSS en JavaScript in één bestand. De pagina bevat:

- bestemmingselectie;
- invoer voor medicijn en aantal;
- lijst met medicijnen voor de levering;
- huidige voorraad;
- handmatig voorraad aanvullen;
- robotstatus;
- voorraadmelding.

De JavaScript-code gebruikt `fetch()` om met de FastAPI-endpoints te communiceren. De browser praat dus niet rechtstreeks met MySQL.

### Backend: `server.py`

De backend gebruikt:

- Python;
- FastAPI voor HTTP-endpoints;
- Uvicorn als lokale webserver;
- SQLAlchemy voor databaseverbindingen en transacties;
- PyMySQL als MySQL-driver;
- `python-dotenv` om de configuratie uit `.env` te lezen.

De backend controleert voorraad in een database-transactie. Daardoor wordt een levering volledig teruggedraaid wanneer een medicijn niet bestaat of onvoldoende voorraad heeft.

### Database

De MySQL-database heet `materialenbuddy` en gebruikt deze tabellen:

- `medicijnen`: medicijnnaam en minimumvoorraad;
- `voorraad`: actuele voorraad per medicijn;
- `leveringen`: leveringsaanvragen en hun status;
- `levering_medicijnen`: medicijnen en aantallen per levering;
- `voorraad_mutaties`: geschiedenis van voorraadwijzigingen.

## API-endpoints

| Methode | Endpoint | Doel |
| --- | --- | --- |
| `GET` | `/` | Webpagina openen |
| `GET` | `/medicijnen` | Medicijnen met voorraad ophalen |
| `GET` | `/voorraad` | Actuele voorraad ophalen |
| `POST` | `/voorraad/{medicijn_id}` | Voorraad handmatig aanvullen |
| `POST` | `/leveringen` | Nieuwe levering maken en voorraad verminderen |
| `GET` | `/leveringen/{id}` | Een levering met status ophalen |

## Configuratie

Maak in dezelfde map als `server.py` een bestand `.env`:

```env
DATABASE_URL=mysql+pymysql://gebruikersnaam:wachtwoord@localhost:3306/materialenbuddy
```

Het wachtwoord hoort alleen lokaal in `.env` te staan. Deel dit bestand niet en commit het niet naar Git.

## Installatie

Open PowerShell in de map `website/webapp`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Website starten

```powershell
cd "C:\Users\Gebruiker\Documents\3de jaar\MaterialenBuddy\website\webapp"
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Open daarna:

```text
http://127.0.0.1:8000/
```

De terminal moet open blijven zolang de website draait. Stop de server met `Ctrl+C`.

## Handige controles

Controleer of de backend medicijnen kan ophalen via:

```text
http://127.0.0.1:8000/medicijnen
```

Controleer de actuele voorraad via:

```text
http://127.0.0.1:8000/voorraad
```

Als deze endpoints HTTP 500 geven, controleer dan eerst de MySQL-server, de database `materialenbuddy` en de `DATABASE_URL` in `.env`.

## Belangrijke huidige beperking

De webapp slaat leveringen en voorraad op in MySQL. De robotbesturing is in deze actuele webapp nog niet gekoppeld aan de levering; de robotstatus op de pagina is voorlopig een demo-status. De volgende integratiestap is de aangemaakte levering koppelen aan de Create 3-navigatie en daarna de echte robotstatus terugsturen naar de webapp.
