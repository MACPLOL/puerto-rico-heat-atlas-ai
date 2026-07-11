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
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[test]"
```

## Refresh historical NOAA data

Historical temperature data comes from the official NOAA/NCEI Daily Summaries
Access Data Service. `data/stations.json` is the single registry for the seven
published stations, including San Juan Airport. The canonical raw file is
`data/raw/noaa_daily.csv`, whose temperatures explicitly use Celsius and whose
NOAA quality attributes are retained where available. See
[data provenance](docs/data-provenance.md).

Run a complete staged refresh (downloads, validation, tests, GeoJSON, and
summary CSV):

```bash
python3 scripts/refresh_data.py
```

Use a dry run to download and validate without changing tracked data files:

```bash
python3 scripts/refresh_data.py --dry-run
```

For an intentional historical redownload, use `--full-refresh`. To update one
station, use its ID from `data/stations.json`, for example:

```bash
python3 scripts/refresh_data.py --station RQW00011641
python3 scripts/refresh_data.py --full-refresh
```

Ordinary downloads begin 14 days before each station's newest stored date.
That overlap lets corrected NOAA records replace prior rows with the same
station/date while retaining all older rows. The overlap is configurable with
`--overlap-days`. The current calendar year's observations are stored, but are
not emitted as completed annual dashboard metrics or compared with complete
years.

The scripts fail clearly for malformed dates or responses, unknown stations,
empty data, unexpected schema, duplicates, unreasonable temperatures, and HTTP
errors. Check your connection and retry a temporary NOAA failure; do not
substitute an unofficial weather source. If a bad update reaches a branch,
revert its data commit (or restore the three generated files from the previous
commit), then rerun a dry refresh before trying again.

To propose a new station, run `python3 scripts/discover_noaa_stations.py` for
a report, review coverage and duplication, then add a complete entry to
`data/stations.json`. Discovery never publishes a station automatically.

## Scheduled refreshes

GitHub Actions runs `.github/workflows/refresh-historical-data.yml` weekly and
can also be started manually. It tests the project, runs the staged refresh,
and exits without a commit if no generated data changed. Otherwise it commits
only canonical/raw and generated data files on a dedicated branch and opens a
pull request against `main`; it never force-pushes or commits directly to
`main`.

In the repository's **Settings → Actions → General → Workflow permissions**,
select **Read and write permissions** and enable **Allow GitHub Actions to
create and approve pull requests**. The workflow uses the built-in
`GITHUB_TOKEN`; no NOAA token or other secret is required.

## Legacy rebuild command

The checked-in dashboard reads `data/stations_heatmetrics_all.geojson`. To recreate it from the supplied raw data:

```bash
python3 process_heatmetrics_multi.py \
  data/all_stations_1960_2025.csv \
  data/stations_heatmetrics_all.geojson
python3 summarize_heatmetrics.py \
  data/stations_heatmetrics_all.geojson \
  data/station_summary.csv
```

The pipeline requires at least 200 valid daily maximum/minimum-temperature pairs in a station-year. It also reports calendar-day data completeness (365 or 366 days), percentages among valid observation days, and longest hot/warm-night streaks; missing dates and missing readings break a streak. Station-relative anomalies use the 1991–2020 baseline and require 20 valid baseline years. Historical percentiles use all valid station-years, half-weight ties, and require 10 valid years; unavailable context is stored as `null`. Review generated changes before committing them.

The old `data/all_stations_1960_2025.csv` and San Juan-only export are retained
as archives, not active pipeline inputs. The one-time explicit migration helper
is `python3 scripts/bootstrap_legacy_raw.py`; normal refreshes use NOAA and do
not maintain a San Juan special case.

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
