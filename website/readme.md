# Website

Healthcare staff can use the MaterialenBuddy web app to check medication stock and request a delivery. To request a delivery, users choose a destination and enter the quantity needed for each medication. Users with the `staff` role can also replenish stock. Delivery requests and stock levels are stored in MySQL.

## Components

- [`webapp/`](webapp/) contains the web page and FastAPI server.
- [`database/`](database/) contains the MySQL schema and test data.
- [`authentik/`](authentik/) contains the Docker Compose configuration for signing in with Authentik.


