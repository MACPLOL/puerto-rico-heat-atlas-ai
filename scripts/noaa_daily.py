"""NOAA/NCEI Daily Summaries download, normalization, and validation helpers.

The canonical CSV stores temperatures in degrees Celsius because the request
explicitly asks NOAA for metric units.  Values are never converted based on
their magnitude: conversion is driven only by an explicit units field.
"""
from __future__ import annotations

import csv
import json
import time
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

NOAA_URL = "https://www.ncei.noaa.gov/access/services/data/v1"
SOURCE = "NOAA/NCEI Daily Summaries Access Data Service"
CANONICAL_COLUMNS = (
    "STATION", "NAME", "LATITUDE", "LONGITUDE", "ELEVATION", "DATE", "TMAX", "TMIN",
    "TMAX_ATTRIBUTES", "TMIN_ATTRIBUTES", "UNITS", "SOURCE",
)


class NOAAError(RuntimeError):
    """A useful, user-facing NOAA response error."""


def load_registry(path: str | Path) -> dict[str, dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    stations = data.get("stations")
    if not isinstance(stations, list):
        raise ValueError("Station registry must contain a stations list")
    result = {station.get("id"): station for station in stations if station.get("id")}
    if len(result) != len(stations):
        raise ValueError("Station registry has missing or duplicate IDs")
    return result


def _request_json(url: str, *, timeout: int, retries: int, user_agent: str) -> list[dict]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
            with urlopen(request, timeout=timeout) as response:  # nosec B310: fixed official HTTPS endpoint
                if response.status != 200:
                    raise NOAAError(f"NOAA returned HTTP {response.status}")
                try:
                    payload = json.loads(response.read().decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise NOAAError("NOAA returned malformed JSON") from error
                if not isinstance(payload, list):
                    raise NOAAError("NOAA response must be a JSON array")
                if not all(isinstance(item, dict) for item in payload):
                    raise NOAAError("NOAA response contains a non-object record")
                return payload
        except (HTTPError, URLError, TimeoutError, NOAAError) as error:
            last_error = error
            if isinstance(error, HTTPError) and 400 <= error.code < 500 and error.code != 429:
                break
            if attempt < retries:
                time.sleep(0.5 * (2 ** attempt))
    raise NOAAError(f"NOAA download failed: {last_error}")


def fetch_station(station_id: str, start: str, end: str, *, timeout: int = 30, retries: int = 2,
                  opener=None) -> list[dict]:
    """Fetch one station from the documented NCEI Access Data Service."""
    try:
        start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError as error:
        raise ValueError("Dates must use YYYY-MM-DD") from error
    if end_date < start_date:
        raise ValueError("End date cannot be before start date")
    query = urlencode({
        "dataset": "daily-summaries", "stations": station_id, "startDate": start,
        "endDate": end, "format": "json", "units": "metric", "includeAttributes": "true",
    })
    url = f"{NOAA_URL}?{query}"
    if opener is not None:
        return opener(url)
    return _request_json(url, timeout=timeout, retries=retries, user_agent="puerto-rico-heat-atlas/0.1 (+https://github.com/MACPLOL/puerto-rico-heat-atlas-ai)")


def _number(value, field: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {field} value {value!r}") from error


def normalize_records(records: Iterable[dict], station: dict) -> list[dict]:
    """Normalize a metric Daily Summaries JSON response into canonical rows."""
    normalized = []
    for item in records:
        station_id = item.get("STATION") or item.get("station")
        if station_id != station["id"]:
            raise ValueError(f"NOAA record station {station_id!r} does not match {station['id']}")
        raw_date = item.get("DATE") or item.get("date")
        try:
            parsed_date = date.fromisoformat(str(raw_date))
        except ValueError as error:
            raise ValueError(f"Malformed NOAA DATE {raw_date!r}") from error
        tmax, tmin = _number(item.get("TMAX"), "TMAX"), _number(item.get("TMIN"), "TMIN")
        normalized.append({
            "STATION": station["id"], "NAME": item.get("NAME") or station["name"],
            "LATITUDE": _number(item.get("LATITUDE"), "LATITUDE") if item.get("LATITUDE") not in (None, "") else station["latitude"],
            "LONGITUDE": _number(item.get("LONGITUDE"), "LONGITUDE") if item.get("LONGITUDE") not in (None, "") else station["longitude"],
            "ELEVATION": _number(item.get("ELEVATION"), "ELEVATION") if item.get("ELEVATION") not in (None, "") else station.get("elevation_m", ""),
            "DATE": parsed_date.isoformat(), "TMAX": tmax, "TMIN": tmin,
            "TMAX_ATTRIBUTES": item.get("TMAX_ATTRIBUTES", ""), "TMIN_ATTRIBUTES": item.get("TMIN_ATTRIBUTES", ""),
            "UNITS": "C", "SOURCE": SOURCE,
        })
    return sorted(normalized, key=lambda row: (row["STATION"], row["DATE"]))


def read_canonical(path: str | Path) -> list[dict]:
    source = Path(path)
    if not source.exists():
        return []
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != CANONICAL_COLUMNS:
            raise ValueError(f"{source} does not use the canonical NOAA CSV schema")
        return list(reader)


def merge_records(existing: Iterable[dict], incoming: Iterable[dict]) -> list[dict]:
    """Use incoming rows for equal station/date keys and sort deterministically."""
    merged = {(row["STATION"], row["DATE"]): dict(row) for row in existing}
    for row in incoming:
        merged[(row["STATION"], row["DATE"])] = dict(row)
    return [merged[key] for key in sorted(merged)]


def validate_rows(rows: Iterable[dict], registry: dict[str, dict]) -> list[dict]:
    rows = list(rows)
    if not rows:
        raise ValueError("Canonical observation data is empty")
    seen = set()
    for row in rows:
        if set(row) != set(CANONICAL_COLUMNS):
            raise ValueError("Canonical observation row has unexpected columns")
        station_id, raw_date = row["STATION"], row["DATE"]
        if station_id not in registry:
            raise ValueError(f"Unknown station ID {station_id!r}")
        try:
            date.fromisoformat(raw_date)
        except ValueError as error:
            raise ValueError(f"Malformed DATE {raw_date!r}") from error
        key = (station_id, raw_date)
        if key in seen:
            raise ValueError(f"Duplicate station-date record {station_id} {raw_date}")
        seen.add(key)
        if row["UNITS"] != "C":
            raise ValueError("Canonical temperatures must declare C units")
        for field in ("TMAX", "TMIN"):
            value = _number(row[field], field)
            if value is not None and not (-40 <= value <= 60):
                raise ValueError(f"Unreasonable Celsius {field} value {value}")
    return rows


def write_canonical(path: str | Path, rows: Iterable[dict]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(destination)
