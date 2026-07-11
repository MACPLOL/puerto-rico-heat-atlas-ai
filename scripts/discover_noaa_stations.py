#!/usr/bin/env python3
"""Optionally report official Puerto Rico GHCN-Daily station candidates.

The official GHCN-Daily station and inventory files provide the coverage
metadata needed for a useful report. Discovery never changes the registry/map.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.noaa_daily import load_registry
STATIONS_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"
INVENTORY_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt"


def download_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "puerto-rico-heat-atlas/0.1"})
    with urlopen(request, timeout=30) as response:  # nosec B310: fixed official HTTPS URL
        if response.status != 200:
            raise RuntimeError(f"NOAA returned HTTP {response.status}")
        return response.read().decode("utf-8")


def candidates(stations_text: str, inventory_text: str):
    stations = {}
    for line in stations_text.splitlines():
        station_id = line[:11].strip()
        if station_id.startswith("RQ"):
            stations[station_id] = {"name": line[41:].strip(), "latitude": line[12:20].strip(), "longitude": line[21:30].strip()}
    inventory = {}
    for line in inventory_text.splitlines():
        station_id, element = line[:11].strip(), line[31:35].strip()
        if station_id not in stations or element not in {"TMAX", "TMIN"}:
            continue
        inventory.setdefault(station_id, {})[element] = (int(line[36:40]), int(line[41:45]))
    for station_id in sorted(stations):
        elements = inventory.get(station_id, {})
        earliest = min((span[0] for span in elements.values()), default="")
        latest = max((span[1] for span in elements.values()), default="")
        paired_start = max((span[0] for span in elements.values()), default=None)
        paired_end = min((span[1] for span in elements.values()), default=None)
        valid_years = max(0, paired_end - paired_start + 1) if paired_start is not None and paired_end is not None else 0
        yield station_id, stations[station_id], earliest, latest, valid_years, "TMAX" in elements and "TMIN" in elements


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Report official NOAA/NCEI Puerto Rico daily-summary station candidates; does not publish stations.")
    parser.add_argument("--output", type=Path, default=Path("noaa_pr_station_candidates.csv"))
    parser.add_argument("--registry", type=Path, default=ROOT / "data/stations.json")
    args = parser.parse_args(argv)
    registered = load_registry(args.registry)
    fields = ["station_id", "name", "latitude", "longitude", "earliest_year", "latest_year", "approx_valid_year_count", "tmax_tmin_available", "registered"]
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for station_id, station, earliest, latest, valid_years, paired in candidates(download_text(STATIONS_URL), download_text(INVENTORY_URL)):
            writer.writerow({"station_id": station_id, "name": station["name"], "latitude": station["latitude"], "longitude": station["longitude"], "earliest_year": earliest, "latest_year": latest, "approx_valid_year_count": valid_years, "tmax_tmin_available": paired, "registered": station_id in registered})
    print(f"Wrote candidate report to {args.output}; review coverage and duplicates before adding any station.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
