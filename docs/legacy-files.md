# Legacy and overlapping data files

The active dashboard data source is `data/stations_heatmetrics_all.geojson`; `index.html` also loads `data/pr_boundary.geojson`. No other GeoJSON file is loaded by the main application.

| File | Active use | Schema / purpose | Recommendation |
| --- | --- | --- | --- |
| `data/stations_heatmetrics_all.geojson` | Active | Station points with `id`, `name`, `country`, and annual `metrics`. | Keep as canonical output. |
| `data/pr_boundary.geojson` | Active | Boundary FeatureCollection, with polygon geometry and `name`. | Keep. |
| `data/stations_heatmetrics.geojson` | Not active | Earlier six-station version of the `metrics` schema. | Archive after confirming it is superseded. |
| `data/stations_san_juan_heatmetrics.geojson` | Not active | One-station subset of the `metrics` schema. | Archive or retain as a small fixture. |
| `data/stations_all_hotdays.geojson` | Not active | Point features with `station_id`, `name`, `country`, and annual `values`. | Archive; legacy schema differs from the dashboard contract. |
| `data/stations_multi_hotdays.geojson` | Not active | Multi-station `values` schema. | Archive after provenance review. |
| `data/stations_multi_hotdays_filtered.geojson` | Not active | Filtered `values` schema. | Archive after provenance review. |
| `data/stations_san_juan_hotdays.geojson` | Not active | San Juan-only `values` schema. | Archive or retain as a fixture. |
| `data/stations_example.geojson` | Not active | Example point features with annual `values`. | Retain only as a documented example or test fixture. |

Related scripts are likewise overlapping: `process_heatmetrics_multi.py` produces the active metrics schema; `summarize_heatmetrics.py` summarizes it. `process_hotdays_multi.py` and `process_hotdays_ghcnd.py` produce the older `values` schema, while `merge_hotdays_geojson.py` and `filter_hotdays_stations.py` manipulate that schema. `merge_heatmetrics_geojson.py` merges metrics files but is not part of the documented primary pipeline. `plot_station_timeseries.py` reads the metrics schema and is a useful optional validation tool. Do not remove any of these files until a later archival decision is approved.
