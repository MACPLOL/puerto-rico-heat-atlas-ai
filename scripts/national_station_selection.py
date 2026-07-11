"""Deterministic GHCN-Daily station ranking for the national atlas.

This module consumes the official fixed-width ``ghcnd-stations.txt`` and
``ghcnd-inventory.txt`` files. It never creates stations or observations.
Population targets and state boundaries are separate versioned inputs so a
selection can be reproduced exactly from its manifest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

REQUIRED_ELEMENTS = {"TMAX", "TMIN"}
ROLE_TARGETS = {"urban": 8, "rural": 8, "coverage": 4}


@dataclass(frozen=True)
class Station:
    id: str
    latitude: float
    longitude: float
    elevation_m: float | None
    state: str
    name: str
    first_year: int
    last_year: int
    elements: tuple[str, ...]

    @property
    def record_years(self) -> int:
        return self.last_year - self.first_year + 1


def parse_stations(text: str) -> dict[str, dict]:
    found = {}
    for line in text.splitlines():
        if len(line) < 71:
            continue
        station_id = line[0:11].strip()
        try:
            found[station_id] = {
                "id": station_id, "latitude": float(line[12:20]),
                "longitude": float(line[21:30]),
                "elevation_m": None if line[31:37].strip() == "-999.9" else float(line[31:37]),
                "state": line[38:40].strip(), "name": line[41:71].strip(),
            }
        except ValueError:
            continue
    return found


def parse_inventory(text: str) -> dict[str, dict[str, tuple[int, int]]]:
    inventory: dict[str, dict[str, tuple[int, int]]] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        try:
            inventory.setdefault(parts[0], {})[parts[3]] = (int(parts[4]), int(parts[5]))
        except ValueError:
            continue
    return inventory


def candidates(stations_text: str, inventory_text: str) -> list[Station]:
    metadata, inventory = parse_stations(stations_text), parse_inventory(inventory_text)
    output = []
    for station_id, item in metadata.items():
        variables = inventory.get(station_id, {})
        if not REQUIRED_ELEMENTS.issubset(variables):
            continue
        first = max(variables[name][0] for name in REQUIRED_ELEMENTS)
        last = min(variables[name][1] for name in REQUIRED_ELEMENTS)
        if first > last:
            continue
        output.append(Station(**item, first_year=first, last_year=last,
                              elements=tuple(sorted(variables))))
    return sorted(output, key=lambda item: item.id)


def score(station: Station, role: str, current_year: int | None = None) -> float:
    """Stable pre-spacing score; final tie breaker is always NOAA station ID."""
    current_year = current_year or date.today().year
    recency = max(0, 25 - (current_year - station.last_year))
    length = min(station.record_years, 100)
    variable_bonus = 15 if {"PRCP", "TMAX", "TMIN"}.issubset(station.elements) else 0
    elevation_bonus = min(abs(station.elevation_m or 0) / 100, 15) if role == "coverage" else 0
    return round(length * 0.55 + recency + variable_bonus + elevation_bonus, 4)


def select_state(stations: list[Station], roles: dict[str, str], state: str,
                 count: int = 20, current_year: int | None = None) -> list[dict]:
    """Select a deterministic role-balanced set from pre-classified candidates."""
    pool = [item for item in stations if item.state == state]
    selected: list[dict] = []
    used: set[str] = set()
    for role, target in ROLE_TARGETS.items():
        ranked = sorted((s for s in pool if roles.get(s.id) == role),
                        key=lambda s: (-score(s, role, current_year), s.id))
        for station in ranked[:target]:
            selected.append({**asdict(station), "role": role,
                             "selection_score": score(station, role, current_year)})
            used.add(station.id)
    ranked_remainder = sorted((s for s in pool if s.id not in used),
                              key=lambda s: (-score(s, roles.get(s.id, "coverage"), current_year), s.id))
    for station in ranked_remainder[:max(0, count - len(selected))]:
        role = roles.get(station.id, "coverage")
        selected.append({**asdict(station), "role": role,
                         "selection_score": score(station, role, current_year)})
    return selected[:count]


def write_manifest(path: Path, selected: list[dict], sources: dict[str, Path]) -> None:
    fingerprints = {name: sha256(source.read_bytes()).hexdigest() for name, source in sources.items()}
    payload = {"schema_version": 1, "source_sha256": fingerprints,
               "station_count": len(selected), "stations": selected}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
