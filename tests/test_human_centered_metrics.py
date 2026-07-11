import json

import pandas as pd

from process_heatmetrics_multi import (
    BASELINE_END_YEAR,
    BASELINE_START_YEAR,
    MIN_DAYS_PER_YEAR,
    anomaly,
    calculate_year_metrics,
    feature_collection,
    historical_percentile,
    longest_threshold_streak,
    main,
)


def daily_frame(year, values):
    """values contains (date, Tmax C, Tmin C) rows."""
    frame = pd.DataFrame(values, columns=["DATE", "TMAX_C", "TMIN_C"])
    frame["DATE"] = pd.to_datetime(frame["DATE"])
    frame["month"] = frame["DATE"].dt.month
    return frame


def complete_frame(year, tmax=32.0, tmin=24.0):
    dates = pd.date_range(f"{year}-01-01", periods=MIN_DAYS_PER_YEAR)
    return daily_frame(year, [(date, tmax, tmin) for date in dates])


def test_completeness_handles_normal_and_leap_years():
    normal = calculate_year_metrics(complete_frame(2023))
    leap = calculate_year_metrics(complete_frame(2024))
    assert normal["completeness_pct"] == 200 * 100 / 365
    assert leap["completeness_pct"] == 200 * 100 / 366


def test_percentages_use_valid_pair_days():
    frame = complete_frame(2023, 31.0, 23.0)
    frame.loc[:99, "TMAX_C"] = 32.0
    frame.loc[100:149, "TMIN_C"] = 24.0
    metrics = calculate_year_metrics(frame)
    assert metrics["valid_days"] == 200
    assert metrics["hot_day_pct"] == 50
    assert metrics["warm_night_pct"] == 25


def test_streaks_and_gaps_or_missing_values_break_them():
    frame = daily_frame(2023, [
        ("2023-01-01", 32, 24), ("2023-01-02", 32, 24),
        ("2023-01-04", 32, 24), ("2023-01-05", None, 24),
        ("2023-01-06", 32, None), ("2023-01-07", 32, 24),
    ])
    assert longest_threshold_streak(frame, "TMAX_C", 32) == 2
    assert longest_threshold_streak(frame, "TMIN_C", 24) == 2


def test_year_metrics_include_longest_streaks():
    frame = complete_frame(2023, 31.0, 23.0)
    frame.loc[:2, "TMAX_C"] = 32
    frame.loc[5:8, "TMIN_C"] = 24
    metrics = calculate_year_metrics(frame)
    assert metrics["longest_hot_streak"] == 3
    assert metrics["longest_warm_night_streak"] == 4


def test_existing_core_metric_fields_keep_their_definitions():
    frame = complete_frame(2023, 31.0, 23.0)
    frame.loc[:49, "TMAX_C"] = 35
    frame.loc[50:99, "TMAX_C"] = 32
    frame.loc[:74, "TMIN_C"] = 24
    metrics = calculate_year_metrics(frame)
    assert {name: metrics[name] for name in (
        "hot_days_32", "hot_days_35", "warm_nights_24", "oppressive_days",
        "hottest_month_index", "hottest_month_tmax", "hottest_month_tmin",
    )} == {
        "hot_days_32": 100, "hot_days_35": 50, "warm_nights_24": 75,
        "oppressive_days": 75, "hottest_month_index": 1,
        "hottest_month_tmax": 35.0, "hottest_month_tmin": 24.0,
    }


def test_anomaly_requires_baseline_years_and_uses_mean():
    baseline = {str(year): 10.0 for year in range(BASELINE_START_YEAR, BASELINE_END_YEAR + 1)}
    assert anomaly(16, baseline) == 6
    assert anomaly(16, dict(list(baseline.items())[:19])) is None


def test_percentile_handles_ties_and_minimum_year_count():
    values = {str(year): value for year, value in enumerate([1, 2, 2, 3, 4, 5, 6, 7, 8, 9])}
    assert historical_percentile(2, values) == 20
    assert historical_percentile(2, dict(list(values.items())[:9])) is None


def test_pipeline_adds_station_coverage_metadata_and_preserves_core_metrics(tmp_path):
    source = tmp_path / "source.csv"
    output = tmp_path / "stations.geojson"
    rows = []
    for year in (2022, 2023):
        for date in pd.date_range(f"{year}-01-01", periods=MIN_DAYS_PER_YEAR):
            rows.append({"STATION": "TEST", "NAME": "Test station", "LATITUDE": 18.4, "LONGITUDE": -66.1, "DATE": date, "TMAX": 89.6, "TMIN": 75.2})
    pd.DataFrame(rows).to_csv(source, index=False)
    main(str(source), str(output))
    data = json.loads(output.read_text())
    props = data["features"][0]["properties"]
    assert (props["data_start_year"], props["data_end_year"], props["valid_year_count"]) == (2022, 2023, 2)
    assert props["metrics"]["hot_days_32"] == {"2022": 200, "2023": 200}
    assert props["metrics"]["oppressive_days"] == {"2022": 200, "2023": 200}


def test_feature_collection_metadata_is_portable_and_descriptive():
    output = feature_collection([], "source.csv")
    assert output["source_filename"] == "source.csv"
    assert output["minimum_valid_days"] == MIN_DAYS_PER_YEAR
    assert output["baseline_period"] == {"start": 1991, "end": 2020}
    assert "heat index" in output["scientific_limitation"]
