# Webapp ↔ Raspberry Pi: communicatie-idee

Kort idee over hoe de webapp en de Raspberry Pi in de robot met elkaar communiceren.
**Al de robot-logica (ROS, navigatie, waar hij precies moet rijden) zit in de Pi zelf.**
Wij bouwen hier alleen de verbinding: de webapp zegt *"ga naar lokaal X"*, de Pi doet
het en meldt terug wat er gebeurt. De Pi behandelen we dus als een **zwarte doos**.

---

## 1. Doel

Nu draait de levering in de webapp in een **simulatie** (na 5 seconden "aangekomen").
Het doel: de webapp doorgeven naar welk lokaal de robot moet, en de echte status
terugkrijgen, zodat we de simulatie weglaten.

```
webapp ── "ga naar B302" ──▶  Raspberry Pi  ──(eigen ROS-logica)──▶ robot
webapp ◀── "onderweg / aangekomen" ──  Raspberry Pi
```

De webapp doet **niet** met ROS. De Pi doet **niet** met de database. Ze praten
alleen met elkaar via een klein REST-protocol.

---

## 2. Wat er al is

- **Webapp (FastAPI/Docker):** heeft al een `leveringen`-tabel met een `status`-ENUM die
  precies op de flow past: `aangevraagd`, `onderweg`, `aangekomen`, `geannuleerd`, `fout`.
  Er is al een `GET /leveringen/{id}` om de status op te halen.
- **De Pi's** hebben vaste namen via **Tailscale** (al geïnstalleerd, "privately connected
  via tailscale"). Bijv. `robot1` = `10.10.216.115`, `robot2` = `10.10.235.148`.

---

## 3. Over welk netwerk?

De webapp komt te draaien op een **VM die online staat**; de Pi zit in de robot op het
lokale lab-netwerk. De twee zitten dus **niet in hetzelfde netwerk** — de VM kan de Pi op
het lokale netwerk niet zomaar bereiken.

Daarom is **Tailscale hier de basis**, niet alleen een keuze:

- VM én Pi in dezelfde private mesh → ze zien elkaar als buren, onafhankelijk van waar de
  VM fysiek staat.
- Geen firewall-poorten openen op de VM nodig; stabiele namen (bijv. `robot1.<tailscale>`).
- Werkt óf de VM online/cloud staat óf lokaal — het protocol blijft identiek.
- Tailscale staat op de Pi's al; de VM krijgt hem er een keer bij.

> Kanttekening: staat de Pi of de VM achter een strikte NAT waar P2P niet lukt, dan
> relayt Tailscale via diens servers. Werkt nog steeds, alleen iets traag — één keer testen is genoeg.

Het adres van de Pi en van de VM verandert hiermee van lokaal IP naar hun Tailscale-naam;
de rest van het idee (protocol, push, status) blijft ongewijzigd.

---

## 4. Hoe communiceren ze (het protocol)

We gebruiken **REST over HTTP** — dezelfde technologie als de webapp zelf. Geen extra
infrastructuur, geen MQTT-broker, geen WebSocket.

Twee kleine endpoints, allebei over HTTP:

**a) Webapp → Pi: de opdracht versturen**
De webapp POST een opdracht naar de Pi (via diens Tailscale-naam):
```
POST https://robot1.<tailscale>:8000/opdracht
{ "levering_id": 12, "bestemming": "B302" }
```
Daarna is de Pi aan het werk (zijn eigen ROS-logica).

**b) Pi → webapp: de status terugsturen**
Zodra de robot onderweg is / aangekomen is / een fout geeft, POST de Pi de status terug
(via de Tailscale-naam van de VM):
```
PUT https://<vm>.<tailscale>/leveringen/12/status
{ "status": "onderweg" }
```
De webapp updatet de `leveringen`-rij; de frontend toont daarna de echte status
(i.p.v. de 5-seconden-timer).

> Beide richtingen zijn dus een simpel HTTP-call. De enige nieuwe code in de webapp is
> die ene status-endpoint (`PUT /leveringen/{id}/status`) — de `status`-waarden zijn er al.

---

## 5. Wie spreekt wie aan: push of poll?

Een keuze: wie zet de eerste stap bij de opdracht?

- **Push (aangenaan) ✅** — de webapp stuurt de opdracht direct naar de Pi op het moment
  dat de levering wordt aangevraagd. Eén extra HTTP-call, direct resultaat.
- **Polling** — de Pi checkt elke paar seconden de webapp op nieuwe leveringen. Simpel en
  robuust, maar met een klein vertraging-venster.

**Aanbeveling: push.** De webapp heeft de levering net aangemaakt; die stuurt dan meteen
`POST /opdracht` naar de Pi. Als de Pi even niet bereikbaar is, blijft de levering in de
DB op status `aangevraagd` en kan de webapp de opdracht later alsnog (her)sturen — dat is
je ingebouwde "queue". De **status** stroomt in beide richtingen dezelfde manier terug:
de Pi POST het naar `PUT /leveringen/{id}/status`.

---

## 6. Status-flow (past op bestaande `leveringen.status`)

| Stap | Wie | Actie | `status` |
|:--|:--|:--|:--|
| 1 | Personeel | Vraagt levering aan in webapp | `aangevraagd` |
| 2 | Webapp | Slaat op + stuurt `POST /opdracht` naar de Pi | `aangevraagd` |
| 3 | Pi | Begint de robot te sturen, meldt `onderweg` | `onderweg` |
| 4 | Pi | Robot arriveert, meldt `aangekomen` | `aangekomen` |
| 4b | Pi | Fout/timeout, meldt `fout` | `fout` |

Alleen de **webapp** wijst hierin iets toe (stap 1); de overige statussen stuurt de **Pi**
terug. De frontend hoeft alleen nog de echte status op te halen i.p.v. te simuleren.

---

## 7. Veiligheid (machine-to-machine)

De bestaande login (Authentik/OIDC) is voor **mensen in een browser**. De Pi is een
**machine** en heeft geen sessie. Eenvoudige oplossing:

- De Pi krijgt een eigen **API-key** (een geheime string, bijv. in een `.env` op de Pi).
- Die stuurt de Pi mee in elke call: header `X-API-Key: <sleutel>`.
- De webapp checkt op de machine-to-machine-endpoints (status) of die key klopt.

**Belangrijker nu dat de webapp online staat** (VM): vóór draaide de webapp lokaal
(alleen bereikbaar op localhost). Nu staat hij bereikbaar voor iedereen →

- de **API-key** wordt echt essentieel; de `status`-endpoint moet **niet** open zonder die key.
- ga over op **HTTPS/TLS** in plaats van puur HTTP (bijv. reverse proxy + certificaat voor de
  VM; de Pi praat dan met `https://<vm-tailscale>`).
- de Pi spreekt de VM aan via diens **Tailscale-naam** (privé mesh), niet via een publiek IP.

---

## 8. Wat er in de webapp verandert (korte lijst)

1. Eén nieuw endpoint: `PUT /leveringen/{id}/status` (alleen met geldige API-key).
2. Bij `POST /leveringen`: na het opslaan, een `POST /opdracht` naar de Pi
   (via diens Tailscale-naam), met `levering_id` + `bestemming`.
3. Frontend: de 5-seconden-simulatie vervangen door het ophalen van de echte status.

Alles andere (voorraad, medicijnen, auth voor mensen) blijft zoals het is.

---

## 9. Openstaande vragen

- **Eén robot of beide tegelijk?** Beïnvloedt enkel hoe de webapp de juiste Pi aanspreekt
  (bijv. robot1 voor de ene locatie, robot2 voor de andere).
- **Wat is "aangekomen"?** Alleen waypoint bereikt, of ook nog een extra stap na aankomst?
- **Auth:** API-key (boven) of client-credentials via Authentik?

---

## 10. Samenvatting

- De Pi is een **zwarte doos** die zijn eigen ROS-logica draait.
- **Netwerk:** webapp staat op een **online VM**, Pi op het lokale net → **Tailscale** verbindt
  ze privé en stabiel; verkeer over **HTTPS**.
- **Protocol:** REST/HTTP in twee richtingen:
  - webapp → Pi: `POST /opdracht` (welke bestemming)
  - Pi → webapp: `PUT /leveringen/{id}/status` (onderweg / aangekomen / fout)
- **Wie start:** push — de webapp stuurt de opdracht direct; status stroomt terug.
- **Auth:** API-key op de machine-to-machine-calls.
