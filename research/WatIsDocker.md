# Docker – Explanation & Documentation

> **Language / Taal**
>
> 🇬🇧 This document is available in English and Dutch. Both versions contain the same information.
>
> 🇳🇱 Dit document is beschikbaar in het Engels en Nederlands. Beide versies bevatten dezelfde informatie.

---

# 🇬🇧 ENGLISH VERSION

> This is the English version of the document. A Dutch translation is available below.

## What is Docker, how is it structured, and how does it work?

This document explains what Docker is, how it works, and what it can be used for.

### What is Docker and how does it work?

Docker is a program that allows you to run other programs in separate, isolated environments. These environments are called **containers**.

Imagine you have created a website and want to make it accessible to other people. To do this, you need a computer running a web server. A web server, such as Nginx, is a program that sends your website to a visitor's browser.

Normally, you install the web server directly on the computer. With Docker, you place the web server and optionally your website files inside a container. This container runs on the computer but is largely isolated from the rest of the system.

### How does a Docker container work?

You can think of a container as a separate workspace on a computer. This workspace contains the programs, files, and settings needed to run a particular application.

A container is somewhat similar to a small virtual computer, but there is an important difference: a container does not have its own operating system kernel. Instead, it uses the kernel of the system on which Docker runs. This makes containers generally lighter and faster to start than full virtual machines (VMs).

Docker consists of three important components:

- **Docker:** the software that creates, starts, stops, and manages containers.
- **Docker image:** a package containing the software, files, and default settings needed to create a container.
- **Docker container:** a running instance of a Docker image.

You can compare an image to a blueprint. Docker uses that blueprint to create a container.

### Why do we use Docker?

**The first advantage: isolation**

A program running inside a container is largely separated from other programs. This reduces the chance of different programs interfering with each other. However, this isolation is not absolute: containers can access files and parts of the host computer if you allow them to.

**The second advantage: portability**

Software becomes easier to move between computers. If you want to run a website on another computer, you do not need to manually reinstall all the programs. You install Docker and use the same images and configuration files to recreate the environment.

**The third advantage: easier maintenance**

Imagine you want to update a website. You can create a new image and replace the existing container. You do not need to restart the entire computer. Other containers can continue running normally.

### What about files and data?

Containers are designed to be easily replaced. Files stored only inside a container can be lost when that container is removed.

That is why Docker provides **volumes**. These are storage locations where important data can be preserved, even when a container is replaced. This is particularly important for databases containing orders or other information.

### What is Docker Compose?

When you need multiple containers, for example one for a website and another for a database, you can use **Docker Compose**.

With Docker Compose, you describe which containers are needed, which software they use, and how they communicate with each other in a single configuration file. You can then start and manage these containers together.

### Summary

Docker allows programs to run in separate, largely isolated environments. This makes software easier to install, move, maintain, and replace.

Docker does not automatically make your programs better or faster. Its main purpose is to make the environments in which they run easier to manage.

---

# 🇳🇱 NEDERLANDSE VERSIE

> **Vanaf hier begint de Nederlandse vertaling van de bovenstaande Engelse tekst.**
>
> De inhoud van beide versies is hetzelfde.

---

## Wat is Docker, hoe zit het in elkaar en hoe werkt het?

In dit document wordt uitgelegd wat Docker is, hoe het werkt en waarvoor je het kunt gebruiken.

### Wat is Docker en hoe werkt het?

Docker is een programma waarmee je andere programma's in aparte, afgeschermde omgevingen kunt laten draaien. Die omgevingen noemen we **containers**.

Stel dat je een website hebt gemaakt en die beschikbaar wilt maken voor andere mensen. Daarvoor heb je een computer nodig waarop een webserver draait. Een webserver, zoals Nginx, is een programma dat jouw website doorstuurt naar de browser van een bezoeker.

Normaal installeer je die webserver rechtstreeks op de computer. Met Docker plaats je de webserver en eventueel je websitebestanden in een container. Die container draait op de computer, maar is grotendeels afgeschermd van de rest van het systeem.

### Hoe werkt een Docker-container?

Je kunt een container vergelijken met een aparte werkruimte op een computer. In die werkruimte zitten de programma's, bestanden en instellingen die nodig zijn om een bepaalde toepassing uit te voeren.

Een container lijkt daardoor op een kleine virtuele computer, maar er is een belangrijk verschil: een container heeft geen eigen besturingssysteemkernel. Hij gebruikt de kernel van het systeem waarop Docker draait. Daardoor zijn containers meestal lichter en sneller op te starten dan volledige virtuele machines (VM's).

Docker werkt met drie belangrijke onderdelen:

- **Docker:** het programma dat containers aanmaakt, start, stopt en beheert.
- **Docker-image:** een pakket met de software, bestanden en standaardinstellingen die nodig zijn om een container te maken.
- **Docker-container:** een draaiende instantie van een Docker-image.

Een image kun je vergelijken met een bouwplan. Docker gebruikt dat bouwplan om een container te maken.

### Waarom gebruiken we Docker?

**Het eerste voordeel: isolatie**

Een programma in een container draait grotendeels gescheiden van andere programma's. Daardoor is de kans kleiner dat verschillende programma's elkaar beïnvloeden. Die isolatie is niet absoluut: containers kunnen toegang krijgen tot bestanden en onderdelen van de computer als je dat toestaat.

**Een tweede voordeel: verplaatsbaarheid**

Software is gemakkelijker te verplaatsen. Als je een website op een andere computer wilt draaien, hoef je niet opnieuw alle programma's handmatig te installeren. Je installeert Docker en gebruikt dezelfde images en configuratiebestanden om de omgeving opnieuw op te bouwen.

**Een derde voordeel: eenvoudiger onderhoud**

Stel dat je een website wilt updaten. Dan kun je een nieuwe image maken en de bestaande container vervangen. Je hoeft daarvoor niet de volledige computer opnieuw op te starten. Andere containers kunnen gewoon blijven draaien.

### Hoe zit het met bestanden en gegevens?

Containers zijn bedoeld om gemakkelijk vervangen te worden. Bestanden die alleen in een container opgeslagen zijn, kunnen verloren gaan wanneer je die container verwijdert.

Daarom gebruikt Docker onder andere **volumes**. Dat zijn opslagplaatsen waarin belangrijke gegevens bewaard blijven, ook wanneer een container vervangen wordt. Dit is bijvoorbeeld belangrijk voor een database met bestellingen.

### Wat is Docker Compose?

Wanneer je meerdere containers nodig hebt, bijvoorbeeld één voor een website en één voor een database, kun je **Docker Compose** gebruiken.

Met Docker Compose beschrijf je in één configuratiebestand welke containers nodig zijn, welke software ze gebruiken en hoe ze met elkaar communiceren. Daarna kun je die containers samen opstarten en beheren.

### Samengevat

Docker zorgt ervoor dat je programma's in afzonderlijke, grotendeels geïsoleerde omgevingen kunt uitvoeren. Hierdoor kun je software eenvoudiger installeren, verplaatsen, onderhouden en vervangen.

Docker maakt je programma's niet automatisch beter of sneller, maar maakt vooral de omgeving waarin ze draaien gemakkelijker te beheren.