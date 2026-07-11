#!/usr/bin/env python3
"""Optionally report official Puerto Rico GHCN-Daily station candidates.

The NCEI station-search service is deliberately reporting-only: discovery
never changes the public registry or map.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.noaa_daily import load_registry
STATIONS_URL = "https://www.ncei.noaa.gov/access/services/search/v1/data"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Report official NOAA/NCEI Puerto Rico daily-summary station candidates; does not publish stations.")
    parser.add_argument("--output", type=Path, default=Path("noaa_pr_station_candidates.csv"))
    parser.add_argument("--registry", type=Path, default=ROOT / "data/stations.json")
    args = parser.parse_args(argv)
    query = urlencode({"dataset": "daily-summaries", "location": "FIPS:72", "limit": "1000", "format": "json"})
    request = Request(f"{STATIONS_URL}?{query}", headers={"User-Agent": "puerto-rico-heat-atlas/0.1", "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:  # nosec B310: fixed official HTTPS endpoint
        if response.status != 200:
            raise SystemExit(f"NOAA returned HTTP {response.status}")
        import json
        stations = json.loads(response.read().decode("utf-8"))
    registered = load_registry(args.registry)
    fields = ["station_id", "name", "latitude", "longitude", "earliest_date", "latest_date", "tmax_tmin_available", "registered"]
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for station in stations:
            station_id = station.get("id") or station.get("station")
            writer.writerow({"station_id": station_id, "name": station.get("name", ""), "latitude": station.get("latitude", ""), "longitude": station.get("longitude", ""), "earliest_date": station.get("mindate", ""), "latest_date": station.get("maxdate", ""), "tmax_tmin_available": "check Daily Summaries inventory", "registered": station_id in registered})
    print(f"Wrote candidate report to {args.output}; review coverage and duplicates before adding any station.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
