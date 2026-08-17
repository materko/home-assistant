# Home Assistant — konfigurácia

Verzionovaná konfigurácia domácej inštancie Home Assistant.

- **Core** 2026.8.2 · **HA OS** 18.2 · **Supervisor** 2026.07.5
- Lovelace beží v `storage` režime (12 dashboardov, 13 resources)
- 12 add-onov, 53 config entries, 40 HACS balíkov
- 2 poschodia / 12 miestností

## Čo tu je

| Priečinok | Obsah |
|---|---|
| `automations/` | 43 automatizácií — formát zhodný s `/config/automations.yaml` |
| `scripts/` | 14 skriptov — formát zhodný s `/config/scripts.yaml` |
| `dashboards/` | Lovelace dashboardy zo `storage` režimu |
| `registry/` | Miestnosti, poschodia, helpery, osoby, Lovelace resources |
| `inventory/` | Zoznam add-onov, integrácií a HACS balíkov |

## Ako to vzniklo

Táto inštancia drží prakticky celú konfiguráciu v UI, čiže v `.storage/` — nie
v YAML súboroch. `.storage/` sa **nedá commitovať**, lebo v tom istom priečinku sú
`auth`, hashe hesiel a API tokeny integrácií. Export preto vytiahol logickú
konfiguráciu cez API a zapísal ju do čitateľného YAML.

Export je **snapshot**, nie živá synchronizácia. Po väčších zmenách v HA ho treba
zopakovať.

## Čo tu zámerne NIE JE

- **`secrets.yaml`**, `.storage/`, tokeny, heslá, API kľúče
- **Databáza** `home-assistant_v2.db` (~656 MiB histórie)
- **Poverenia integrácií** — po obnove treba každú integráciu prepojiť znova
- **Zigbee sieť** (Zigbee2MQTT `coordinator_backup.json`, `database.db`) — bez nej
  sa všetky Zigbee zariadenia musia párovať odznova. Je súčasťou plnej zálohy.
- **ESPHome firmvéry a YAML** zariadení
- Plné zálohy (`.tar`) — tie idú do Google Drive, nie sem

## Vzťah k plnej zálohe

Git a Google Drive riešia dve rôzne veci:

| | Git (tento repo) | Plná záloha → Google Drive |
|---|---|---|
| Obsah | čitateľná konfigurácia | všetko vrátane tajomstiev a DB |
| Veľkosť | kilobajty | ~785 MB |
| Načo | história zmien, diff, „čo som zmenil" | disaster recovery |

Automatická záloha beží denne o 5:16 do `hassio.local` + Google Drive, retencia 3 kópie.

> **Šifrovací kľúč záloh** nie je v tomto repe a ani tu byť nesmie.
> Bez neho sú zálohy v Google Drive nepoužiteľné — patrí do password manažéra.

## Obnova z tohto repa

Poradie je dôležité:

1. Čerstvá inštalácia HA + prihlásenie
2. Add-ony podľa `inventory/addons.md`
3. HACS + balíky podľa `inventory/hacs.md` (forky `materko/*` ako custom repository)
4. Integrácie podľa `inventory/integrations.md` — každú prepojiť ručne
5. Miestnosti a poschodia podľa `registry/areas_floors.yaml`
6. Helpery podľa `registry/helpers.yaml`
7. `automations/automations.yaml` → `/config/automations.yaml`, to isté pre skripty
8. Dashboardy z `dashboards/` naimportovať cez raw editor

Kroky 4–6 sú ručné. Preto je toto doplnok k plnej zálohe, nie jej náhrada.

## Poznámka o obsahu

Repo obsahuje interné IP adresy, ID zariadení, MAC adresy, mená členov domácnosti
a jeden IR kód. Žiadne heslá ani tokeny — ale **drž tento repozitár privátny**.
