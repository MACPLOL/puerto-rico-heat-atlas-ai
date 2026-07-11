#!/usr/bin/env python3
"""Fetch and merge NOAA/NCEI daily temperature observations.

Normal incremental downloads begin DEFAULT_OVERLAP_DAYS before each station's
latest stored date, allowing NOAA corrections to replace recent observations.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.noaa_daily import (
    NOAAError, fetch_station, load_registry, merge_records, normalize_records, read_canonical,
    validate_rows, write_canonical,
)

DEFAULT_OVERLAP_DAYS = 14


def date_range_for_station(existing, station_id: str, args) -> tuple[str, str]:
    end = args.end_date or date.today().isoformat()
    if args.start_date:
        return args.start_date, end
    if args.full_refresh:
        return "1960-01-01", end
    dates = [row["DATE"] for row in existing if row["STATION"] == station_id]
    if not dates:
        return "1960-01-01", end
    start = date.fromisoformat(max(dates)) - timedelta(days=args.overlap_days)
    return start.isoformat(), end


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch official NOAA/NCEI Daily Summaries into canonical Celsius CSV data.")
    parser.add_argument("--station", help="Fetch only one registered station ID.")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD); defaults to today.")
    parser.add_argument("--full-refresh", action="store_true", help="Fetch each selected station from 1960-01-01.")
    parser.add_argument("--overlap-days", type=int, default=DEFAULT_OVERLAP_DAYS, help=f"Incremental correction overlap (default: {DEFAULT_OVERLAP_DAYS}).")
    parser.add_argument("--dry-run", action="store_true", help="Download and validate without changing the canonical CSV.")
    parser.add_argument("--registry", default=ROOT / "data/stations.json", type=Path)
    parser.add_argument("--output", default=ROOT / "data/raw/noaa_daily.csv", type=Path)
    return parser


def main(argv=None, *, fetch=fetch_station) -> int:
    try:
        args = build_parser().parse_args(argv)
        if args.overlap_days < 0:
            raise ValueError("--overlap-days must be zero or greater")
        registry = load_registry(args.registry)
        if args.station and args.station not in registry:
            raise ValueError(f"Unknown registered station ID: {args.station}")
        selected = [registry[args.station]] if args.station else [station for station in registry.values() if station.get("active")]
        existing = read_canonical(args.output)
        incoming = []
        for station in selected:
            start, end = date_range_for_station(existing, station["id"], args)
            print(f"Fetching {station['id']} from {start} through {end}")
            records = fetch(station["id"], start, end)
            incoming.extend(normalize_records(records, station))
        merged = merge_records(existing, incoming)
        validate_rows(merged, registry)
        changed = merged != existing
        if args.dry_run:
            print(f"Dry run: {len(incoming)} downloaded row(s), {'would update' if changed else 'no changes'}.")
        elif changed:
            write_canonical(args.output, merged)
            print(f"Wrote {len(merged)} canonical observation row(s) to {args.output}")
        else:
            print("No canonical observation changes.")
        return 0
    except (NOAAError, ValueError) as error:
        print(f"Fetch failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
