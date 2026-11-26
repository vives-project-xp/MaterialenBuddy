# Authentik starten

De officiële `compose.yml` en een `.env` met unieke willekeurige geheimen staan
klaar. Deel het `.env`-bestand niet. De bestaande `.gitignore` sluit het uit.

1. Start Docker Desktop en wacht tot Docker draait.
2. Open een terminal in deze map (`authentik-server`).
3. Start Authentik:

   ```powershell
   docker compose up -d
   ```

4. Open http://localhost:9000 en voltooi de eerste configuratie voor `akadmin`.
5. Volg daarna [de koppelinstructies](../documentatie/authentik-installatie.md), vanaf onderdeel 2:
   maak de groepen, het aparte MaterialenBuddy-adminaccount, de registratieflow
   die nieuwe accounts automatisch user maakt, en de application/provider.
6. Vul de providergegevens in `webapp/.env` in en start de webapp opnieuw.

Deze bestanden alleen activeren de login en zelfregistratie nog niet. Daarvoor
moet bovenstaande configuratie in Authentik eerst worden voltooid.

Status bekijken vanuit deze map:

```powershell
docker compose ps
docker compose logs --tail=50 server worker
```

Stoppen met behoud van gegevens:

```powershell
docker compose down
```

Bewaar de `.env` samen met je back-up van de Authentik-database. De geheime sleutel
blijft dezelfde bij opnieuw starten. Authentik gebruikt zijn eigen database;
de MaterialenBuddy-database in MySQL blijft afzonderlijk.

Officiële installatiehandleiding:
https://docs.goauthentik.io/install-config/install/docker-compose/
