"""Optional stackstac integrations for lazy STAC raster workflows."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from .auth import is_http_401_error, warn_auth_required


def load_items_stackstac(
    items: Sequence[Any],
    *,
    assets: Optional[Sequence[str]] = None,
    epsg: Optional[int] = None,
    resolution: Optional[float] = None,
    bounds: Optional[tuple[float, float, float, float]] = None,
    bounds_latlon: Optional[tuple[float, float, float, float]] = None,
    chunksize: int | tuple[int, int, int, int] = 1024,
    xy_coords: str = "topleft",
    sortby_date: str | bool = "asc",
    rescale: bool = True,
    fill_value: Any = None,
    dtype: Any = None,
    **kwargs: Any,
):
    """Create a lazy Dask-backed ``xarray.DataArray`` from STAC items.

    This wraps ``stackstac.stack`` while keeping dependency optional.
    """

    if not items:
        raise ValueError("No items provided.")
    if bounds is not None and bounds_latlon is not None:
        raise ValueError("Pass only one of `bounds` or `bounds_latlon`.")

    try:
        import stackstac
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "stackstac is not installed. Install with `pip install tern-stac[stackstac]`"
        ) from exc

    params = {
        "assets": assets,
        "epsg": epsg,
        "resolution": resolution,
        "bounds": bounds,
        "bounds_latlon": bounds_latlon,
        "chunksize": chunksize,
        "xy_coords": xy_coords,
        "sortby_date": sortby_date,
        "rescale": rescale,
    }
    if fill_value is not None:
        params["fill_value"] = fill_value
    if dtype is not None:
        params["dtype"] = dtype
    params.update(kwargs)
    params = {k: v for k, v in params.items() if v is not None}
    try:
        return stackstac.stack(items, **params)
    except Exception as exc:
        if is_http_401_error(exc):
            warn_auth_required(context="load_items_stackstac")
            return None
        raise


def mosaic_time(
    arr,
    *,
    reverse: bool = False,
    nodata: Any = None,
    split_every: Optional[int] = None,
):
    """Mosaic a stackstac DataArray along time."""

    try:
        import stackstac
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "stackstac is not installed. Install with `pip install tern-stac[stackstac]`"
        ) from exc

    params = {"reverse": reverse}
    if nodata is not None:
        params["nodata"] = nodata
    if split_every is not None:
        params["split_every"] = split_every
    try:
        return stackstac.mosaic(arr, **params)
    except Exception as exc:
        if is_http_401_error(exc):
            warn_auth_required(context="mosaic_time")
            return None
        raise


def get_array_bounds(arr, *, to_epsg: Optional[int] = None):
    """Return bounds for a stackstac array, optionally transformed to another EPSG."""

    try:
        import stackstac
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "stackstac is not installed. Install with `pip install tern-stac[stackstac]`"
        ) from exc

    if to_epsg is None:
        return stackstac.array_bounds(arr)
    return stackstac.array_bounds(arr, to_epsg=to_epsg)


def get_array_epsg(arr, *, default: Optional[int] = None):
    """Return EPSG from a stackstac array."""

    try:
        import stackstac
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "stackstac is not installed. Install with `pip install tern-stac[stackstac]`"
        ) from exc

    try:
        return stackstac.array_epsg(arr)
    except Exception:
        return default
