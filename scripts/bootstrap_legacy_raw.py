#!/usr/bin/env python3
"""One-time, explicit migration of supplied Fahrenheit exports to canonical CSV.

This preserves their documented historical provenance; normal refreshes use
the NOAA downloader and never depend on this migration helper.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.noaa_daily import CANONICAL_COLUMNS, load_registry, merge_records, validate_rows, write_canonical



def legacy_rows(path: Path, registry: dict[str, dict]):
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["STATION"] not in registry:
                continue
            yield {
                "STATION": row["STATION"], "NAME": row["NAME"], "LATITUDE": row["LATITUDE"], "LONGITUDE": row["LONGITUDE"],
                "ELEVATION": row["ELEVATION"], "DATE": row["DATE"], "TMAX": _celsius(row.get("TMAX")), "TMIN": _celsius(row.get("TMIN")),
                "TMAX_ATTRIBUTES": "", "TMIN_ATTRIBUTES": "", "UNITS": "C",
                "SOURCE": "Legacy project Fahrenheit export; NOAA/NCEI provenance pending replacement by official refresh",
            }


def _celsius(value):
    if value in (None, ""):
        return ""
    return (float(value) - 32) * 5 / 9


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Explicitly migrate legacy project Fahrenheit files to the canonical Celsius schema.")
    parser.add_argument("--output", type=Path, default=ROOT / "data/raw/noaa_daily.csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    registry = load_registry(ROOT / "data/stations.json")
    sources = [ROOT / "data/all_stations_1960_2025.csv", ROOT / "data/raw/san_juan_1960_2025.csv"]
    rows = merge_records([], (row for source in sources for row in legacy_rows(source, registry)))
    validate_rows(rows, registry)
    if args.dry_run:
        print(f"Dry run: would write {len(rows)} canonical rows.")
    else:
        write_canonical(args.output, rows)
        print(f"Wrote {len(rows)} canonical rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
