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

De server verhoogt de voorraad en registreert de positieve wijziging in `voorraad_mutaties` met de reden `Handmatig aangevuld`. Het onderdeel `Voorraad aanvullen` is alleen zichtbaar voor gebruikers in de rol **staff**.

## Authenticatie (Authentik)

De webapp gebruikt [Authentik](https://goauthentik.io/) voor inloggen via OpenID Connect (OIDC). Alleen de startpagina `GET /` is publiek; alle overige endpoints eisen een aangemelde gebruiker, en `POST /voorraad/{medicijn_id}` vereist bovendien de rol **staff**.

### Hoe werkt het inloggen?

De webapp gebruikt de OAuth2 *authorization-code flow* met **PKCE** (S256). Het verloopt zo:

1. De gebruiker klikt op **Inloggen**; de browser gaat naar `/auth/login`.
2. De server genereert een `code_verifier`/`code_challenge`, slaat de verifier op in een HTTP-only cookie `mb_pkce` en stuurt de door naar de **Authorize**-endpoint van Authentik.
3. De gebruiker meldt zich aan bij Authentik en stemt toe. Authentik stuurt de browser terug naar `http://localhost:8000/auth/callback` met een `code` mee.
4. `/auth/callback` wisselt de `code` voor tokens in bij Authentik (met de `code_verifier` Ã©n het `client_secret`), controleert de `id_token` aan de hand van de JWKS-sleutels van Authentik en legt een sessie vast.
5. De sessie is een getekend JWT (HS256) in een HTTP-only cookie `mb_session` (samesite=lax) met een geldigheidsduur van 8 uur.
6. `/auth/me` geeft de gegevens van de aangemelde gebruiker terug; `/auth/logout` verwijdert de sessie.

### Rollen

Een gebruiker heeft de rol **staff** wanneer in de `id_token` een van deze waarden voorkomt:

- de claim `staff` is `true`, of
- in `authentik_groups` / `groups` staat de groep `staff`.

In Authentik maak je dan een **groep** aan met de exacte naam `staff` en leg je de gewenste gebruikers in die groep.

### Authentik starten

De Authentik-stack staat in een eigen map. Open PowerShell in `website/authentik`:

```powershell
cd "C:\Users\Gebruiker\Documents\3de jaar\MaterialenBuddy\website\authentik"
docker compose up -d
```

Authentik draait daarna op `http://localhost:9000`.

### Een toepassing (application) aanmaken in Authentik

1. Open de admin op `http://localhost:9000/if/admin/` en log in (de eerste gebruiker wordt bij de eerste start aangemaakt via het setup-scherm).
2. Ga naar **Providers** â†’ **Add** â†’ **OpenID Provider** (OIDC) en geef hem een naam, bijvoorbeeld `materialenbuddy`.
3. Ga naar **Applications** â†’ **Add** en kies de zojuist aangemaakte provider. Zet **Client ID** op `materialenbuddy` en voeg bij **Redirect URIs** de URL `http://localhost:8000/auth/callback` toe.
4. Open de applicatie en kopieer de **Client secret**. Vul die waarde in je `.env` in onder `AUTHENTIK_CLIENT_SECRET`.
5. Zet de gewenste gebruikers in de groep `staff` (zie **Rollen** hierboven).

### Verplichte omgevingsvariabelen

De webapp leest deze waarden uit de omgeving (zie `.env` / `.env.example`):

| Variabele | Doel | Standaard |
| --- | --- | --- |
| `AUTHENTIK_ISSUER` | Basis-URL van de Authentik-server | `http://localhost:9000` |
| `AUTHENTIK_CLIENT_ID` | Client ID van de OIDC-toepassing | `materialenbuddy` |
| `AUTHENTIK_CLIENT_SECRET` | Client secret (verplicht invullen) | â€” |
| `AUTHENTIK_REDIRECT_URI` | Terug-redirect van de browser | `http://localhost:8000/auth/callback` |
| `SESSION_SECRET` | Sleutel om het sessie-JWT te tekenen | alleen dev-waarde |
| `SESSION_MAX_AGE_SECONDS` | Levensduur van de sessie | `28800` (8 uur) |

> **Let op (Docker):** als je de webapp met Docker draait, praat de webapp-server vanuit een container naar de Authentik-server op de host. Gebruik daarvoor `AUTHENTIK_ISSUER=http://host.docker.internal:9000`. De `AUTHENTIK_REDIRECT_URI` blijft op `http://localhost:8000/auth/callback`, want die URL wordt door de browser gebruikt. De webapp `docker-compose.yaml` zet dit al automatisch in.

> Voor productie moet je zowel `AUTHENTIK_ISSUER` als `AUTHENTIK_REDIRECT_URI` gebruiken met HTTPS en het juiste domein.

## Onderdelen

### Frontend: `index.html`

De frontend bestaat uit HTML, CSS en JavaScript in Ã©Ã©n bestand. De pagina bevat:

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

| Methode | Endpoint | Doel | Toegang |
| --- | --- | --- | --- |
| `GET` | `/` | Webpagina openen | Publiek |
| `GET` | `/auth/login` | Naar de login van Authentik doorsturen | Publiek |
| `GET` | `/auth/callback` | OIDC-callback na het inloggen | Publiek |
| `GET` | `/auth/me` | Aangemelde gebruiker ophalen | Aangemeld |
| `POST` | `/auth/logout` | Sessie beÃ«indigen | Publiek |
| `GET` | `/medicijnen` | Medicijnen met voorraad ophalen | Aangemeld |
| `GET` | `/voorraad` | Actuele voorraad ophalen | Aangemeld |
| `POST` | `/voorraad/{medicijn_id}` | Voorraad handmatig aanvullen | Staff |
| `POST` | `/leveringen` | Nieuwe levering maken en voorraad verminderen | Aangemeld |
| `GET` | `/leveringen/{id}` | Een levering met status ophalen | Aangemeld |

## Configuratie

Maak in dezelfde map als `server.py` een bestand `.env` (kopieer `.env.example` als startpunt):

```env
DATABASE_URL=mysql+pymysql://<gebruiker>:<wachtwoord>@localhost:3306/materialenbuddy
AUTHENTIK_ISSUER=http://localhost:9000
AUTHENTIK_CLIENT_ID=materialenbuddy
AUTHENTIK_CLIENT_SECRET=
AUTHENTIK_REDIRECT_URI=http://localhost:8000/auth/callback
SESSION_SECRET=
SESSION_MAX_AGE_SECONDS=28800
```

Daarnaast zijn voor de authenticatie de variabelen `AUTHENTIK_CLIENT_ID`, `AUTHENTIK_CLIENT_SECRET`, `AUTHENTIK_ISSUER`, `AUTHENTIK_REDIRECT_URI`, `SESSION_SECRET` en `SESSION_MAX_AGE_SECONDS` nodig (zie de sectie [Authenticatie](#authenticatie-authentik) en `.env.example`). Vul `AUTHENTIK_CLIENT_SECRET` en een lange willekeurige `SESSION_SECRET` in. Het wachtwoord en de secrets horen alleen lokaal in `.env` te staan. Deel dit bestand niet en commit het niet naar Git.

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

## Starten met Docker

Docker start automatisch zowel MySQL als de FastAPI-webapp. Open PowerShell in deze map:

```powershell
cd "C:\Users\Gebruiker\Documents\3de jaar\MaterialenBuddy\website\webapp"
docker compose up --build
```

Open daarna http://127.0.0.1:8000/. De database wordt bij de eerste start aangemaakt met het schema uit `website/database/materialenbuddy_test_database.sql` en testdata uit `website/database/02-seed.sql`.

Stop de containers met:

```powershell
docker compose down
```

Ook de MySQL-data verwijderen en helemaal opnieuw initialiseren:

```powershell
docker compose down -v
```

De standaard Docker-wachtwoorden zijn alleen bedoeld voor lokaal testen. Je kunt ze aanpassen met `MYSQL_PASSWORD` en `MYSQL_ROOT_PASSWORD` in een `.env`-bestand naast `docker-compose.yaml`.

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
