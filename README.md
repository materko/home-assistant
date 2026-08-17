# Home Assistant — konfigurácia

Verzionovaná konfigurácia domácej inštancie Home Assistant.
Repozitár sa aktualizuje **automaticky**, denne o 04:30.

- **Core** 2026.8.2 · **HA OS** 18.2 · **Supervisor** 2026.07.5
- Lovelace v `storage` režime (12 dashboardov, 13 resources)
- 13 add-onov, 53 config entries, 40 HACS balíkov
- 2 poschodia / 12 miestností

## Ako to funguje

Export robí add-on [Git Exporter](https://github.com/Poeschl-HomeAssistant-Addons/git-exporter)
(v1.17.1), ktorý beží priamo v Home Assistant. Add-on je typu „spusti a skonči",
takže ho štartuje automatizácia **„Git Exporter - denny export konfiguracie"**
každý deň o 04:30. Pri každom behu spraví commit a push.

Add-on má vstavanú kontrolu tajomstiev — ak nájde heslo v plaintexte,
commit **zastaví**. To je funkcia, nie chyba.

### Čo generuje add-on

| Cesta | Obsah |
|---|---|
| `config/` | `configuration.yaml`, `automations.yaml`, `scripts.yaml`, `scenes.yaml`, `packages/`, `themes/`, `blueprints/` |
| `lovelace/` | všetkých 12 dashboardov zo `storage` režimu + resources |
| `addons/` | zoznam registrovaných add-on repozitárov |

### Čo add-on nevie a je tu doplnené ručne

| Cesta | Obsah |
|---|---|
| `registry/` | miestnosti a poschodia, helpery, osoby — žijú v `.storage`, add-on ich neexportuje |
| `inventory/` | add-ony s verziami, integrácie, HACS balíky vrátane vlastných forkov |
| `tools/ha_export.py` | záložný ručný exportér cez HA API (viď nižšie) |

Tieto súbory sú **snapshot k 17. 8. 2026** — add-on ich neprepisuje, takže po
väčších zmenách v HA ich treba obnoviť ručne.

## Čo tu zámerne NIE JE

- **`secrets.yaml`**, `secret.yaml`, `.env`, tokeny, heslá
- **`custom_components/`** a **`www/community/`** — kód spravovaný cez HACS.
  Sú to stovky MB a push kvôli nim padal na timeout. Zoznam je v `inventory/hacs.md`.
- **Databáza** `home-assistant_v2.db` (~656 MiB histórie)
- **`zigbee2mqtt/coordinator_backup.json`** — obsahuje sieťový kľúč Zigbee siete
- **`zigbee2mqtt/configuration.yaml`** — má MQTT heslo v plaintexte
- **ESPHome konfigurácie** — export je vypnutý, viď nižšie
- **Poverenia integrácií** — po obnove treba každú integráciu prepojiť znova

## Dva známe dlhy

**1. ESPHome export je vypnutý.** Súbor `atoms3-lite-ble-proxy-0effac.yaml` má OTA
heslo v plaintexte a kontrolór tajomstiev kvôli nemu zastavoval každý beh.
Oprava: v ESPHome Device Builder presunúť heslo do `secrets.yaml`

```yaml
# secrets.yaml
ota_password: "..."

# atoms3-lite-ble-proxy-0effac.yaml
password: !secret ota_password
```

Pri nezmenenej hodnote netreba zariadenie preflashovať. Potom v konfigurácii
add-onu prepnúť `export.esphome` späť na `true`.

**2. Zigbee2MQTT `configuration.yaml`** je vylúčený z rovnakého dôvodu.
Z2M má **inú** syntax než HA — súbor `secret.yaml` vedľa `configuration.yaml`:

```yaml
# configuration.yaml
mqtt:
  password: '!secret.yaml password'
```

Názov súboru vrátane prípony, kľúč za medzerou, úvodzovky povinné.
Po oprave odstrániť príslušný riadok z `exclude` v konfigurácii add-onu.

## Vzťah k plnej zálohe

| | Git (tento repo) | Plná záloha → Google Drive |
|---|---|---|
| Obsah | čitateľná konfigurácia | všetko vrátane tajomstiev a DB |
| Veľkosť | ~1 MB | ~785 MB |
| Načo | história zmien, diff | disaster recovery |

Automatická záloha beží denne o 5:16 do `hassio.local` + Google Drive, retencia 3 kópie.
Zigbee sieť (`coordinator_backup.json`) je **len** v nej — bez nej sa všetky Zigbee
zariadenia musia párovať odznova.

> **Šifrovací kľúč záloh** nie je v tomto repe a ani tu byť nesmie.
> Bez neho sú zálohy v Google Drive nepoužiteľné — patrí do password manažéra.

## Záložný ručný export

`tools/ha_export.py` vytiahne cez HA API to, čo add-on nevie — registre, helpery,
osoby. Potrebuje `.env` v koreni repa (je v `.gitignore`):

```
HA_URL=http://192.168.68.55:8123
HA_TOKEN=<long-lived access token>
```

```bash
pip install pyyaml websocket-client
python tools/ha_export.py
```

## Poznámka o obsahu

Repo obsahuje interné IP adresy, ID zariadení, MAC adresy a mená členov domácnosti.
Kontrola IP adries je v add-one **vypnutá**, lebo by inak zhodila každý beh.
Heslá ani tokeny tu nie sú — **drž tento repozitár privátny**.
