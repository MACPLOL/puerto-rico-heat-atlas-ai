#!/usr/bin/env python3
import sys
import json
import pandas as pd

# Thresholds (°C)
HOT_DAY_32 = 32.0          # “hot day”
HOT_DAY_35 = 35.0          # “very hot day”
WARM_NIGHT_24 = 24.0       # “warm night”

# Quality filter
MIN_DAYS_PER_YEAR = 200    # require at least this many valid days in a year

# Stations to ignore completely (too short / messy records)
BAD_STATIONS = {
    "ADJUNTAS 2 NW, PR US",
    "MAYAGUEZ AIRPORT, PR US",
    "MAYAGUEZ ARRIBA, PR RQ",
}

# Nicer labels for some stations
FRIENDLY_NAMES = {
    "SAN JUAN L M MARIN INTERNATIONAL AIRPORT, PR US": "San Juan (Airport)",
    "PONCE 4 E, PR US": "Ponce",
    "MAYAGUEZ 1 O, PR US": "Mayagüez",
    "ROOSEVELT ROADS, PR US": "Ceiba (Roosevelt Roads)",
    "ARECIBO 3 ESE, PR US": "Arecibo",
    # add/edit as you like
}

METRIC_NAMES = (
    "hot_days_32",
    "hot_days_35",
    "warm_nights_24",
    "oppressive_days",
    "hottest_month_index",
    "hottest_month_tmax",
    "hottest_month_tmin",
)


def fahrenheit_to_celsius(value):
    """Convert a Fahrenheit number or pandas Series to Celsius."""
    return (value - 32.0) * 5.0 / 9.0


def calculate_year_metrics(year_data: pd.DataFrame) -> dict | None:
    """Return temperature-only metrics for one year, or None if incomplete."""
    valid = year_data.dropna(subset=["TMAX_C", "TMIN_C"])
    if len(valid) < MIN_DAYS_PER_YEAR:
        return None

    hottest_month = int(valid.groupby("month")["TMAX_C"].mean().idxmax())
    monthly = valid.groupby("month").agg(
        tmax_mean=("TMAX_C", "mean"),
        tmin_mean=("TMIN_C", "mean"),
    )
    return {
        "hot_days_32": int((valid["TMAX_C"] >= HOT_DAY_32).sum()),
        "hot_days_35": int((valid["TMAX_C"] >= HOT_DAY_35).sum()),
        "warm_nights_24": int((valid["TMIN_C"] >= WARM_NIGHT_24).sum()),
        "oppressive_days": int(
            ((valid["TMAX_C"] >= HOT_DAY_32) & (valid["TMIN_C"] >= WARM_NIGHT_24)).sum()
        ),
        "hottest_month_index": hottest_month,
        "hottest_month_tmax": float(monthly.loc[hottest_month, "tmax_mean"]),
        "hottest_month_tmin": float(monthly.loc[hottest_month, "tmin_mean"]),
    }


def feature_collection(features: list[dict]) -> dict:
    """Build the GeoJSON container used by the dashboard."""
    return {"type": "FeatureCollection", "features": features}


# ---------- MAIN LOGIC ----------

def main(input_csv: str, output_geojson: str) -> None:
    # Read CSV and parse DATE column as datetime
    df = pd.read_csv(input_csv, parse_dates=["DATE"])

    # Drop known-bad stations (by NAME)
    if "NAME" in df.columns:
        df = df[~df["NAME"].isin(BAD_STATIONS)].copy()

    # Keep only the columns we actually need
    required = ["STATION", "NAME", "LATITUDE", "LONGITUDE", "DATE", "TMAX", "TMIN"]
    for col in required:
        if col not in df.columns:
            raise SystemExit(f"Missing required column '{col}' in {input_csv}")

    df = df[required]

    # Convert Fahrenheit to Celsius (CDO “Standard” units are °F)
    df["TMAX_C"] = fahrenheit_to_celsius(df["TMAX"])
    df["TMIN_C"] = fahrenheit_to_celsius(df["TMIN"])

    # Precompute year and month
    df["year"] = df["DATE"].dt.year
    df["month"] = df["DATE"].dt.month

    features = []

    for station_id, g in df.groupby("STATION"):
        g = g.sort_values("DATE").copy()

        name_raw = g["NAME"].iloc[0]
        name = FRIENDLY_NAMES.get(name_raw, name_raw)
        lat = float(g["LATITUDE"].iloc[0])
        lon = float(g["LONGITUDE"].iloc[0])

        # metrics[metric_name][year_str] = value
        metrics = {name: {} for name in METRIC_NAMES}

        for year, gy in g.groupby("year"):
            year_metrics = calculate_year_metrics(gy)
            if year_metrics is None:
                continue
            year_str = str(year)
            for metric_name, value in year_metrics.items():
                metrics[metric_name][year_str] = value

        # If station has no valid years, skip it
        if not metrics["hot_days_32"]:
            continue

        # --- Early vs late change metrics (late minus early) ---
        early_start, early_end = 1961, 1980
        late_start, late_end = 2006, 2025

        def mean_for_range(values_dict, start, end):
            vals = []
            for y, v in values_dict.items():
                y_int = int(y)
                if start <= y_int <= end and v is not None:
                    vals.append(v)
            return sum(vals) / len(vals) if vals else None

        hot32_early = mean_for_range(metrics["hot_days_32"], early_start, early_end)
        hot32_late = mean_for_range(metrics["hot_days_32"], late_start, late_end)
        warm24_early = mean_for_range(metrics["warm_nights_24"], early_start, early_end)
        warm24_late = mean_for_range(metrics["warm_nights_24"], late_start, late_end)

        if hot32_early is not None and hot32_late is not None:
            metrics["delta_hot_days_32"] = {"late_minus_early": hot32_late - hot32_early}
        if warm24_early is not None and warm24_late is not None:
            metrics["delta_warm_nights_24"] = {"late_minus_early": warm24_late - warm24_early}

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
                "properties": {
                    "id": station_id,
                    "name": name,
                    "country": "Puerto Rico",
                    "metrics": metrics,
                },
            }
        )

    fc = feature_collection(features)

    with open(output_geojson, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(features)} station(s) to {output_geojson}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 process_heatmetrics_multi.py input.csv output.geojson")
        raise SystemExit(1)

    main(sys.argv[1], sys.argv[2])
