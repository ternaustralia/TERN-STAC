"""ROI and spatial utility helpers."""

from __future__ import annotations

from typing import Iterable, Tuple

try:
    import xarray as xr  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    xr = None  # type: ignore


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
        data_crs = None
        try:
            data_crs = dataset.rio.crs
        except Exception:
            data_crs = None
        if data_crs is not None:
            data_crs_str = str(data_crs)
            if data_crs_str.upper() != bounds_crs.upper():
                try:
                    from rasterio.warp import transform_bounds
                except Exception as exc:  # pragma: no cover
                    raise ImportError(
                        "rasterio is required for bounds CRS transform. "
                        "Install with `pip install tern-stac[rasterio]`"
                    ) from exc
                minx, miny, maxx, maxy = transform_bounds(
                    bounds_crs,
                    data_crs_str,
                    minx,
                    miny,
                    maxx,
                    maxy,
                    densify_pts=21,
                )

    y_descending = bool(dataset[y_dim][0] > dataset[y_dim][-1])

    if y_descending:
        out = dataset.sel(**{x_dim: slice(minx, maxx), y_dim: slice(maxy, miny)})
    else:
        out = dataset.sel(**{x_dim: slice(minx, maxx), y_dim: slice(miny, maxy)})

    if out.sizes.get(x_dim, 0) == 0 or out.sizes.get(y_dim, 0) == 0:
        raise ValueError(
            "Spatial slice returned no pixels. "
            "Check bounds values and bounds CRS against dataset CRS."
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
