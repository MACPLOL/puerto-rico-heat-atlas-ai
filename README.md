# Puerto Rico Heat Atlas

A static, map-based dashboard for exploring historical temperature-only heat metrics at Puerto Rico weather stations. It uses daily station maximum and minimum temperatures to show hot days, very hot days, warm nights, and a project-defined `oppressive_days` temperature proxy.

These are not official heat index, WBGT, or “feels-like” values. The historical data has no humidity, wind, solar-radiation, or cloud observations for those calculations. See [the data schema](docs/data-schema.md) for thresholds, data-quality rules, and units.

## First-time setup

You need Python 3.10 or newer. From the project folder, create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the processing and test dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

## Rebuild the dashboard data

The checked-in dashboard reads `data/stations_heatmetrics_all.geojson`. To recreate it from the supplied raw data:

```bash
python process_heatmetrics_multi.py \
  data/all_stations_1960_2025.csv \
  data/stations_heatmetrics_all.geojson
python summarize_heatmetrics.py \
  data/stations_heatmetrics_all.geojson \
  data/station_summary.csv
```

The pipeline requires at least 200 valid daily maximum/minimum-temperature pairs in a station-year. It also reports calendar-day data completeness (365 or 366 days), percentages among valid observation days, and longest hot/warm-night streaks; missing dates and missing readings break a streak. Station-relative anomalies use the 1991–2020 baseline and require 20 valid baseline years. Historical percentiles use all valid station-years, half-weight ties, and require 10 valid years; unavailable context is stored as `null`. Review generated changes before committing them.

The aggregate export omits the published San Juan Airport station, so the pipeline automatically includes the supplied `data/raw/san_juan_1960_2025.csv` supplemental export when rebuilding from `all_stations_1960_2025.csv`. This preserves the seven-station dashboard coverage; both source filenames are recorded in the generated metadata.

The source has only daily maximum and minimum temperatures. It cannot support official heat index, WBGT, or feels-like estimates, because humidity, wind, radiation, and cloud data are not present. `oppressive_days` remains a project-defined temperature proxy.

## Run the tests

With the virtual environment active:

```bash
pytest
```

## Open the dashboard locally

Browsers block local file requests, so serve the project instead of opening `index.html` directly:

```bash
python -m http.server 8000
```

Open <http://localhost:8000> in a browser. Stop the server with `Ctrl+C` when finished.

For a quick manual map check:

1. Confirm that Puerto Rico’s boundary and station markers load and that only one **Time** year slider appears.
2. Move the slider and choose each metric; stations without data for a selected year should disappear without an error.
3. Press **Play** and then **Pause**. Open a station marker to confirm its popup and trend chart render.
4. Change temperature units and use **Reset view** to confirm the controls still work.

## Repository layout

- `index.html` — static Leaflet and Chart.js dashboard.
- `process_heatmetrics_multi.py` — primary temperature-metric GeoJSON pipeline.
- `summarize_heatmetrics.py` — CSV summary generator.
- `data/` — source data, boundary, and derived GeoJSON.
- `tests/` — focused Python pipeline tests.
- `docs/data-schema.md` — canonical map-data contract.
- `docs/legacy-files.md` — overlapping and legacy outputs kept for review.
