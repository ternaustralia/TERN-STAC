"""ROI and spatial utility helpers."""

from __future__ import annotations

from typing import Iterable, Tuple

try:
    import xarray as xr  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    xr = None  # type: ignore


def _dataset_crs_str(dataset) -> str | None:
    """Best-effort extraction of dataset CRS as a string."""

    try:
        rio_crs = dataset.rio.crs
        if rio_crs is not None:
            return str(rio_crs)
    except Exception:
        pass

    try:
        odc_crs = dataset.odc.crs
        if odc_crs is not None:
            return str(odc_crs)
    except Exception:
        pass

    attrs = getattr(dataset, "attrs", {}) or {}
    if isinstance(attrs, dict):
        crs = attrs.get("crs")
        if crs:
            return str(crs)

    coords = getattr(dataset, "coords", {})
    try:
        spatial_ref = coords.get("spatial_ref")
    except Exception:
        spatial_ref = None
    if spatial_ref is not None:
        sr_attrs = getattr(spatial_ref, "attrs", {}) or {}
        for key in ("crs_wkt", "spatial_ref"):
            value = sr_attrs.get(key)
            if value:
                return str(value)

    return None


def spatial_slice(
    dataset,
    bounds: Tuple[float, float, float, float],
    *,
    x_dim: str = "x",
    y_dim: str = "y",
    bounds_crs: str | None = None,
):
    """Subset a raster-like xarray object by a bounds tuple.

    Parameters
    ----------
    dataset:
        xarray Dataset or DataArray.
    bounds:
        (minx, miny, maxx, maxy)
    bounds_crs:
        CRS of ``bounds`` (e.g. ``EPSG:4326``). If provided and different to
        dataset CRS, bounds are transformed before slicing.
    """

    if xr is None:
        raise ImportError(
            "xarray is not installed. Install with `pip install tern-stac[xarray]`"
        )

    minx, miny, maxx, maxy = bounds
    if bounds_crs is not None:
        data_crs_str = _dataset_crs_str(dataset)
        if data_crs_str is None:
            raise ValueError(
                "Could not determine dataset CRS for bounds transform. "
                "Provide bounds in dataset CRS, or ensure CRS metadata is available."
            )
        try:
            from rasterio.crs import CRS
            from rasterio.warp import transform
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "rasterio is required for bounds CRS transform. "
                "Install with `pip install tern-stac[rasterio]`"
            ) from exc

        if CRS.from_user_input(data_crs_str) != CRS.from_user_input(bounds_crs):
            # Transform explicit corner points to avoid axis-order ambiguity.
            xs, ys = transform(
                bounds_crs,
                data_crs_str,
                [minx, maxx, maxx, minx],
                [miny, miny, maxy, maxy],
            )
            minx, maxx = min(xs), max(xs)
            miny, maxy = min(ys), max(ys)

    y_descending = bool(dataset[y_dim][0] > dataset[y_dim][-1])

    if y_descending:
        out = dataset.sel(**{x_dim: slice(minx, maxx), y_dim: slice(maxy, miny)})
    else:
        out = dataset.sel(**{x_dim: slice(minx, maxx), y_dim: slice(miny, maxy)})

    if out.sizes.get(x_dim, 0) == 0 or out.sizes.get(y_dim, 0) == 0:
        raise ValueError(
            "Spatial slice returned no pixels. "
            "Check bounds values and bounds CRS against dataset CRS. "
            f"Dataset x/y extent: ({float(dataset[x_dim].min())}, {float(dataset[y_dim].min())}, "
            f"{float(dataset[x_dim].max())}, {float(dataset[y_dim].max())}). "
            f"Transformed bounds used: ({minx}, {miny}, {maxx}, {maxy})."
        )
    return out


def bounds_from_geodataframe(gdf) -> Tuple[float, float, float, float]:
    """Return global bounds from a GeoPandas GeoDataFrame-like object."""

    if not hasattr(gdf, "to_crs"):
        raise TypeError("Expected a GeoPandas GeoDataFrame-like object.")
    gdf = gdf.to_crs(gdf.crs) if hasattr(gdf, "to_crs") else gdf
    bounds = gdf.total_bounds
    if len(bounds) != 4:
        raise ValueError("Could not compute bounds from GeoDataFrame.")
    return tuple(float(v) for v in bounds)


def mean_over_dims(dataset, dims: Iterable[str] = ("x", "y"), *, skipna: bool = True):
    """Reduce an xarray object over spatial dimensions."""

    if xr is None:
        raise ImportError(
            "xarray is not installed. Install with `pip install tern-stac[xarray]`"
        )

    return dataset.mean(dim=tuple(dims), skipna=skipna)
