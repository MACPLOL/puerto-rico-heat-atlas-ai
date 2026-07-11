import csv
import sys, json
from pathlib import Path
import statistics as stats

EARLY_START = 1961
EARLY_END   = 1980     # inclusive
LATE_START  = 2006
LATE_END    = 2025

def mean_for_range(d, start, end):
    vals = []
    for y, v in d.items():
        y_int = int(y)
        if start <= y_int <= end and v is not None:
            vals.append(v)
    return stats.mean(vals) if vals else None

def main(geojson_path, out_csv):
    data = json.loads(Path(geojson_path).read_text(encoding="utf-8"))
    header = [
        "name", "id",
        "first_year", "last_year",
        "mean_hot32_early", "mean_hot32_late",
        "mean_warm24_early", "mean_warm24_late"
    ]
    with Path(out_csv).open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)
        for feat in data["features"]:
            props = feat["properties"]
            metrics = props["metrics"]
            hot32 = metrics.get("hot_days_32", {})
            warm24 = metrics.get("warm_nights_24", {})
            years = sorted(int(y) for y in hot32.keys())
            if not years:
                continue
            writer.writerow([
                props.get("name", ""), props.get("id", ""), years[0], years[-1],
                mean_for_range(hot32, EARLY_START, EARLY_END),
                mean_for_range(hot32, LATE_START, LATE_END),
                mean_for_range(warm24, EARLY_START, EARLY_END),
                mean_for_range(warm24, LATE_START, LATE_END),
            ])
    print(f"Saved summary to {out_csv}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 summarize_heatmetrics.py data/stations_heatmetrics_all.geojson output.csv")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
