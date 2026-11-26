# Authentik instellen voor MaterialenBuddy

De koppeling is ingebouwd; een werkende Authentik-server en de instellingen in
`webapp/.env` zijn nog nodig. Je bestaande MySQL-database blijft behouden.
Authentik gebruikt een eigen PostgreSQL-database voor accounts.

## 1. Authentik installeren

Start Docker Desktop. Installeer Authentik in een aparte map, bijvoorbeeld
`authentik` naast `webapp`. Gebruik de actuele officiële Compose-configuratie:
https://docs.goauthentik.io/install-config/install/docker-compose/

Voer vanuit de hoofdmap van dit project uit in PowerShell:

```powershell
New-Item -ItemType Directory -Path authentik -Force
Set-Location authentik
Invoke-WebRequest https://docs.goauthentik.io/compose.yml -OutFile compose.yml
```

Maak in die nieuwe map een `.env` met twee verschillende willekeurige geheimen:

```env
PG_PASS=een-lang-willekeurig-wachtwoord
AUTHENTIK_SECRET_KEY=een-ander-lang-willekeurig-geheim
```

Maak bijvoorbeeld per geheim een willekeurige waarde met PowerShell:

```powershell
$secretBytes = New-Object byte[] 48
$generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$generator.GetBytes($secretBytes)
[Convert]::ToBase64String($secretBytes)
$generator.Dispose()
```

Start daarna vanuit de map `authentik`:

```powershell
docker compose pull
docker compose up -d
```

Open `http://localhost:9000` en voltooi de eerste configuratie voor `akadmin`.
Voor extern gebruik: stel een domein met HTTPS in volgens de officiële handleiding.

## 2. Groepen en accounts

Maak in de Authentik-beheeromgeving onder **Directory > Groups**:

- `materialenbuddy-admins`
- `materialenbuddy-users`

### Apart adminaccount

Maak onder **Directory > Users** een apart account, bijvoorbeeld
`materialenbuddy-admin`. Stel een wachtwoord in en voeg dit account toe aan
`materialenbuddy-admins`. Geef het account aan de persoon die de website gaat
beheren. Je eigen account hoeft geen MaterialenBuddy-admin te zijn.

Dit account krijgt alle beschikbare beheerfuncties op de website. Het hoeft
geen Authentik-superuser te zijn. Het initiële `akadmin`-account gebruik je voor
de technische configuratie van Authentik; dat is een ander account.

Lidmaatschap van de admin-groep heeft voorrang wanneer iemand in beide groepen
zit. Accounts zonder een van deze groepen worden door de webapp geweigerd.

### Zelfregistratie: nieuwe accounts automatisch user

De gewenste route is: **Inloggen of account maken** op de website → het
Authentik-inlogscherm → **Registreren** → gegevens invullen → automatisch lid
van `materialenbuddy-users` → bestellen op de website.

Dit stel je in Authentik in; alleen de webapp aanpassen schakelt registratie
niet in. Maak een eigen enrollment flow zodat de groepskeuze vastligt:

1. Ga naar **Flows and Stages > Flows** en maak een flow met de naam
   `MaterialenBuddy registratie`, slug `materialenbuddy-registratie`, designation
   **Enrollment** en authentication **Require unauthenticated**.
2. Maak onder **Flows and Stages > Prompts** verplichte velden voor
   gebruikersnaam (field key `username`, type Username), naam (`name`, Text),
   e-mailadres (`email`, Email), wachtwoord (`password`, Password) en
   wachtwoordbevestiging (`password_repeat`, Password).
3. Maak onder **Stages** een **Prompt stage** met deze velden. Koppel de
   beschikbare standaard password validation policy voor enrollment aan de
   validation policies van deze stage; zo worden wachtwoord en bevestiging
   gecontroleerd. Neem geen invoerveld voor een rol of groep op.
4. Maak een eigen **User Write stage**, bijvoorbeeld
   `materialenbuddy-registratie-user-write`, met:

   | Instelling | Waarde |
   | --- | --- |
   | User creation mode | Always create |
   | Create users group | `materialenbuddy-users` |
   | Create users as inactive | Uit |
   | User type | Internal |

5. Maak een **User Login stage** voor deze registratie.
6. Open de registratieflow en bind onder **Stage Bindings** de Prompt stage op
   volgorde 10, de User Write stage op 20 en de User Login stage op 30.
7. Open de **Identification stage** die aan je gebruikte authentication flow
   gekoppeld is (bij een standaardinstallatie doorgaans
   `default-authentication-identification`). Kies bij **Enrollment flow** de
   flow `materialenbuddy-registratie`. Hierdoor verschijnt de registratielink
   onder het inlogformulier.
8. Als je de toegang tot de application met groepsbindings beperkt, laat dan
   zowel `materialenbuddy-users` als `materialenbuddy-admins` toe met **Any**
   als policy engine mode. Anders kunnen nieuwe users na registratie worden
   tegengehouden.

De vaste instelling **Create users group** zorgt dat nieuwe accounts automatisch
user worden. Zet hier nooit de admin-groep. Een gebruiker kan bij registratie
geen adminrechten kiezen. Een bevoegde Authentik-beheerder kan later handmatig
een account aan `materialenbuddy-admins` toevoegen.

Bronnen: [User Write stage](https://docs.goauthentik.io/add-secure-apps/flows-stages/stages/user_write)
en [Identification stage](https://docs.goauthentik.io/add-secure-apps/flows-stages/stages/identification/).

## 3. Application en provider

Maak onder **Applications** een application met een **OAuth2/OpenID Connect**
provider. Gebruik deze instellingen:

| Instelling | Waarde |
| --- | --- |
| Application slug | `materialenbuddy` |
| Client type | Confidential |
| Redirect URI (Strict) | `http://localhost:8000/auth/callback` |
| Flow | Authorization code |
| Scopes / scope mappings | Standaard `openid`, `profile`, `email` |
| Signing key | Selecteer een beschikbare asymmetrische signing key |

Kies de standaard beschikbare authentication/authorization flows. Bewaar de
gegenereerde client ID en client secret. Laat claims uit de scope mappings ook
in het ID-token opnemen (**Include claims in id_token**). De standaard `profile`
mapping geeft de claim `groups` mee; verwijder die niet. Een aangepaste mapping
moet dezelfde groepsnamen teruggeven.

Officiële documentatie:
https://docs.goauthentik.io/add-secure-apps/providers/oauth2/

## 4. Webapp configureren

Voeg de velden uit `.env.example` toe aan je bestaande `webapp/.env`.
Behoud je bestaande `DATABASE_URL`. Vul client ID en client secret in en genereer
een derde willekeurige waarde voor `SESSION_SECRET` (minstens 32 tekens).

Voor een webapp die rechtstreeks met Python op dezelfde computer draait:

```env
AUTHENTIK_DISCOVERY_URL=http://localhost:9000/application/o/materialenbuddy/.well-known/openid-configuration
AUTHENTIK_CLIENT_ID=client-id-uit-authentik
AUTHENTIK_CLIENT_SECRET=client-secret-uit-authentik
AUTHENTIK_REDIRECT_URI=http://localhost:8000/auth/callback
AUTHENTIK_ADMIN_GROUP=materialenbuddy-admins
AUTHENTIK_USER_GROUP=materialenbuddy-users
SESSION_SECRET=een-derde-willekeurig-geheim-van-minstens-32-tekens
SESSION_COOKIE_SECURE=false
```

Open de website consequent via `http://localhost:8000`, zodat cookies en redirect
URI overeenkomen. `127.0.0.1` en `localhost` zijn voor cookies verschillende hosts.
Bij HTTPS zet je `SESSION_COOKIE_SECURE=true` en gebruik je de echte HTTPS-URL
als redirect URI, zowel in `.env` als bij de provider.

**Als de webapp ook in Docker draait:** `localhost:9000` verwijst vanuit de
webcontainer naar die container zelf. Gebruik voor Authentik een hostname die
zowel je browser als de webcontainer kan bereiken. Op Docker Desktop kun je
`host.docker.internal:9000` gebruiken als deze ook in je browser bereikbaar is.
Open dan ook Authentik via die hostname voordat je de provider configureert,
en gebruik diezelfde hostname in de discovery-URL. Wijzig de redirect URI van de
webapp niet: die blijft `http://localhost:8000/auth/callback`.

Installeer vanuit `webapp` de afhankelijkheden en start de webapp opnieuw:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Of start de bestaande app met database via `docker compose up --build` vanuit
`webapp`. De Authentik-containers draaien afzonderlijk.

## 5. Rechten controleren

| Actie | User | Admin |
| --- | --- | --- |
| Voorraad bekijken | Ja | Ja |
| Medicijnen aan een nieuwe bestelling toevoegen | Ja | Ja |
| Bestelling indienen | Ja | Ja |
| Ingediende bestelling wijzigen | Nee | Geen wijzigingsfunctie aanwezig |
| Voorraad aanvullen | Nee | Ja |
| Materialen registreren, naam of minimum wijzigen | Nee | Ja |
| Materiaal zonder historiek verwijderen | Nee | Ja |

De bestaande database bewaart leveringen en voorraadhistoriek. Materialen met die
historiek kunnen daarom ook door een admin niet worden verwijderd (HTTP 409).
Een item verwijderen uit een nog niet ingediende bestellijst wijzigt geen
opgeslagen bestelling en is toegestaan.

Test met twee accounts en een privévenster. Een user krijgt HTTP 403 bij
voorraad- of materiaalbeheer, ook als die de API rechtstreeks aanroept.
Zonder login geven data-endpoints HTTP 401. Schrijfacties vereisen de
`X-CSRF-Token` header uit `/auth/me`; de frontend verzorgt die automatisch.

Controleer ook de registratie in een privévenster:

1. Klik op **Inloggen of account maken** en daarna op de registratielink.
2. Registreer een nieuw account en controleer in Authentik dat het automatisch
   lid is van `materialenbuddy-users` en niet van `materialenbuddy-admins`.
3. Controleer dat het account kan bestellen, maar geen voorraadbeheer ziet.
4. Meld apart aan met `materialenbuddy-admin` en controleer voorraadbeheer.

Groepen worden bij het inloggen vastgesteld. Een sessie verloopt uiterlijk na
één uur, of eerder als het ID-token verloopt. Na een groepswijziging opnieuw
inloggen; bestaande sessies veranderen niet onmiddellijk. Uitloggen op de
website beëindigt alleen de MaterialenBuddy-sessie, niet de centrale
Authentik-sessie. Voor een ander account log je ook uit bij Authentik of gebruik
je een privévenster.

De applicatie start bewust niet zonder geldige authenticatieconfiguratie.
Wachtwoorden en client secrets horen alleen in `.env`, nooit in de HTML.
