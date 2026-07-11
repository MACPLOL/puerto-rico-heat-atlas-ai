# Dashboard GeoJSON contract

`index.html` currently consumes `data/stations_heatmetrics_all.geojson`. It must be a GeoJSON `FeatureCollection` with a `features` array. Each station is a GeoJSON `Feature` with a `Point` geometry whose coordinates are `[longitude, latitude]` in WGS 84.

Each station feature requires these properties:

| Property | Type | Meaning |
| --- | --- | --- |
| `id` | string | Unique station identifier. |
| `name` | string | Human-readable station name. |
| `country` | string | Currently `Puerto Rico`. |
| `metrics` | object | Metric-name-to-year-values mapping. |

The annual metric names are `hot_days_32`, `hot_days_35`, `warm_nights_24`, `oppressive_days`, `hottest_month_index`, `hottest_month_tmax`, and `hottest_month_tmin`. Their values are objects keyed by a four-digit calendar year string, such as `"2020"`. The dashboard forms its year slider from the sorted union of these keys across all stations; a station can therefore be absent in a selected year.

`hot_days_32`, `hot_days_35`, `warm_nights_24`, and `oppressive_days` are counts in days (or nights for `warm_nights_24`). `hottest_month_index` is 1–12; the two hottest-month temperatures are degrees Celsius. A missing metric or year key means no available data and is rendered as no station marker, not as zero.

Only years with at least 200 daily records having both `TMAX` and `TMIN` are emitted. Temperatures are converted from the input Fahrenheit values. Thresholds are inclusive: hot day `Tmax >= 32 C`, very hot day `Tmax >= 35 C`, warm night `Tmin >= 24 C`. `oppressive_days` is the project-defined temperature proxy where both `Tmax >= 32 C` and `Tmin >= 24 C` on the same observation day.

The optional comparison metric keys `delta_hot_days_32` and `delta_warm_nights_24` contain `late_minus_early`, calculated as the annual-average difference between 2006–2025 (late) and 1961–1980 (early). They are counts of days per year.

These are temperature-only project metrics. They are not official heat index, WBGT, or official “feels-like temperature” measurements: the historical input does not supply the humidity, wind, solar radiation, or cloud observations needed for those calculations.
