import csv
import json

import pandas as pd

from process_heatmetrics_multi import (
    MIN_DAYS_PER_YEAR,
    calculate_year_metrics,
    fahrenheit_to_celsius,
    feature_collection,
)
from summarize_heatmetrics import main as write_summary


def year_data(rows):
    frame = pd.DataFrame(rows, columns=["TMAX_C", "TMIN_C"])
    frame["month"] = 7
    return frame


def complete_year(rows):
    return year_data(rows * MIN_DAYS_PER_YEAR)


def test_fahrenheit_to_celsius():
    assert fahrenheit_to_celsius(32) == 0
    assert fahrenheit_to_celsius(89.6) == 32


def test_thresholds_are_inclusive_and_oppressive_day_requires_both():
    metrics = calculate_year_metrics(complete_year([
        (32.0, 24.0),  # exactly at both thresholds
        (35.0, 23.9),  # exactly at very-hot threshold only
        (31.9, 24.0),
    ]))
    assert metrics["hot_days_32"] == MIN_DAYS_PER_YEAR * 2
    assert metrics["hot_days_35"] == MIN_DAYS_PER_YEAR
    assert metrics["warm_nights_24"] == MIN_DAYS_PER_YEAR * 2
    assert metrics["oppressive_days"] == MIN_DAYS_PER_YEAR


def test_minimum_valid_days_and_missing_values():
    incomplete = complete_year([(32.0, 24.0)])
    incomplete.loc[0, "TMIN_C"] = None
    assert calculate_year_metrics(incomplete) is None

    complete = complete_year([(32.0, 24.0)])
    complete.loc[0, "TMIN_C"] = None
    complete.loc[len(complete)] = [32.0, 24.0, 7]
    metrics = calculate_year_metrics(complete)
    assert metrics["hot_days_32"] == MIN_DAYS_PER_YEAR
    assert metrics["oppressive_days"] == MIN_DAYS_PER_YEAR


def test_geojson_output_structure():
    feature = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-66.1, 18.4]},
        "properties": {"id": "TEST", "name": "Test", "metrics": {"hot_days_32": {"2020": 1}}},
    }
    output = feature_collection([feature])
    assert output["type"] == "FeatureCollection"
    assert output["features"] == [feature]


def test_summary_csv_quotes_station_name_with_comma(tmp_path):
    source = tmp_path / "stations.geojson"
    output = tmp_path / "summary.csv"
    source.write_text(json.dumps({"type": "FeatureCollection", "features": [{
        "type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]},
        "properties": {"id": "TEST", "name": "Ponce, Puerto Rico", "metrics": {
            "hot_days_32": {"1961": 1, "2006": 2},
            "warm_nights_24": {"1961": 3, "2006": 4},
        }},
    }]}), encoding="utf-8")
    write_summary(source, output)
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[1][0] == "Ponce, Puerto Rico"
    assert rows[1][2:4] == ["1961", "2006"]
