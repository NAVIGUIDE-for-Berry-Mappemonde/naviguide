# Geospatial data (not in Git)

Large rasters are **not** committed to keep clones fast and repos within platform limits. After cloning, run the fetch script once from the **repository root**.

## Disk space (indicative)

| Asset | Approx. size |
|--------|----------------|
| GEBCO 2024 netCDF (`GEBCO_2024_CF.nc`) | ~7 GB |
| World Bank Global Ship Density (zip + extracted GeoTIFF + sidecars) | ~510 MB + overhead |

Reserve **~10 GB** free space to be safe.

## Prerequisites

- `bash`, `curl`, `unzip`
- Stable network (large downloads)

## Steps

### 1. Download AIS (automated) and prepare GEBCO (manual)

From the repo root:

```bash
chmod +x scripts/fetch_data.sh
./scripts/fetch_data.sh
```

This script:

- Creates `data/gebco/` and `data/ais_worldbank/`.
- Downloads and extracts the World Bank **Global Ship Density** zip into `data/ais_worldbank/`.
- If `data/gebco/GEBCO_2024_CF.nc` is missing, prints the official GEBCO download page — you must place the file manually (GEBCO does not always offer a stable direct `curl` URL).

**GEBCO:** download **[GEBCO 2024](https://www.gebco.net/data_and_products/gridded_bathymetry_data/gebco_2024/)** grid in netCDF form and save as:

`data/gebco/GEBCO_2024_CF.nc`

### 2. Verify layout

```bash
./scripts/fetch_data.sh --check-only
```

Expected:

- `data/gebco/GEBCO_2024_CF.nc`
- `data/ais_worldbank/shipdensity_global.tif` (and optional `.tfw`, `.aux.xml`, `.ovr` from extraction)

### 3. Berry-Mappemonde polar (already in Git)

Boat performance polars for the demo expedition are versioned as:

`naviguide_workspace/polar_data/polar_berry-mappemonde-2026.json`

No download step.

### 4. Run the stack locally

See [naviguide_workspace/start_local.sh](../naviguide_workspace/start_local.sh) and the main [README](../README.md) for Python/Node setup and service URLs.

## Legacy script name

`scripts/download_geodata.sh` is the implementation; `scripts/fetch_data.sh` is the preferred entry point and forwards all arguments.
