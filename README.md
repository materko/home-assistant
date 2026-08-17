# Home Assistant blueprint — Svetlo na pohyb

Blueprint pre Home Assistant, ktorý jednou automatizáciou nahradí obvyklú trojicu
*zapni pri pohybe* / *zhasni po odchode* / *poistka po X minútach* pre jednu miestnosť.

## Import

[![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmaterko%2Fhome-assistant%2Fblob%2Fmain%2Fsvetlo_pohyb.yaml)

Alebo ručne: **Settings → Automations & Scenes → Blueprints → Import Blueprint** a vlož URL súboru `svetlo_pohyb.yaml`.

## Čo rieši

Pri stavbe „svetlo na pohyb" cez UI zvyčajne vzniknú tri automatizácie na miestnosť.
Pri viacerých miestnostiach sa kopírujú a rozchádzajú — oprava logiky sa musí spraviť
všade zvlášť. Tento blueprint drží logiku na jednom mieste.

Zvláda aj prípady, ktoré základný `motion_light` nepokrýva:

- **PIR aj occupancy naraz** — PIR reaguje rýchlo, occupancy (mmWave) drží svetlo
  zapnuté, kým v miestnosti niekto naozaj je. Occupancy je voliteľné.
- **Senzory, ktoré nehlásia `on`/`off`** — napr. `motion_state` s hodnotami
  `large` / `small` / `none`. Stavy sú konfigurovateľné.
- **Rôzne sady svetiel podľa svetelnosti** — pod hranicou luxu sa zapne hlavná sada,
  nad ňou iná (typicky slabšie svetlo pri zrkadle namiesto stropného).
- **Nočný režim** — v zadanom časovom okne sa zapne tretia sada.
- **Poistka** — ak svetlo svieti dlhšie než limit a nikto tam nie je, zhasne.
  Chráni pred senzorom zaseknutým v stave „obsadené".

## Vstupy

| Vstup | Povinné | Default | Poznámka |
|---|---|---|---|
| `senzory_pohybu` | áno | — | viac naraz; `binary_sensor` aj `sensor` |
| `senzory_pritomnosti` | nie | `[]` | prázdne = vypína sa podľa PIR |
| `stavy_pohybu` | nie | `on`, `large`, `small` | čo znamená pohyb |
| `stavy_pokoja` | nie | `off`, `none` | čo znamená pokoj |
| `svetla_hlavne` | áno | — | viac naraz, `switch` aj `light` |
| `svetla_nocne` | nie | `[]` | prázdne = v noci sa nezapne nič |
| `svetla_pri_svetle` | nie | `[]` | prázdne = pri dostatku svetla sa nezapne nič |
| `cakanie_po_odchode` | nie | 30 s | pokoj na všetkých senzoroch pred zhasnutím |
| `max_cas_svietenia` | nie | 10 min | poistka |
| `potvrdenie_okno` | nie | `0` = vypnuté | čakanie na potvrdenie prítomnosti, viď nižšie |
| `potvrdenie_pir_off` | nie | 1 min | počas okna: ako dlho musí PIR mlčať |
| `nocny_rezim_zapnuty` | nie | `false` | |
| `nocny_od` / `nocny_do` | nie | 23:00 / 06:00 | |
| `lux_senzory` | nie | `[]` | viac senzorov → berie sa najnižšia hodnota |
| `lux_limit` | nie | 1000 lx | hranica medzi tmou a svetlom |

## Ako sa vyberá sada svetiel

Pri pohybe sa vyberie **práve jedna** sada, v tomto poradí:

1. **nočná** — ak je nočný režim zapnutý a je jeho čas
2. **pri svetle** — ak lux senzor hlási viac než limit
3. **hlavná** — inak

Vypína sa vždy zjednotenie všetkých troch sád, takže nezostane svietiť nič.

Bez lux senzorov sa vždy vyhodnocuje ako tma. Ak sú lux senzory nedostupné, správa sa
to rovnako — radšej zapnúť než nechať človeka v tme.

## Potvrdzovacie okno (voliteľné)

PIR reaguje aj na niekoho, kto len prejde okolo dverí. Ak ti to vadí, nastav
`potvrdenie_okno` napríklad na `1:45`. Po zapnutí svetla sa potom čaká, či occupancy
senzor potvrdí, že v miestnosti niekto naozaj je:

- **potvrdí sa** → svetlo svieti ďalej, zhasne až bežným spôsobom po odchode
- **PIR stíchne** na `potvrdenie_pir_off` → berie sa to ako falošné zopnutie, zhasne hneď
- **vyprší okno** bez potvrdenia → to isté

Pred zhasnutím sa vždy ešte overí, že žiadny senzor nehlási prítomnosť.

Dve poistky proti nechcenému zhasnutiu:

- funguje len ak sú vyplnené **senzory prítomnosti** — so samotným PIR nie je čo potvrdzovať
- uplatní sa len keď svetlo rozsvietila **táto automatizácia**. Ak už svietilo
  (napr. si ho zapol ručne), potvrdzovanie sa preskočí a nikto ti ho nezhasne.

Pri `0` (default) sa celý blok preskočí a blueprint sa správa ako predtým.

## Kedy sa zhasína

Buď keď sú **všetky** senzory (PIR aj occupancy) v pokoji po dobu `cakanie_po_odchode`,
alebo keď poistka zistí, že svetlo svieti dlhšie než `max_cas_svietenia` a nikto tam nie je.

Blueprint neposiela príkaz, keď už je stav správny — nezapína to, čo svieti, a nevypína
to, čo je zhasnuté. Pri PIR senzoroch, ktoré pulzujú často, to ušetrí veľa zbytočnej
prevádzky na Zigbee sieti.

## Poznámky

- Používa výhradne `entity_id`, žiadne `device_id` — nerozbije sa pri prepárovaní zariadenia.
- `mode: restart`.
- Voliteľné vstupy s prázdnym zoznamom sú v poriadku — príslušný trigger sa jednoducho
  nikdy nespustí.

## Licencia

MIT
