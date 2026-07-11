# Historical-data provenance and refresh

The historical dashboard uses daily maximum (`TMAX`) and minimum (`TMIN`)
temperature records from the official [NOAA/NCEI Access Data Service Daily
Summaries dataset](https://www.ncei.noaa.gov/access/services/data/v1), requested
with `dataset=daily-summaries`, `format=json`, `units=metric`, and
`includeAttributes=true`. This is an API endpoint, not a scraped web page.

`data/stations.json` is the authoritative registry of the seven published
stations. It records each canonical NOAA station ID, map name and coordinates,
elevation, source dataset, active refresh status, publication status, and any
station note. San Juan Airport (`RQW00011641`) is an ordinary registry entry;
there is no application special case or ongoing supplemental San Juan input.

`data/raw/noaa_daily.csv` is the canonical raw observation format. Its required
columns are `STATION`, `NAME`, `LATITUDE`, `LONGITUDE`, `ELEVATION`, `DATE`,
`TMAX`, `TMIN`, `TMAX_ATTRIBUTES`, `TMIN_ATTRIBUTES`, `UNITS`, and `SOURCE`.
All temperatures in this file are Celsius and `UNITS` must explicitly be `C`.
Blank `TMAX` or `TMIN` means missing, never zero. NOAA quality attributes are
retained when supplied.

The initial canonical file was explicitly migrated from the previous checked-in
Fahrenheit exports, including `data/raw/san_juan_1960_2025.csv`. That temporary
legacy file is retained only as an archival provenance input; it is not read by
the refresh or map-processing pipeline. NOAA refreshes replace matching
station/date rows, so any old San Juan record is deduplicated through exactly
the same key rule as every other station. It can be removed in a later cleanup
after a reviewed full NOAA refresh provides equivalent coverage.

The dashboard remains temperature-only. It does not calculate official heat
index, WBGT, or feels-like temperature, and does not infer humidity, wind,
solar radiation, or cloud observations.
