# Dashboard GeoJSON contract

`index.html` currently consumes `data/stations_heatmetrics_all.geojson`. It must be a GeoJSON `FeatureCollection` with a `features` array. Each station is a GeoJSON `Feature` with a `Point` geometry whose coordinates are `[longitude, latitude]` in WGS 84.

Each station feature requires these properties:

| Property | Type | Meaning |
| --- | --- | --- |
| `id` | string | Unique station identifier. |
| `name` | string | Human-readable station name. |
| `country` | string | Currently `Puerto Rico`. |
| `metrics` | object | Metric-name-to-year-values mapping. |

Station features also include `data_start_year`, `data_end_year`, and
`valid_year_count`. These describe only years that passed the 200-valid-pair
quality rule.

The annual metric names are `hot_days_32`, `hot_days_35`, `warm_nights_24`, `oppressive_days`, `hottest_month_index`, `hottest_month_tmax`, and `hottest_month_tmin`. Their values are objects keyed by a four-digit calendar year string, such as `"2020"`. The dashboard forms its year slider from the sorted union of these keys across all stations; a station can therefore be absent in a selected year.

`hot_days_32`, `hot_days_35`, `warm_nights_24`, and `oppressive_days` are counts in days (or nights for `warm_nights_24`). `hottest_month_index` is 1–12; the two hottest-month temperatures are degrees Celsius. A missing metric or year key means no available data and is rendered as no station marker, not as zero.

Only years with at least 200 daily records having both `TMAX` and `TMIN` are emitted. Temperatures are converted from the input Fahrenheit values. Thresholds are inclusive: hot day `Tmax >= 32 C`, very hot day `Tmax >= 35 C`, warm night `Tmin >= 24 C`. `oppressive_days` is the project-defined temperature proxy where both `Tmax >= 32 C` and `Tmin >= 24 C` on the same observation day.

The optional comparison metric keys `delta_hot_days_32` and `delta_warm_nights_24` contain `late_minus_early`, calculated as the annual-average difference between 2006–2025 (late) and 1961–1980 (early). They are counts of days per year.

## Human-centered annual metrics

The following additional metrics use the same year-string mapping as the core
metrics. `valid_days` is the number of dates with both a valid maximum and
minimum temperature. `completeness_pct` is `valid_days / calendar days in the
year * 100`, so leap years use 366 days and normal years use 365 days.
`hot_day_pct` and `warm_night_pct` are respectively hot days and warm nights
as a percentage of valid days. They are `null` when no valid days exist.

`longest_hot_streak` is the largest run of consecutive calendar dates with
`Tmax >= 32 C`; `longest_warm_night_streak` is the equivalent run with
`Tmin >= 24 C`. A missing calendar date or missing temperature observation
always breaks a streak.

`hot_days_32_anomaly` and `warm_nights_24_anomaly` are the selected year’s
count minus that station’s mean count in the 1991–2020 baseline. They are
`null` unless the station has at least 20 valid baseline years.

`hot_days_32_percentile` and `warm_nights_24_percentile` compare a selected
year with all valid years for that station. The calculation is
`100 * (lower values + 0.5 * equal values) / valid years`; it is `null` unless
at least 10 valid station-years exist. These percentiles provide historical
context only and are not medical-risk categories.

The FeatureCollection has portable metadata: UTC generation time, source file
name, thresholds, quality and baseline settings, units, and the scientific
limitation statement. No absolute machine paths are included.

These are temperature-only project metrics. They are not official heat index, WBGT, or official “feels-like temperature” measurements: the historical input does not supply the humidity, wind, solar radiation, or cloud observations needed for those calculations.

## Canonical raw observations and complete years

`data/raw/noaa_daily.csv` is the refresh pipeline's canonical raw format. It
uses the schema and explicit Celsius-unit rule documented in
[data provenance](data-provenance.md). A station/date is unique; a newer NOAA
record for that key replaces an older one. Rows are sorted by station ID then
date.

The map emits only completed calendar years. Downloaded observations for the
current calendar year are retained in canonical raw data, but are excluded from
the annual GeoJSON and summary, even if they happen to pass the 200 paired-day
minimum. This prevents partial year-to-date data from being compared or labeled
as a complete historical year.
