# Authentik verder instellen voor MaterialenBuddy

Deze handleiding begint bij je huidige stap. Authentik draait en de groepen `materialenbuddy-admins` en `materialenbuddy-users` zijn aangemaakt. Je bent bezig met het account voor de websitebeheerder.

De stappen zijn bedoeld voor lokaal gebruik op deze computer. Schermnamen kunnen per Authentik-versie licht verschillen. Vink een onderdeel af zodra je het hebt uitgevoerd.

## 1. Het beheeraccount afwerken

1. Open de Authentik-beheeromgeving via `http://localhost:9000/if/admin/` en meld aan met je bestaande Authentik-beheeraccount.
2. Ga naar **Directory → Users**.
3. Als het account nog niet opgeslagen is, klik op **Create** en vul de onderstaande waarden in. Als het al bestaat, open je dat account.

| Veld | Waarde |
| --- | --- |
| Username | `materialenbuddy-admin` |
| Name | De naam van de websitebeheerder |
| Email | Het e-mailadres van de beheerder, voorlopig je eigen adres als jij het beheert |
| User type | **Internal** |
| Active | Aan |
| Path | Standaardwaarde laten staan |
| Attributes | Standaardwaarde laten staan |

4. Klik op **Create** of **Save**.
5. Open de gebruiker en klik op **Set password**. Dit kan onder het actiemenu staan.
6. Vul tweemaal hetzelfde wachtwoord in en bevestig.
7. Open bij deze gebruiker **Groups** en kies **Add to existing group** of de overeenkomstige knop.
8. Selecteer `materialenbuddy-admins` en bevestig.
9. Als groepslidmaatschap via de gebruiker niet beschikbaar is, ga naar **Directory → Groups → materialenbuddy-admins → Users**, kies **Add existing user** en selecteer `materialenbuddy-admin`.
10. Controleer dat het account bij de groep vermeld staat.

- [ ] Beheeraccount opgeslagen, wachtwoord ingesteld en groepslidmaatschap gecontroleerd.

Gebruik je bestaande Authentik-beheeraccount voor alle configuratiestappen hieronder. Het nieuwe account gebruik je straks om de website te beheren.

## 2. Bepalen hoe je de website start

Kies de rij die overeenkomt met hoe je de webapp uitvoert. Authentik zelf mag in beide gevallen in Docker blijven draaien.

| Hoe de webapp draait | Authentik-adres voor de volgende stappen |
| --- | --- |
| Via Python met `python -m uvicorn ...` | `http://localhost:9000` |
| Via `docker compose` in de map `webapp` | `http://host.docker.internal:9000` |

1. Open het Authentik-adres uit jouw rij in je browser.
2. Controleer dat de inlogpagina of gebruikersomgeving verschijnt.
3. Meld indien nodig opnieuw aan met je Authentik-beheeraccount.
4. Open `/if/admin/` achter datzelfde adres.
5. Gebruik dit adres consequent bij het configureren en testen van Authentik.

Bij Docker moet hetzelfde Authentik-adres bereikbaar zijn vanuit je browser en de webcontainer. Als `host.docker.internal` in je browser niet opent, moet die bereikbaarheid eerst opgelost worden voordat je de Docker-route kunt testen.

- [ ] Uitvoermethode gekozen en Authentik-adres geopend.

## 3. De registratieflow maken

### 3.1 De flow aanmaken

1. Ga naar **Flows and Stages → Flows**.
2. Klik op **Create**.
3. Vul de volgende waarden in.

| Veld | Waarde |
| --- | --- |
| Name | `MaterialenBuddy registratie` |
| Slug | `materialenbuddy-registratie` |
| Title | `Maak je MaterialenBuddy-account aan` |
| Designation | **Enrollment** |
| Authentication | **Require unauthenticated** |

4. Laat de overige instellingen op hun standaardwaarde staan en sla op.

### 3.2 De vijf invoervelden aanmaken

1. Ga naar **Flows and Stages → Prompts**. In sommige versies staan prompts bij **Stages** onder een apart tabblad.
2. Klik op **Create**.
3. Maak één prompt per rij van deze tabel. Klik na iedere prompt op **Create** en begin daarna opnieuw voor de volgende rij.

| Name, indien gevraagd | Field key | Label | Type | Order | Required |
| --- | --- | --- | --- | --- | --- |
| `mb-username` | `username` | Gebruikersnaam | Username | 10 | Aan |
| `mb-name` | `name` | Naam | Text | 20 | Aan |
| `mb-email` | `email` | E-mailadres | Email | 30 | Aan |
| `mb-password` | `password` | Wachtwoord | Password | 40 | Aan |
| `mb-password-repeat` | `password_repeat` | Herhaal wachtwoord | Password | 50 | Aan |

4. Laat **Placeholder** en **Initial value** leeg.
5. Laat het interpreteren van die waarden als expressie uitgeschakeld.
6. Controleer dat alle vijf prompts zijn opgeslagen.

### 3.3 De Prompt stage maken

1. Ga naar **Flows and Stages → Stages**.
2. Klik op **Create**.
3. Selecteer **Prompt Stage** en klik op **Next**.
4. Geef als naam `materialenbuddy-registratie-prompt` op.
5. Selecteer bij **Fields** alle vijf prompts die je net hebt gemaakt.
6. Selecteer bij **Validation Policies** de standaard wachtwoordpolicy voor enrollment als die aanwezig is, doorgaans `default-password-policy`.
7. Sla de stage op.

De twee velden van het type Password moeten in dezelfde Prompt stage staan. Authentik controleert dan dat beide waarden overeenkomen. De geselecteerde wachtwoordpolicy bepaalt aanvullende wachtwoordeisen. [Prompt stage](https://docs.goauthentik.io/add-secure-apps/flows-stages/stages/prompt/)

### 3.4 De User Write stage maken

1. Klik onder **Stages** opnieuw op **Create**.
2. Selecteer **User Write Stage** en klik op **Next**.
3. Vul de onderstaande instellingen in.

| Veld | Waarde |
| --- | --- |
| Name | `materialenbuddy-registratie-user-write` |
| User creation mode | **Always create** |
| Create users group | `materialenbuddy-users` |
| Create users as inactive | Uit |
| User type | **Internal** |
| User path | Standaardwaarde laten staan |

4. Sla op.

De instelling **Create users group** voegt nieuwe accounts automatisch toe aan `materialenbuddy-users`. [User Write stage](https://docs.goauthentik.io/add-secure-apps/flows-stages/stages/user_write/)

### 3.5 De User Login stage maken

1. Klik onder **Stages** op **Create**.
2. Selecteer **User Login Stage** en klik op **Next**.
3. Geef als naam `materialenbuddy-registratie-login` op.
4. Laat de overige instellingen op hun standaardwaarde staan.
5. Sla op.

### 3.6 De stages aan de flow koppelen

1. Ga naar **Flows and Stages → Flows**.
2. Open `MaterialenBuddy registratie`.
3. Open **Stage Bindings**.
4. Klik op **Bind existing stage**.
5. Selecteer `materialenbuddy-registratie-prompt`, vul **Order 10** in en sla op.
6. Klik opnieuw op **Bind existing stage**.
7. Selecteer `materialenbuddy-registratie-user-write`, vul **Order 20** in en sla op.
8. Klik opnieuw op **Bind existing stage**.
9. Selecteer `materialenbuddy-registratie-login`, vul **Order 30** in en sla op.
10. Controleer dat de drie stages in deze volgorde vermeld staan.

### 3.7 De registratielink op het inlogscherm zetten

1. Ga naar **Flows and Stages → Flows**.
2. Open `default-authentication-flow` en bekijk onder **Stage Bindings** welke Identification stage gebruikt wordt.
3. Ga naar **Flows and Stages → Stages**.
4. Bewerk die Identification stage, doorgaans `default-authentication-identification`.
5. Kies bij **Enrollment flow** de flow `MaterialenBuddy registratie`.
6. Sla op.

- [ ] Flow, vijf prompts, drie stages en registratielink ingesteld.

## 4. De provider voor de website maken

1. Ga naar **Applications → Providers**.
2. Klik op **Create**.
3. Kies **OAuth2/OpenID Provider** en klik op **Next**.
4. Vul de onderstaande instellingen in. Open indien nodig de uitklapbare onderdelen voor protocolinstellingen en geavanceerde instellingen.

| Veld | Waarde |
| --- | --- |
| Name | `MaterialenBuddy provider` |
| Authentication flow, indien getoond | `default-authentication-flow` |
| Authorization flow | `default-provider-authorization-implicit-consent` |
| Invalidation flow, indien verplicht | De standaard provider invalidation flow |
| Client type | **Confidential** |
| Client ID | De gegenereerde waarde behouden |
| Client Secret | De gegenereerde waarde behouden |
| Redirect URIs, matching mode | **Strict** |
| Redirect URIs, URL | `http://localhost:8000/auth/callback` |
| Signing key | De beschikbare asymmetrische sleutel, doorgaans `authentik Self-signed Certificate` |
| Scopes / Scope mappings | De standaard mappings voor `openid`, `email` en `profile` selecteren |
| Include claims in id_token | Aan |

5. Kopieer de Client ID en Client Secret tijdelijk naar de bijbehorende velden in `webapp/.env`, zoals beschreven in stap 6.
6. Sla de provider op.

De website gebruikt de authorization code flow. Als jouw versie een keuze voor toegestane grant types toont, schakel **Authorization code** in. Het woord `implicit` in de naam van de consentflow hierboven verwijst naar toestemming zonder extra bevestigingsscherm. [OAuth2-provider](https://docs.goauthentik.io/add-secure-apps/providers/oauth2/)

## 5. De application maken en toegang instellen

1. Ga naar **Applications → Applications**.
2. Klik op **Create**.
3. Vul de onderstaande waarden in.

| Veld | Waarde |
| --- | --- |
| Name | `MaterialenBuddy` |
| Slug | `materialenbuddy` |
| Provider | `MaterialenBuddy provider` |
| Launch URL | `http://localhost:8000` |
| Policy engine mode | **Any** |

4. Sla op en open de application.
5. Open **Policy / Group / User Bindings**.
6. Klik op **Bind existing Policy / Group / User**.
7. Kies het tabblad of type **Group** en selecteer `materialenbuddy-admins`.
8. Zet **Enabled** aan, laat **Negate** uit, vul **Order 10** in en sla op.
9. Maak op dezelfde manier een tweede binding voor `materialenbuddy-users`, met **Order 20**.
10. Controleer dat **Policy engine mode** op **Any** staat. Lidmaatschap van één van de twee groepen geeft dan toegang.

- [ ] Provider en application opgeslagen, beide groepen gekoppeld.

## 6. Het bestand webapp/.env invullen

1. Open in je editor de map `webapp`.
2. Open `.env`. Als het bestand ontbreekt, maak in die map een bestand met exact de naam `.env`.
3. Behoud de bestaande database-instellingen en eventuele `MYSQL_PASSWORD` en `MYSQL_ROOT_PASSWORD`.
4. Voeg onderstaande regels toe. Als een instelling al bestaat, pas die regel aan zodat iedere instelling één keer voorkomt.

```env
AUTHENTIK_DISCOVERY_URL=http://localhost:9000/application/o/materialenbuddy/.well-known/openid-configuration
AUTHENTIK_CLIENT_ID=PLAK_HIER_DE_CLIENT_ID
AUTHENTIK_CLIENT_SECRET=PLAK_HIER_DE_CLIENT_SECRET
AUTHENTIK_REDIRECT_URI=http://localhost:8000/auth/callback
AUTHENTIK_ADMIN_GROUP=materialenbuddy-admins
AUTHENTIK_USER_GROUP=materialenbuddy-users
SESSION_SECRET=PLAK_HIER_EEN_NIEUW_WILLEKEURIG_GEHEIM
SESSION_COOKIE_SECURE=false
```

5. Draait de webapp in Docker, gebruik dan voor de eerste regel deze waarde.

```env
AUTHENTIK_DISCOVERY_URL=http://host.docker.internal:9000/application/o/materialenbuddy/.well-known/openid-configuration
```

6. Open de provider in Authentik en kopieer de echte **Client ID** naar `AUTHENTIK_CLIENT_ID`.
7. Kopieer de echte **Client Secret** naar `AUTHENTIK_CLIENT_SECRET`.
8. Open een PowerShell-terminal en voer de volgende code uit om een nieuw sessiegeheim te maken.

```powershell
$sessionBytes = New-Object byte[] 48
$sessionGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$sessionGenerator.GetBytes($sessionBytes)
[Convert]::ToBase64String($sessionBytes)
$sessionGenerator.Dispose()
```

9. Kopieer de uitgeprinte waarde naar `SESSION_SECRET`.
10. Sla `.env` op.
11. Controleer dat alle drie de `PLAK_HIER...`-waarden vervangen zijn.

Bewaar deze geheimen in `.env`. Voor de Python-route moet de bestaande `DATABASE_URL` naar je werkende MySQL-database verwijzen. Bij de Docker-route stelt `docker-compose.yaml` de databaseverbinding in met de bestaande Docker-database-instellingen.

- [ ] `.env` ingevuld en opgeslagen.

## 7. De discovery-URL controleren

1. Kopieer alleen de URL achter `AUTHENTIK_DISCOVERY_URL` uit `.env`.
2. Open die URL in je browser.
3. Controleer dat je JSON ziet met onder andere `issuer`, `authorization_endpoint`, `token_endpoint` en `jwks_uri`.
4. Controleer dat de adressen daarin dezelfde Authentik-hostnaam gebruiken als je gekozen adres uit stap 2.
5. Bij een foutmelding controleer je of de application-slug exact `materialenbuddy` is en of de provider eraan gekoppeld is.

- [ ] Discovery-URL geeft JSON terug.

## 8. De website starten of herstarten

Voer één van de twee routes hieronder uit, afhankelijk van je keuze in stap 2. Open in je editor een terminal in de map `webapp`. Controleer de terminalmap voordat je het commando uitvoert.

### Route A — webapp met Docker

1. Zorg dat Docker Desktop actief is.
2. Voer vanuit `webapp` het volgende commando uit.

```powershell
docker compose up -d --build
```

3. Controleer de status.

```powershell
docker compose ps
```

4. Controleer dat `db` gezond is en `web` draait.
5. Als `web` herstart of stopt, bekijk de logs.

```powershell
docker compose logs --tail 100 web
```

### Route B — webapp rechtstreeks met Python

1. Zorg dat je bestaande MySQL-database draait.
2. Activeer je bestaande Python-omgeving als je er een gebruikt.
3. Installeer vanuit `webapp` de vereiste pakketten.

```powershell
python -m pip install -r requirements.txt
```

4. Als de webapp al draait in een terminal, stop die met **Ctrl+C**.
5. Start vanuit `webapp` de website.

```powershell
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

6. Laat deze terminal open zolang je de website gebruikt.

- [ ] Website gestart zonder opstartfout.

## 9. Aanmelden als websitebeheerder testen

1. Open een nieuw privévenster in je browser.
2. Open `http://localhost:8000`.
3. Klik op **Inloggen of account maken**.
4. Controleer dat het Authentik-inlogscherm opent.
5. Meld aan met `materialenbuddy-admin` en het ingestelde wachtwoord.
6. Doorloop eventuele extra stappen die jouw Authentik-inlogflow toont.
7. Controleer dat je terugkeert naar MaterialenBuddy.
8. Controleer dat je de voorraad kunt zien en de beheerfuncties voor voorraad en materialen beschikbaar zijn.
9. Controleer eventueel `http://localhost:8000/auth/me` in hetzelfde privévenster om je aangemelde account en rol te bekijken.
10. Sluit alle privévensters om de sessie af te sluiten voordat je de registratie test.

- [ ] Inloggen met de websitebeheerder werkt en beheerfuncties verschijnen.

## 10. Zelfregistratie en gebruikersrechten testen

1. Open een nieuw privévenster.
2. Ga naar `http://localhost:8000`.
3. Klik op **Inloggen of account maken**.
4. Klik op **Registreren** of de enrollment-link onder het Authentik-inlogformulier.
5. Vul een nieuwe, unieke testgebruikersnaam in, bijvoorbeeld `materialenbuddy-testuser`.
6. Vul een naam en een e-mailadres in dat je kunt gebruiken voor deze test.
7. Vul in beide wachtwoordvelden hetzelfde wachtwoord in.
8. Verstuur het registratieformulier.
9. Controleer dat de registratie slaagt en je terugkeert naar de website. Als Authentik eerst zijn gebruikersomgeving toont, open opnieuw `http://localhost:8000` en klik op de inlogknop.
10. Open in je gewone browservenster de Authentik-beheeromgeving met je Authentik-beheeraccount.
11. Ga naar **Directory → Users** en open de nieuwe testgebruiker.
12. Controleer onder **Groups** dat deze gebruiker lid is van `materialenbuddy-users` en dat `materialenbuddy-admins` ontbreekt.
13. Controleer in het privévenster dat de testgebruiker voorraad kan bekijken en items aan een bestellijst kan toevoegen.
14. Dien een testbestelling alleen in met gegevens die je in je lokale database wilt bewaren.
15. Controleer dat voorraadbeheer en materiaalbeheer voor deze gebruiker afgeschermd zijn.

- [ ] Registreren werkt en het account krijgt automatisch de gebruikersgroep.
- [ ] De gebruiker kan bestellen en het beheeraccount kan voorraad beheren.

## 11. Als een stap fout loopt

| Wat je ziet | Wat je controleert en doet |
| --- | --- |
| Geen registratielink | Controleer de Enrollment flow op de Identification stage van de gebruikte authentication flow, volgens stap 3.7. Test in een nieuw privévenster. |
| Gebruiker wordt niet aangemaakt | Controleer de volgorde Prompt 10, User Write 20, User Login 30. Zet User creation mode op Always create. |
| Registratie slaagt maar toegang wordt geweigerd | Controleer de gebruikersgroep en de twee application-bindings met Any. |
| Redirect URI-fout | Zet in de provider en `.env` exact `http://localhost:8000/auth/callback` en herstart de webapp. |
| Invalid client of client authentication failed | Kopieer de Client ID en Client Secret opnieuw uit de gekoppelde provider naar `.env` en herstart de webapp. |
| Discovery kan niet opgehaald worden | Controleer de URL uit stap 7. Gebruik bij Docker de bereikbare host `host.docker.internal` voor Authentik. |
| Website blijft terugsturen naar inloggen | Controleer `SESSION_COOKIE_SECURE=false` voor lokaal HTTP, gebruik consequent `localhost:8000` en herstart na een wijziging. |
| Account heeft geen toegestane groep | Controleer exact de groepsnamen in Authentik en `.env`. Meld opnieuw aan na aanpassing. |
| Groepen ontbreken in het token | Selecteer de standaard profile scope mapping en zet Include claims in id_token aan in de provider. Meld opnieuw aan. |
| Je wordt automatisch met het vorige account aangemeld | Sluit alle privévensters en open een nieuw privévenster. De website en Authentik hebben elk hun eigen sessie. |
| Poort 8000 is bezet | Stop de eerdere webapp in de bijbehorende terminal of Docker-service voordat je dezelfde webapp opnieuw start. |

## Afronding

- [ ] Alle stappen hierboven zijn uitgevoerd.
- [ ] De beheerder kan aanmelden en voorraad beheren.
- [ ] Nieuwe gebruikers kunnen zichzelf registreren.
- [ ] Nieuwe accounts krijgen automatisch `materialenbuddy-users`.
- [ ] Gebruikers kunnen bestellen en krijgen de bedoelde toegangsrechten.

Deze handleiding rondt de lokale koppeling af. Voor gebruik via een publiek domein horen de Authentik-URL, callback-URL en HTTPS-cookie-instelling bij die omgeving.
