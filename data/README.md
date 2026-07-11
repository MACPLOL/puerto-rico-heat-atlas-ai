# Data folder

This folder holds the datasets used by the Caribbean Heat Stress Atlas project. The files are kept small and focused so it is clear which ones drive the map and which ones are raw inputs.

## Primary inputs
- `data/raw/noaa_daily.csv`: Canonical Celsius daily observations used by the refresh pipeline and map outputs.
- `data/stations.json`: The seven-station NOAA registry used for downloads and map coverage validation.
- `data/all_stations_1960_2025.csv`: Pre-refresh Fahrenheit archive retained for provenance only.

## Derived outputs (used by the web map)
- `data/stations_heatmetrics_all.geojson`: Per-station, per-year heat metrics used by `index.html`.
- `data/stations_heatmetrics.geojson`: A smaller or earlier version of the heat metrics output.
- `data/stations_all_hotdays.geojson`: Hot-day counts per station.
- `data/stations_multi_hotdays.geojson`: Hot-day counts across multiple stations.
- `data/stations_multi_hotdays_filtered.geojson`: Filtered version of the multi-station hot-day dataset.
- `data/stations_san_juan_heatmetrics.geojson`: Heat metrics focused on the San Juan station.
- `data/stations_san_juan_hotdays.geojson`: Hot-day counts focused on the San Juan station.
- `data/stations_example.geojson`: Example subset for testing or demo use.
- `data/station_summary.csv`: Summary table created from the metrics.
- `data/pr_boundary.geojson`: Puerto Rico boundary used for the map overlay.

## Raw inputs
- `data/raw/`: Raw, unprocessed files kept for reference or reruns.
  - `data/raw/san_juan_1960_2025.csv`: Legacy San Juan Fahrenheit archive retained for provenance only; the refresh pipeline does not read it.

## Regeneration
Use `python3 scripts/refresh_data.py` to stage, validate, and atomically replace the canonical data and generated map outputs. See the root README for dry-run, full-refresh, and recovery commands.
