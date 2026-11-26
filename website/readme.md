# Website

Met de webapp van MaterialenBuddy kan zorgpersoneel de medicijnvoorraad bekijken en een levering aanvragen. Bij een aanvraag kiest de gebruiker een bestemming en geeft die per medicijn het gewenste aantal op. Gebruikers met de rol `staff` kunnen de voorraad ook aanvullen. De aanvragen en voorraad worden opgeslagen in MySQL. 

## Onderdelen

- [`webapp/`](webapp/) bevat de webpagina en de FastAPI-server.
- [`database/`](database/) bevat het MySQL-schema en de testgegevens.
- [`authentik/`](authentik/) bevat de Docker Compose-configuratie voor het inloggen via Authentik.


