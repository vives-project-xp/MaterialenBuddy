# Authentik: een persoon toevoegen (handleiding voor dummies)

Hier lees je stap voor stap hoe je zelf een nieuwe persoon (gebruiker) toevoegt aan jullie
authentik-installatie, op twee manieren:

1. **Gewone gebruiker** — mag inloggen op de webapp, maar mag niets administratieven.
2. **Staff** — mag bovenop die webapp-toegang ook de voorraad/beheerfuncties gebruiken.
3. **authentik-admin** — mag ook het authentik-beheerpaneel openen en zelf mensen toevoegen.

> Dit werkt in jullie setup op de school-VM (`http://10.20.233.15:9000`). Zet je webapp
> later op een andere URL? Dan wordt het de URL waar jullie authentik live staat, de
> stappen zijn identiek.

---

## 0. Waar begin ik?

Jullie authentik draait op:

- Beheerpaneel (admin UI): `http://10.20.233.15:9000/if/admin/`
- Inlog-pagina: `http://10.20.233.15:9000/`

Om iemand toe te voegen heb je iemand nodig die **al** in de groep `authentik Admins` zit
(zoals `akadmin`). Een gewone gebruiker kan dit niet zelf.

**Inloggen in het beheerpaneel:**

1. Ga naar `http://10.20.233.15:9000/if/admin/`
2. Log in met een account dat in de groep `authentik Admins` zit (bijv. `akadmin`).
3. Je ziet nu het dashboard van authentik.



## 1. Een gewone gebruiker toevoegen

Dit is de basis. Elke persoon die op de webapp mag inloggen heeft dit nodig.

1. In het authentik-beheerpaneel: klik links in het menu op **Directory**.
2. Klik op **Users** (je ziet nu de lijst met alle gebruikers).
3. Bovenin de lijst klik je op **New user** (blauwe knop).
4. Vul in het venster:
   - **Gebruiksnaam**: de volledige naam van de persoon (bijv. `Jens Peeters`).
     - Dit mag niet dubbel zijn met een bestaande username.
   - Vink **Understand the implications of creating the user without setting a password** NIET aan
     als je meteen een wachtwoord wilt zetten (zie stap 5).
   - Klik **Save**.
5. De gebruiker staat nu in de lijst. Klik op de username om het profiel open te doen.
6. Scroll naar beneden naar de sectie **Password**:
   - Klik **Wachtwoord instellen** (of vink aan dat je het wachtwoord nu wilt instellen).
   - Vul een tijdelijk wachtwoord in (voldoet aan: minimaal 10 tekens, letters + cijfers +
     speciaal tekens, mag geen woord uit woordenlijst zijn).
   - Klik **Save**.
7. Geef het tijdelijk wachtwoord aan de persoon. Bij de eerste login op de webapp wordt die
   gevraagd om het te wijzigen (standaard gedrag van authentik).

**Klaar.** Deze persoon kan nu inloggen op `http://10.20.233.15:8000/auth/login` en ziet de
gewone voorraadlijst, maar **geen** knoppen voor aanvullen/uitfaseren.

---

## 2. Een staff-lid toevoegen

Staff is een gebruiker mét bijkomende rechten in de webapp (voorraad aanvullen, medicijnen
toevoegen/uitfaseren). Jullie webapp herkent staff op twee manieren:

- Het `staff: true` claim dat authentik toevoegt bij login.
- Of een groep genaamd `staff` in de token.

Beide mechanismes werken in jullie setup (de scope-expressie keert `staff: true` terug voor
leden van `authentik Admins` **én** de groep `staff`). Het meest expliciete en duidelijkste
is de groep `staff` toevoegen.

**Stappen (na het toevoegen van de gebruiker uit sectie 1):**

1. Ga terug naar **Directory → Users**.
2. Klik op de username van de persoon die je net toevoegde.
3. In het gebruikersprofiel zoek je de sectie **Groups**.
4. Klik **Add Group**.
5. Zoek de groep **`staff`** in de lijst en selecteer haar.
6. Klik **Save**.

> 💡 Je kunt dit ook omgekeerd doen: ga naar **Directory → Groups**, open de groep `staff`,
> tab **Users**, en klik daar **Add to existing group**.

**Klaar.** Wanneer de persoon de volgende keer inlogt op de webapp, ziet die de staff-knoppen.

⚠️ De persoon moet **uitloggen en opnieuw inloggen** op de webapp om de verandering te zien.
Een sessie die al gelogen is gebruikt de oude claims.

---

## 3. Een authentik-admin toevoegen

Een authentik-admin mag het beheerpaneel openen, gebruikers aanmaken, groepen beheren,
providers, flows, mappen, … Kort gezegd: alles wat in het `if/admin/` paneel staat.

In jullie installatie is dit de groep **`authentik Admins`** (let op hoofdletters en spatie —
dat is de exacte naam die authentik bij een frisse installatie maakt).

**Stappen (na het toevoegen van de gebruiker uit sectie 1):**

1. Ga naar **Directory → Groups**.
2. Zoek de groep **`authentik Admins`** en klik erop open.
3. Tab **Users** bovenin.
4. Klik **Add to existing group**.
5. Zoek de username van de persoon, selecteer, **Save**.

**Of via het gebruikersprofiel:** profiel openen → sectie **Groups** → **Add Group** →
`authentik Admins` → **Save**.

**Gevolgen:**

- Deze persoon mag `http://10.20.233.15:9000/if/admin/` openen en zelf nieuwe gebruikers
  toevoegen (zoals je zelf doet met deze handleiding).
- Deze persoon krijgt automatisch ook `staff: true` in de webapp (zie de scope-expressie),
  dus die heeft ook alle staff-knoppen.

⚠️ Dit is een **grote macht**. Doe dit alleen met mensen die je volledig vertrouwt.

---

## 4. Het hele plaatje in één oogopslag

| Rol | Wat die mag | Hoe je het doet |
|---|---|---|
| Gewone gebruiker | Alleen inloggen en voorraad bekijken | Alleen gebruiker aanmaken (sectie 1) |
| Staff | Bovenop: voorraad aanvullen, medicijnen beheren | Gebruiker + groep `staff` (sectie 2) |
| authentik-admin | Bovenop: beheerpaneel, zelf mensen toevoegen | Gebruiker + groep `authentik Admins` (sectie 3) |

Je kunt ook combinaties: iemand die zowel in `staff` als in `authentik Admins` zit heeft
beide rechten. Iemand die in géén van beide zit, is gewoon een gebruiker.



