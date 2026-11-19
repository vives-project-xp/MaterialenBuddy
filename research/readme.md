# Onderzoek MaterialenBuddy

In deze map verzamelen we het onderzoek, de lokale tests en de prototypes voor MaterialenBuddy. Hier kan je terugvinden welke technieken we hebben onderzocht, hoe de testopstellingen werken en welke ideeën we verder willen uitproberen.

## Robot en navigatie

Hier onderzoeken we hoe de iRobot Create 3 een bestemming kan bereiken en hoe de website via een Raspberry Pi een opdracht kan doorgeven. Je vindt er ook de handleiding voor ROS 2 en de lokale Bluetooth-tests.

- [ROS 2 Jazzy installeren](robot/ros2-installatie.md) en [ROS 2-configuratie (PDF)](robot/ROS2_config.pdf)
- [Bluetooth-navigatietest uitvoeren](robot/bluetooth-navigatietest/readme.md)
- [Eerste Bluetooth-verbinding met de Create 3 testen](robot/testverbinding.md)
- [Communicatie tussen webapp, Raspberry Pi en robot](robot/raspberry-pi-robot-verbinding.md) en [Raspberry Pi-notities](robot/Raspberry%27s)
- [Lokalisatie- en navigatiemethoden](robot/Navigation%20Methods.md) en [Methodenoverzicht (PDF)](robot/Materialenbuddy-Methods-EN.pdf)

## Authentik-logintest

Met een eenvoudige HTML-testwebsite hebben we getest hoe Authentik het inloggen en de toegang voor verschillende gebruikers regelt. De testwebsite, loginserver, screenshots en het verslag staan bij elkaar.

- [Verslag van de oorspronkelijke Authentik-test](authentik-logintest/authentik_test_documentatie.md)
- [HTML-testwebsite](authentik-logintest/authentik-test/README.md) en [bijbehorende Authentik-server](authentik-logintest/authentik-server/README.md)

## Docker en prototype

De Docker-documentatie legt uit hoe we onderdelen in containers draaien. Het websiteprototype laat zien hoe de webapp, de database en Authentik kunnen samenwerken.

- [Wat is Docker?](docker/WatIsDocker.md)
- [MaterialenBuddy-websiteprototype](website%20materialenbuddy/readme.md)
- [Projectideeën](idee%C3%ABn.md)
