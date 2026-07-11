#!/usr/bin/env python3
"""Perform the complete, reproducible historical-data refresh.

Downloads are staged in a temporary directory.  Repository files are atomically
replaced only after canonical data and both generated outputs validate.
"""
from __future__ import annotations

import argparse
import csv
import filecmp
import json
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from process_heatmetrics_multi import main as build_geojson
from scripts.fetch_noaa_daily import DEFAULT_OVERLAP_DAYS, date_range_for_station
from scripts.noaa_daily import fetch_station, load_registry, merge_records, normalize_records, read_canonical, validate_rows, write_canonical
from summarize_heatmetrics import main as build_summary



def validate_outputs(geojson_path: Path, summary_path: Path, registry: dict[str, dict]) -> None:
    if not geojson_path.exists() or geojson_path.stat().st_size == 0:
        raise ValueError("Generated GeoJSON is empty")
    if not summary_path.exists() or summary_path.stat().st_size == 0:
        raise ValueError("Generated summary CSV is empty")
    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    if data.get("type") != "FeatureCollection" or not data.get("features"):
        raise ValueError("Generated GeoJSON is not a non-empty FeatureCollection")
    published = {station_id for station_id, station in registry.items() if station.get("published")}
    emitted = {feature.get("properties", {}).get("id") for feature in data["features"]}
    if not published.issubset(emitted):
        raise ValueError(f"Published stations missing from GeoJSON: {sorted(published - emitted)}")
    for feature in data["features"]:
        props = feature.get("properties", {})
        if props.get("id") not in registry:
            raise ValueError(f"Generated GeoJSON contains unknown station {props.get('id')!r}")
    with summary_path.open(newline="", encoding="utf-8") as handle:
        if not list(csv.DictReader(handle)):
            raise ValueError("Generated summary CSV has no station rows")


def atomic_replace(source: Path, destination: Path) -> None:
    source.replace(destination)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download, validate, and regenerate Puerto Rico Heat Atlas historical data.")
    parser.add_argument("--station", help="Refresh one registered station only.")
    parser.add_argument("--start-date", help="Fetch start date (YYYY-MM-DD).")
    parser.add_argument("--end-date", help="Fetch end date (YYYY-MM-DD), default: today.")
    parser.add_argument("--full-refresh", action="store_true", help="Download selected station(s) from 1960-01-01.")
    parser.add_argument("--overlap-days", type=int, default=DEFAULT_OVERLAP_DAYS)
    parser.add_argument("--dry-run", action="store_true", help="Validate all staged work without modifying repository data files.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest; useful only for focused local diagnostics.")
    parser.add_argument("--registry", type=Path, default=ROOT / "data/stations.json")
    parser.add_argument("--raw-data", type=Path, default=ROOT / "data/raw/noaa_daily.csv")
    parser.add_argument("--geojson", type=Path, default=ROOT / "data/stations_heatmetrics_all.geojson")
    parser.add_argument("--summary", type=Path, default=ROOT / "data/station_summary.csv")
    return parser


def run(args, *, fetch=fetch_station) -> bool:
    if args.overlap_days < 0:
        raise ValueError("--overlap-days must be zero or greater")
    registry = load_registry(args.registry)
    if args.station and args.station not in registry:
        raise ValueError(f"Unknown registered station ID: {args.station}")
    if not args.skip_tests:
        subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=True)
    existing = read_canonical(args.raw_data)
    chosen = [registry[args.station]] if args.station else [s for s in registry.values() if s.get("active")]
    incoming = []
    for station in chosen:
        start, end = date_range_for_station(existing, station["id"], args)
        print(f"Fetching {station['id']} from {start} through {end}")
        incoming.extend(normalize_records(fetch(station["id"], start, end), station))
    merged = merge_records(existing, incoming)
    validate_rows(merged, registry)
    with tempfile.TemporaryDirectory(prefix="heat-atlas-refresh-") as temporary:
        staging = Path(temporary)
        raw_stage, geo_stage, summary_stage = staging / "noaa_daily.csv", staging / "stations.geojson", staging / "summary.csv"
        write_canonical(raw_stage, merged)
        build_geojson(str(raw_stage), str(geo_stage))
        build_summary(str(geo_stage), str(summary_stage))
        validate_outputs(geo_stage, summary_stage, registry)
        changed = not args.raw_data.exists() or any(not target.exists() or not filecmp.cmp(stage, target, shallow=False) for stage, target in ((raw_stage, args.raw_data), (geo_stage, args.geojson), (summary_stage, args.summary)))
        if args.dry_run:
            print(f"Dry run: {len(incoming)} downloaded row(s); {'would update outputs' if changed else 'no generated differences'}.")
            return changed
        if changed:
            for stage, target in ((raw_stage, args.raw_data), (geo_stage, args.geojson), (summary_stage, args.summary)):
                target.parent.mkdir(parents=True, exist_ok=True)
                atomic_replace(stage, target)
            print("Refresh completed: canonical data and generated outputs updated.")
        else:
            print("Refresh completed: no generated differences.")
        return changed


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run(args)
    except (ValueError, RuntimeError) as error:
        print(f"Refresh failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
