#!/usr/bin/env python3
"""Create the dashboard's temperature-only station-year GeoJSON data."""

import json
import sys
from calendar import isleap
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Project temperature definitions (degrees Celsius).  These are deliberately
# temperature-only measures, not heat index, WBGT, or feels-like calculations.
HOT_DAY_32 = 32.0
HOT_DAY_35 = 35.0
WARM_NIGHT_24 = 24.0
MIN_DAYS_PER_YEAR = 200
BASELINE_START_YEAR = 1991
BASELINE_END_YEAR = 2020
MIN_BASELINE_YEARS = 20
MIN_PERCENTILE_YEARS = 10

FRIENDLY_NAMES = {
    "SAN JUAN L M MARIN INTERNATIONAL AIRPORT, PR US": "San Juan (Airport)",
    "PONCE 4 E, PR US": "Ponce",
    "MAYAGUEZ 1 O, PR US": "Mayagüez",
    "ROOSEVELT ROADS, PR US": "Ceiba (Roosevelt Roads)",
    "ARECIBO 3 ESE, PR US": "Arecibo",
}
CORE_METRIC_NAMES = (
    "hot_days_32", "hot_days_35", "warm_nights_24", "oppressive_days",
    "hottest_month_index", "hottest_month_tmax", "hottest_month_tmin",
)
NEW_METRIC_NAMES = (
    "valid_days", "completeness_pct", "hot_day_pct", "warm_night_pct",
    "longest_hot_streak", "longest_warm_night_streak", "hot_days_32_anomaly",
    "warm_nights_24_anomaly", "hot_days_32_percentile",
    "warm_nights_24_percentile",
)
METRIC_NAMES = CORE_METRIC_NAMES + NEW_METRIC_NAMES


def fahrenheit_to_celsius(value):
    """Convert a Fahrenheit number or pandas Series to Celsius."""
    return (value - 32.0) * 5.0 / 9.0


def calendar_days_in_year(year: int) -> int:
    return 366 if isleap(year) else 365


def percentage(numerator: int, denominator: int) -> float | None:
    """Return a percentage, preserving missingness when no denominator exists."""
    return None if denominator == 0 else numerator * 100.0 / denominator


def longest_threshold_streak(year_data: pd.DataFrame, column: str, threshold: float) -> int:
    """Find a consecutive-calendar-day threshold streak; gaps and nulls reset it."""
    if "DATE" not in year_data:
        # Kept for backwards-compatible direct use with older, date-free inputs.
        dates = pd.Series(pd.date_range("2001-01-01", periods=len(year_data)))
        data = year_data.copy()
        data["DATE"] = dates
    else:
        data = year_data.copy()
    data = data.sort_values("DATE")
    longest = current = 0
    previous_date = None
    for row in data[["DATE", column]].itertuples(index=False):
        date, value = row
        consecutive = previous_date is not None and (date - previous_date).days == 1
        if not consecutive or pd.isna(value) or value < threshold:
            current = 0
        if not pd.isna(value) and value >= threshold:
            current = current + 1 if consecutive else 1
            longest = max(longest, current)
        previous_date = date
    return longest


def calculate_year_metrics(year_data: pd.DataFrame) -> dict | None:
    """Return metrics for one sufficiently complete station-year, otherwise None."""
    valid = year_data.dropna(subset=["TMAX_C", "TMIN_C"])
    valid_days = len(valid)
    if valid_days < MIN_DAYS_PER_YEAR:
        return None
    year = int(year_data["DATE"].iloc[0].year) if "DATE" in year_data else 2001
    hottest_month = int(valid.groupby("month")["TMAX_C"].mean().idxmax())
    monthly = valid.groupby("month").agg(tmax_mean=("TMAX_C", "mean"), tmin_mean=("TMIN_C", "mean"))
    hot_days = int((valid["TMAX_C"] >= HOT_DAY_32).sum())
    warm_nights = int((valid["TMIN_C"] >= WARM_NIGHT_24).sum())
    return {
        "hot_days_32": hot_days,
        "hot_days_35": int((valid["TMAX_C"] >= HOT_DAY_35).sum()),
        "warm_nights_24": warm_nights,
        "oppressive_days": int(((valid["TMAX_C"] >= HOT_DAY_32) & (valid["TMIN_C"] >= WARM_NIGHT_24)).sum()),
        "hottest_month_index": hottest_month,
        "hottest_month_tmax": float(monthly.loc[hottest_month, "tmax_mean"]),
        "hottest_month_tmin": float(monthly.loc[hottest_month, "tmin_mean"]),
        "valid_days": valid_days,
        "completeness_pct": percentage(valid_days, calendar_days_in_year(year)),
        "hot_day_pct": percentage(hot_days, valid_days),
        "warm_night_pct": percentage(warm_nights, valid_days),
        "longest_hot_streak": longest_threshold_streak(year_data, "TMAX_C", HOT_DAY_32),
        "longest_warm_night_streak": longest_threshold_streak(year_data, "TMIN_C", WARM_NIGHT_24),
    }


def anomaly(value: float, values: dict[str, float]) -> float | None:
    baseline = [v for y, v in values.items() if BASELINE_START_YEAR <= int(y) <= BASELINE_END_YEAR and v is not None]
    return None if len(baseline) < MIN_BASELINE_YEARS else value - sum(baseline) / len(baseline)


def historical_percentile(value: float, values: dict[str, float]) -> float | None:
    valid = [v for v in values.values() if v is not None]
    if len(valid) < MIN_PERCENTILE_YEARS:
        return None
    lower = sum(v < value for v in valid)
    equal = sum(v == value for v in valid)
    return 100.0 * (lower + 0.5 * equal) / len(valid)


def add_historical_metrics(metrics: dict[str, dict]) -> None:
    """Add station-relative context after all valid years have been calculated."""
    for source, anomaly_name, percentile_name in (
        ("hot_days_32", "hot_days_32_anomaly", "hot_days_32_percentile"),
        ("warm_nights_24", "warm_nights_24_anomaly", "warm_nights_24_percentile"),
    ):
        for year, value in metrics[source].items():
            metrics[anomaly_name][year] = anomaly(value, metrics[source])
            metrics[percentile_name][year] = historical_percentile(value, metrics[source])


def add_change_metrics(metrics: dict[str, dict]) -> None:
    """Preserve the dashboard's existing early-versus-late comparison fields."""
    def mean_for_range(values: dict[str, float], start: int, end: int) -> float | None:
        selected = [value for year, value in values.items() if start <= int(year) <= end and value is not None]
        return None if not selected else sum(selected) / len(selected)

    for source, target in (("hot_days_32", "delta_hot_days_32"), ("warm_nights_24", "delta_warm_nights_24")):
        early = mean_for_range(metrics[source], 1961, 1980)
        late = mean_for_range(metrics[source], 2006, 2025)
        if early is not None and late is not None:
            metrics[target] = {"late_minus_early": late - early}


def feature_collection(features: list[dict], source_filename: str | None = None, generated_at_utc: str | None = None) -> dict:
    """Build valid GeoJSON, including portable dataset-level provenance metadata."""
    result = {"type": "FeatureCollection", "features": features}
    if source_filename is not None:
        result.update({
            # A source-data marker is deterministic, so a no-change refresh
            # does not manufacture a generated-file diff solely from a clock.
            "generated_at_utc": generated_at_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source_filename": source_filename,
            "threshold_definitions": {"hot_day": "TMAX >= 32 C", "very_hot_day": "TMAX >= 35 C", "warm_night": "TMIN >= 24 C", "oppressive_day": "TMAX >= 32 C and TMIN >= 24 C (project-defined proxy)"},
            "minimum_valid_days": MIN_DAYS_PER_YEAR,
            "baseline_period": {"start": BASELINE_START_YEAR, "end": BASELINE_END_YEAR},
            "minimum_baseline_years": MIN_BASELINE_YEARS,
            "units": {"temperature": "degrees Celsius", "counts": "days or nights", "percentages": "percent"},
            "scientific_limitation": "Temperature-only observations cannot calculate official heat index, WBGT, or feels-like temperature; no humidity, wind, radiation, or cloud data are inferred.",
        })
    return result


def read_observations(input_csv: str) -> tuple[pd.DataFrame, str]:
    """Read one documented input CSV without station-specific side files.

    Canonical NOAA data declares ``UNITS=C``.  The pre-Phase-3 legacy export
    has no units column and is documented as Fahrenheit, so its conversion is
    explicit and never guessed from temperature magnitude.
    """
    input_path = Path(input_csv)
    return pd.read_csv(input_path, parse_dates=["DATE"]), input_path.name


def main(input_csv: str, output_geojson: str, *, current_year: int | None = None) -> None:
    df, source_filename = read_observations(input_csv)
    required = ["STATION", "NAME", "LATITUDE", "LONGITUDE", "DATE", "TMAX", "TMIN"]
    for column in required:
        if column not in df:
            raise SystemExit(f"Missing required column '{column}' in {input_csv}")
    unit_column = ["UNITS"] if "UNITS" in df else []
    df = df[required + unit_column].copy()
    if "UNITS" in df:
        declared_units = set(df["UNITS"].dropna().astype(str).str.upper())
        if declared_units != {"C"}:
            raise SystemExit("Canonical input must explicitly declare Celsius (UNITS=C)")
        df["TMAX_C"] = pd.to_numeric(df["TMAX"], errors="coerce")
        df["TMIN_C"] = pd.to_numeric(df["TMIN"], errors="coerce")
    else:
        # Legacy all_stations_1960_2025.csv is a known Fahrenheit export.
        df["TMAX_C"] = fahrenheit_to_celsius(pd.to_numeric(df["TMAX"], errors="coerce"))
        df["TMIN_C"] = fahrenheit_to_celsius(pd.to_numeric(df["TMIN"], errors="coerce"))
    df["year"] = df["DATE"].dt.year
    df["month"] = df["DATE"].dt.month
    current_year = datetime.now(timezone.utc).year if current_year is None else current_year
    # A partial calendar year must never appear among completed annual metrics.
    df = df[df["year"] != current_year].copy()
    features = []
    for station_id, station in df.groupby("STATION"):
        station = station.sort_values("DATE").copy()
        metrics = {metric: {} for metric in METRIC_NAMES}
        for year, year_data in station.groupby("year"):
            calculated = calculate_year_metrics(year_data)
            if calculated is not None:
                for metric, value in calculated.items():
                    metrics[metric][str(year)] = value
        if not metrics["hot_days_32"]:
            continue
        add_historical_metrics(metrics)
        add_change_metrics(metrics)
        years = sorted(int(year) for year in metrics["hot_days_32"])
        properties = {"id": station_id, "name": FRIENDLY_NAMES.get(station["NAME"].iloc[0], station["NAME"].iloc[0]), "country": "Puerto Rico", "data_start_year": years[0], "data_end_year": years[-1], "valid_year_count": len(years), "metrics": metrics}
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(station["LONGITUDE"].iloc[0]), float(station["LATITUDE"].iloc[0])]}, "properties": properties})
    with open(output_geojson, "w", encoding="utf-8") as output:
        source_marker = f"{df['DATE'].max().date().isoformat()}T00:00:00Z" if not df.empty else None
        json.dump(feature_collection(features, source_filename, source_marker), output, ensure_ascii=False, indent=2)
    print(f"Saved {len(features)} station(s) to {output_geojson}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 process_heatmetrics_multi.py input.csv output.geojson")
        raise SystemExit(1)
    main(sys.argv[1], sys.argv[2])
