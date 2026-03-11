# TERN STAC

Python wrapper around `pystac-client` with TERN STAC defaults and convenience loaders
for **rasterio**, **xarray**, and **geopandas**.

## Install

```bash
pip install tern-stac
```

Optional dependency extras:

```bash
pip install tern-stac[rasterio]
pip install tern-stac[xarray]
pip install tern-stac[geopandas]
pip install tern-stac[odc]
pip install tern-stac[plot]
pip install tern-stac[lidar]
pip install tern-stac[all]
```

## Usage

```python
from tern_stac import TernStacClient
from tern_stac.client import load_from_tern

# Uses the fixed TERN endpoint by default.
client = TernStacClient()
# Or override with an env var:
# export TERN_STAC_URL="https://your.tern.stac.endpoint"

# Search collections/items (STAC API style)
items = client.search(collections=["TERN"])
first_item = next(items.items())

# Load raster asset by key
with client.load_rasterio(first_item, asset_key="rgb") as ds:
    arr = ds.read(1)

# Directly load into xarray (via rioxarray)
xda = client.load_xarray(first_item, asset_key="rgb")

# Directly load vector-style asset into geopandas
gdf = client.load_geodataframe(first_item, asset_key="geometry")
```

## Direct helpers

```python
ds = load_from_tern("https://example.com/some.tif", backend="rasterio")
```

## STAC asset helpers

## Examples

Run one of the API examples:

```bash
python examples/imagery_api_workflow.py
python examples/fractional_cover_api_workflow.py
python examples/lidar_chm_api_workflow.py
```

Each script uses the TERN STAC API via `TernStacClient` and contains placeholder collection/item identifiers that you can swap in.

```python
from tern_stac import TernStacClient

client = TernStacClient()
search = client.search(collections=["<collection_id>"])
items = list(search.items())
print(len(items))
```

```python
from tern_stac import get_item_asset_href, load_items_as_time_series, load_items_odc

asset = get_item_asset_href(item, media_type="application/xml", role="data")

# Load many rasterio-compatible items into a time-indexed xarray object
ts = load_items_as_time_series(
    items,
    media_type="application/xml",
    role="data",
    chunks=True,
)

# Load many items with odc-stac (multi-band / grouped loading)
ds = load_items_odc(items, bands=["b5", "b4", "b3"], crs="utm", groupby="solar_day")
```

## ROI and reduction helpers

```python
from tern_stac import bounds_from_geodataframe, spatial_slice, mean_over_dims

bounds = bounds_from_geodataframe(region_gdf)

roi = spatial_slice(ds, bounds=bounds)
mean_by_time = mean_over_dims(roi, dims=("x", "y"))
```

## LiDAR helper

```python
from tern_stac import laz_to_canopy_height

chm = laz_to_canopy_height("https://data.tern.org.au/uas/dronescape/..../file.copc.laz")
```

## Quick plotting utilities

```python
from tern_stac import preview_raster, plot_time_series, explore_odc

# Plot a single band/time scene
preview_raster(ds, band=0, save_path="preview.png")

# Plot region-mean time series
plot_time_series(ts, figsize=(12, 4))

# Interactive map via odc.explore (when odc-geo is available)
explore_odc(ds, band=0)
```

## Build and release

### GitHub

```bash
git init
git add .
git commit -m "Initial TERN STAC wrapper"
git remote add origin https://github.com/<org>/TERN-STAC.git
git push -u origin main
```

Create a dedicated test branch:

```bash
git checkout -b test
git push -u origin test
```

### PyPI (manual)

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

### GitHub Actions for releases

Tag strategy used by the workflow:

- `vX.Y.Z` → publishes to PyPI
- `test-X.Y.Z` → publishes to TestPyPI

Version is now provided automatically from git tags by `setuptools_scm`; you no longer need to manually edit `src/tern_stac/_version.py`.

Example for test branch release:

```bash
git checkout test
git tag test-0.1.0
git push origin test-0.1.0
```

Example for production release:

```bash
git checkout main
git tag v0.1.0
git push origin v0.1.0
```

### GitHub Actions (included)

The workflow in `.github/workflows/publish.yml` publishes automatically with OpenID Connect:
- `v*` tags → PyPI
- `test-*` tags → TestPyPI

## License

MIT
