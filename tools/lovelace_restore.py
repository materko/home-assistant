#!/usr/bin/env python3
"""Priprav exportovany Lovelace dashboard na vlozenie spat do Home Assistant.

Git Exporter uklada dashboardy v tvare, ktory sa NEDA vlozit priamo:

    config:
      title: "Bat\\xE9rie"        <- escapovana diakritika
      views:                       <- odsadene o dve medzery navyse
      - ...

HA Raw configuration editor ocakava obsah *pod* klucom config:, odsadeny
od zaciatku riadku a s normalnou diakritikou. Tento skript to prevedie.

Pouzitie:
    python tools/lovelace_restore.py lovelace/lovelace.dashboard_baterie.yaml
    python tools/lovelace_restore.py --all        # vsetky do priecinka obnova/

Vysledok vloz cez: dashboard -> ceruzka -> tri bodky -> Raw configuration editor
(cely obsah nahrad, potom Save).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "lovelace"
OUT = REPO / "obnova"

try:
    import yaml
except ImportError:
    sys.exit("CHYBA: chyba PyYAML  ->  pip install pyyaml")


def _str_representer(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


yaml.add_representer(str, _str_representer)


def convert(path: Path) -> str:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name}: necakany tvar suboru")

    # subory dashboardov maju obal config:, zoznamy (lovelace_dashboards,
    # lovelace_resources) maju items: a do raw editora nepatria vobec
    if "config" in raw:
        body = raw["config"]
    elif "items" in raw:
        raise ValueError(
            f"{path.name}: toto nie je dashboard, ale zoznam. "
            "Dashboardy a resources sa vytvaraju v Settings, nie v raw editore."
        )
    else:
        body = raw

    return yaml.dump(body, allow_unicode=True, sort_keys=False,
                     default_flow_style=False, width=120)


def main() -> None:
    # dashboardy obsahuju emoji a diakritiku; konzola na Windows je cp1250
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("subor", nargs="?", help="cesta k lovelace/*.yaml")
    ap.add_argument("--all", action="store_true",
                    help="preved vsetky dashboardy do priecinka obnova/")
    args = ap.parse_args()

    if args.all:
        OUT.mkdir(exist_ok=True)
        done = skipped = 0
        for src in sorted(SRC.glob("lovelace.*.yaml")):
            try:
                text = convert(src)
            except ValueError as exc:
                print(f"  preskocene: {exc}")
                skipped += 1
                continue
            dst = OUT / src.name
            dst.write_text(text, encoding="utf-8", newline="\n")
            print(f"  {dst.relative_to(REPO)}")
            done += 1
        print(f"\nHotovo: {done} dashboardov, {skipped} preskocenych.")
        print("Obsah kazdeho suboru vloz do Raw configuration editora "
              "prislusneho dashboardu.")
        return

    if not args.subor:
        ap.error("zadaj subor alebo --all")

    path = Path(args.subor)
    if not path.is_absolute():
        path = REPO / path
    if not path.is_file():
        sys.exit(f"CHYBA: subor neexistuje: {path}")

    try:
        sys.stdout.write(convert(path))
    except ValueError as exc:
        sys.exit(f"CHYBA: {exc}")


if __name__ == "__main__":
    main()
