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
