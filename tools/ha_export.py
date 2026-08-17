#!/usr/bin/env python3
"""Export konfiguracie z Home Assistant do tohto repozitara.

Vytiahne cez HA API vsetko, co zije v .storage (UI konfiguracia), a zapise
to ako citatelny YAML. Spusti po kazdej vacsej zmene v HA a commitni vysledok.

Pouzitie:
    pip install pyyaml websocket-client
    # vytvor .env vedla tohto suboru (je v .gitignore):
    #   HA_URL=http://192.168.68.55:8123
    #   HA_TOKEN=<long-lived access token z Profil -> Bezpecnost>
    python tools/ha_export.py

Token sa nikam necommituje - .env je ignorovany.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def die(msg: str) -> None:
    sys.exit(f"CHYBA: {msg}")


try:
    import yaml
except ImportError:
    die("chyba PyYAML  ->  pip install pyyaml")

try:
    import websocket  # websocket-client
except ImportError:
    die("chyba websocket-client  ->  pip install websocket-client")


# --------------------------------------------------------------------------
# konfiguracia
# --------------------------------------------------------------------------

def load_env() -> tuple[str, str]:
    for candidate in (REPO / ".env", Path.cwd() / ".env"):
        if not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    url = os.environ.get("HA_URL", "").rstrip("/")
    token = os.environ.get("HA_TOKEN", "")
    if not url or not token:
        die("chyba HA_URL alebo HA_TOKEN (nastav ich v .env alebo v prostredi)")
    return url, token


# --------------------------------------------------------------------------
# YAML vystup
# --------------------------------------------------------------------------

def _str_representer(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


yaml.add_representer(str, _str_representer)


def write_yaml(obj, path: Path, header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    buf.write(header.rstrip() + "\n\n")
    yaml.dump(obj, buf, allow_unicode=True, sort_keys=False,
              default_flow_style=False, width=120)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    print(f"  {path.relative_to(REPO)}")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", str(value).lower()).strip("-") or "dashboard"


# --------------------------------------------------------------------------
# HA klienti
# --------------------------------------------------------------------------

class Rest:
    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.headers = {"Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"}

    def get(self, path: str):
        req = urllib.request.Request(f"{self.url}{path}", headers=self.headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))


class Ws:
    """Minimalny synchronny klient nad HA WebSocket API."""

    def __init__(self, url: str, token: str) -> None:
        ws_url = url.replace("https://", "wss://").replace("http://", "ws://")
        self.conn = websocket.create_connection(f"{ws_url}/api/websocket", timeout=30)
        self._id = 0

        hello = json.loads(self.conn.recv())
        if hello.get("type") != "auth_required":
            die(f"necakana odpoved pri pripojeni: {hello.get('type')}")

        self.conn.send(json.dumps({"type": "auth", "access_token": token}))
        auth = json.loads(self.conn.recv())
        if auth.get("type") != "auth_ok":
            die("token odmietnuty (auth_invalid) - skontroluj HA_TOKEN")

    def cmd(self, type_: str, **kwargs):
        self._id += 1
        payload = {"id": self._id, "type": type_, **kwargs}
        self.conn.send(json.dumps(payload))
        while True:
            msg = json.loads(self.conn.recv())
            if msg.get("id") != self._id or msg.get("type") != "result":
                continue  # event alebo odpoved na iny prikaz
            if not msg.get("success"):
                err = (msg.get("error") or {}).get("message", "neznama chyba")
                raise RuntimeError(f"{type_}: {err}")
            return msg.get("result")

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass


# --------------------------------------------------------------------------
# jednotlive exporty
# --------------------------------------------------------------------------

def export_automations(rest: Rest, states: list[dict]) -> int:
    configs = []
    for st in states:
        if not st["entity_id"].startswith("automation."):
            continue
        unique_id = st.get("attributes", {}).get("id")
        if not unique_id:
            continue
        try:
            configs.append(rest.get(f"/api/config/automation/config/{unique_id}"))
        except Exception as exc:
            print(f"  ! preskocene {st['entity_id']}: {exc}")

    configs.sort(key=lambda c: c.get("alias", ""))
    write_yaml(configs, REPO / "automations" / "automations.yaml",
               "# Automatizacie - format zhodny s /config/automations.yaml\n"
               f"# Pocet: {len(configs)}")
    return len(configs)


def export_scripts(rest: Rest, states: list[dict]) -> int:
    configs = {}
    for st in states:
        if not st["entity_id"].startswith("script."):
            continue
        key = st["entity_id"].split(".", 1)[1]
        try:
            configs[key] = rest.get(f"/api/config/script/config/{key}")
        except Exception as exc:
            print(f"  ! preskocene {st['entity_id']}: {exc}")

    configs = dict(sorted(configs.items()))
    write_yaml(configs, REPO / "scripts" / "scripts.yaml",
               "# Skripty - format zhodny s /config/scripts.yaml\n"
               f"# Pocet: {len(configs)}")
    return len(configs)


def export_scenes(rest: Rest, states: list[dict]) -> int:
    configs = []
    for st in states:
        if not st["entity_id"].startswith("scene."):
            continue
        scene_id = st.get("attributes", {}).get("id")
        if not scene_id:
            continue
        try:
            configs.append(rest.get(f"/api/config/scene/config/{scene_id}"))
        except Exception as exc:
            print(f"  ! preskocene {st['entity_id']}: {exc}")

    if configs:
        write_yaml(configs, REPO / "scenes" / "scenes.yaml",
                   "# Sceny - format zhodny s /config/scenes.yaml\n"
                   f"# Pocet: {len(configs)}")
    return len(configs)


def export_dashboards(ws: Ws) -> int:
    out_dir = REPO / "dashboards"
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.yaml"):
        stale.unlink()

    # None = default dashboard (lovelace), zvysok podla url_path
    targets: list[tuple[str, str | None]] = [("default", None)]
    for board in ws.cmd("lovelace/dashboards/list") or []:
        targets.append((board.get("url_path") or board["id"], board.get("url_path")))

    count = 0
    for name, url_path in targets:
        try:
            config = ws.cmd("lovelace/config", url_path=url_path)
        except RuntimeError as exc:
            # dashboard v YAML rezime alebo bez ulozenej konfiguracie
            print(f"  ! {name}: {exc}")
            continue
        if config is None:
            continue
        write_yaml(config, out_dir / f"{slugify(name)}.yaml",
                   f"# Lovelace dashboard: {name}\n"
                   "# Storage rezim - export z .storage/lovelace.*")
        count += 1

    resources = ws.cmd("lovelace/resources") or []
    write_yaml({"resources": [{"url": r.get("url"), "type": r.get("type")}
                              for r in resources]},
               REPO / "registry" / "dashboard_resources.yaml",
               "# Lovelace resources (custom karty z HACS)")
    return count


def export_registries(ws: Ws) -> None:
    areas = ws.cmd("config/area_registry/list") or []
    floors = ws.cmd("config/floor_registry/list") or []
    by_floor: dict[str | None, list] = {}
    for area in areas:
        by_floor.setdefault(area.get("floor_id"), []).append(
            {"area_id": area["area_id"], "name": area.get("name"),
             "icon": area.get("icon")})

    write_yaml({"floors": [{"floor_id": f["floor_id"], "name": f.get("name"),
                            "level": f.get("level"),
                            "areas": by_floor.get(f["floor_id"], [])}
                           for f in sorted(floors, key=lambda f: (f.get("level") or 0))],
                "unassigned_areas": by_floor.get(None, [])},
               REPO / "registry" / "areas_floors.yaml",
               "# Poschodia a miestnosti (area/floor registry)")

    persons = (ws.cmd("person/list") or {}).get("storage", [])
    write_yaml({"persons": [{"id": p.get("id"), "name": p.get("name"),
                             "device_trackers": p.get("device_trackers", [])}
                            for p in persons]},
               REPO / "registry" / "persons.yaml",
               "# Osoby (person registry). Bez user_id a poverenia.")

    labels = ws.cmd("config/label_registry/list") or []
    if labels:
        write_yaml(labels, REPO / "registry" / "labels.yaml", "# Labels")


def export_helpers(rest: Rest) -> None:
    types = ["input_boolean", "input_number", "input_text", "input_select",
             "input_datetime", "input_button", "counter", "timer", "schedule"]
    out: dict[str, dict] = {}
    for helper_type in types:
        try:
            items = rest.get(f"/api/config/{helper_type}/config")
        except Exception:
            continue
        if items:
            out[helper_type] = items

    if out:
        write_yaml(out, REPO / "registry" / "helpers.yaml",
                   "# Helpery vytvorene cez UI (.storage)")


def export_inventory(rest: Rest, ws: Ws) -> None:
    entries = ws.cmd("config_entries/get") or []
    lines = ["# Integracie (config entries)", "",
             f"Spolu: {len(entries)}. Poverenia su v .storage a zamerne tu nie su.", "",
             "| Domain | Nazov | Stav |", "|---|---|---|"]
    for entry in sorted(entries, key=lambda e: (e.get("domain", ""), e.get("title", ""))):
        lines.append(f"| `{entry.get('domain')}` | {entry.get('title') or '-'} "
                     f"| {entry.get('state')} |")
    path = REPO / "inventory" / "integrations.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"  {path.relative_to(REPO)}")

    try:
        config = rest.get("/api/config")
    except Exception:
        return
    write_yaml({"version": config.get("version"),
                "location_name": config.get("location_name"),
                "time_zone": config.get("time_zone"),
                "unit_system": config.get("unit_system"),
                "components": sorted(config.get("components", []))},
               REPO / "inventory" / "core.yaml",
               "# Zakladne udaje o inštalacii (bez suradnic)")


# --------------------------------------------------------------------------

def main() -> None:
    url, token = load_env()
    print(f"Export z {url}")

    rest = Rest(url, token)
    try:
        states = rest.get("/api/states")
    except Exception as exc:
        die(f"nepodarilo sa pripojit na REST API: {exc}")

    ws = Ws(url, token)
    try:
        print("automatizacie:")
        n_auto = export_automations(rest, states)
        print("skripty:")
        n_script = export_scripts(rest, states)
        print("sceny:")
        n_scene = export_scenes(rest, states)
        print("dashboardy:")
        n_dash = export_dashboards(ws)
        print("registre:")
        export_registries(ws)
        export_helpers(rest)
        print("inventar:")
        export_inventory(rest, ws)
    finally:
        ws.close()

    print(f"\nHotovo: {n_auto} automatizacii, {n_script} skriptov, "
          f"{n_scene} scen, {n_dash} dashboardov.")
    print("Skontroluj `git diff` a commitni.")


if __name__ == "__main__":
    main()
