import argparse
import csv
import json
from datetime import date
from pathlib import Path
from urllib.error import URLError

import pandas as pd
import pytest

from process_heatmetrics_multi import main as build_geojson
from scripts.fetch_noaa_daily import date_range_for_station
from scripts.noaa_daily import (
    CANONICAL_COLUMNS, NOAAError, _request_json, load_registry, merge_records,
    normalize_records, validate_rows, write_canonical,
)
from scripts.refresh_data import run, validate_outputs
from scripts.discover_noaa_stations import candidates


def station(station_id="TEST"):
    return {"id": station_id, "name": "Test Station", "latitude": 18.4, "longitude": -66.1, "elevation_m": 1, "active": True, "published": True}


def noaa_record(station_id="TEST", day="2025-01-01", tmax="32", tmin="24"):
    return {"STATION": station_id, "DATE": day, "TMAX": tmax, "TMIN": tmin, "TMAX_ATTRIBUTES": " , ,", "TMIN_ATTRIBUTES": " , ,"}


def canonical_row(station_id="TEST", day="2025-01-01", tmax="32", tmin="24"):
    return normalize_records([noaa_record(station_id, day, tmax, tmin)], station(station_id))[0]


def write_registry(path, stations):
    path.write_text(json.dumps({"stations": stations}), encoding="utf-8")


def test_official_response_parsing_units_missing_and_stable_ordering():
    rows = normalize_records([noaa_record(day="2025-01-02", tmax="", tmin="24"), noaa_record(day="2025-01-01", tmax="31.5", tmin=None)], station())
    assert [row["DATE"] for row in rows] == ["2025-01-01", "2025-01-02"]
    assert rows[0]["TMAX"] == 31.5 and rows[0]["TMIN"] is None
    assert rows[0]["UNITS"] == "C"


def test_invalid_date_station_and_unknown_registry_id_are_rejected():
    with pytest.raises(ValueError, match="does not match"):
        normalize_records([noaa_record("OTHER")], station())
    with pytest.raises(ValueError, match="Malformed"):
        normalize_records([noaa_record(day="not-a-date")], station())
    with pytest.raises(ValueError, match="Unknown station"):
        validate_rows([canonical_row()], {})


def test_duplicate_replacement_and_incremental_overlap_are_deterministic():
    old = canonical_row(tmax="30")
    replacement = canonical_row(tmax="31")
    later = canonical_row(day="2025-01-02", tmax="32")
    merged = merge_records([later, old], [replacement])
    assert [(r["DATE"], r["TMAX"]) for r in merged] == [("2025-01-01", 31.0), ("2025-01-02", 32.0)]
    args = argparse.Namespace(start_date=None, end_date="2025-02-01", full_refresh=False, overlap_days=14)
    assert date_range_for_station(merged, "TEST", args) == ("2024-12-19", "2025-02-01")


def test_full_refresh_and_empty_response_behavior():
    args = argparse.Namespace(start_date=None, end_date="2025-02-01", full_refresh=True, overlap_days=14)
    assert date_range_for_station([canonical_row()], "TEST", args) == ("1960-01-01", "2025-02-01")
    assert normalize_records([], station()) == []
    with pytest.raises(ValueError, match="empty"):
        validate_rows([], {"TEST": station()})


def test_http_and_malformed_response_failures(monkeypatch):
    def fails(*args, **kwargs):
        raise URLError("offline")
    monkeypatch.setattr("scripts.noaa_daily.urlopen", fails)
    with pytest.raises(NOAAError, match="download failed"):
        _request_json("https://example.invalid", timeout=1, retries=0, user_agent="test")

    class Response:
        status = 200
        def read(self): return b"not-json"
        def __enter__(self): return self
        def __exit__(self, *args): return False
    monkeypatch.setattr("scripts.noaa_daily.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(NOAAError, match="malformed"):
        _request_json("https://example.invalid", timeout=1, retries=0, user_agent="test")


def test_current_incomplete_year_is_excluded_and_completed_year_is_included(tmp_path):
    source, output = tmp_path / "source.csv", tmp_path / "out.geojson"
    rows = []
    for year in (2025, 2026):
        for day in pd.date_range(f"{year}-01-01", periods=200):
            rows.append({"STATION": "TEST", "NAME": "Test", "LATITUDE": 18.4, "LONGITUDE": -66.1, "DATE": day, "TMAX": 32, "TMIN": 24, "UNITS": "C"})
    pd.DataFrame(rows).to_csv(source, index=False)
    build_geojson(str(source), str(output), current_year=2026)
    years = json.loads(output.read_text())["features"][0]["properties"]["metrics"]["hot_days_32"]
    assert years == {"2025": 200}


def test_seven_station_registry_is_valid():
    registry = load_registry(Path("data/stations.json"))
    assert len(registry) == 7
    assert {sid for sid, item in registry.items() if item["published"]} == set(registry)
    assert "RQW00011641" in registry


def test_station_discovery_reports_temperature_coverage():
    station_line = f"{'RQW00011641':<11} {'18.4326':>8} {'-66.0106':>9} {'3.0':>6} {'SAN JUAN TEST':<30}"
    tmax = f"{'RQW00011641':<11} {'18.4326':>8} {'-66.0106':>9} {'TMAX':<4} {'1960':>4} {'2025':>4}"
    tmin = f"{'RQW00011641':<11} {'18.4326':>8} {'-66.0106':>9} {'TMIN':<4} {'1962':>4} {'2024':>4}"
    found = list(candidates(station_line, f"{tmax}\n{tmin}"))
    assert found[0][0] == "RQW00011641"
    assert found[0][2:] == (1960, 2025, 63, True)


def test_fixture_end_to_end_refresh_dry_run_and_no_change(tmp_path):
    registry_path = tmp_path / "stations.json"
    raw, geojson, summary = tmp_path / "raw.csv", tmp_path / "out.geojson", tmp_path / "summary.csv"
    write_registry(registry_path, [station()])
    records = [noaa_record(day=day.date().isoformat()) for day in pd.date_range("2025-01-01", periods=200)]
    def fetch(station_id, start, end):
        assert station_id == "TEST"
        return records
    args = argparse.Namespace(station=None, start_date="2025-01-01", end_date="2025-12-31", full_refresh=False, overlap_days=14, dry_run=True, skip_tests=True, registry=registry_path, raw_data=raw, geojson=geojson, summary=summary)
    assert run(args, fetch=fetch) is True
    assert not any(path.exists() for path in (raw, geojson, summary))
    args.dry_run = False
    assert run(args, fetch=fetch) is True
    assert run(args, fetch=fetch) is False
    assert list(csv.DictReader(summary.open()))[0]["id"] == "TEST"
