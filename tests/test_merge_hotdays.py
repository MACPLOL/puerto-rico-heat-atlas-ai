import json

from merge_hotdays_geojson import main


def feature(station_id, name):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-66, 18]},
        "properties": {"id": station_id, "name": name, "values": {"2020": 1}},
    }


def test_merge_prevents_duplicate_station_ids(tmp_path):
    first, second, output = (tmp_path / name for name in ("one.geojson", "two.geojson", "out.geojson"))
    first.write_text(json.dumps({"type": "FeatureCollection", "features": [feature("A", "One")]}))
    second.write_text(json.dumps({"type": "FeatureCollection", "features": [feature("A", "Duplicate"), feature("B", "Two")]}))
    main(first, second, output)
    merged = json.loads(output.read_text())
    assert [item["properties"]["id"] for item in merged["features"]] == ["A", "B"]
