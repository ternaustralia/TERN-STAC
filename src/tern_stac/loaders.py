"""Higher-level loaders for STAC-derived data workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable, List, Optional, Sequence

from .auth import is_http_401_error, warn_auth_required

try:
    import xarray as xr  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    xr = None  # type: ignore


def _coerce_href(obj: Any) -> Optional[str]:
    """Best-effort extraction of an href from common STAC-like objects."""

    if isinstance(obj, str):
        return obj

    href = getattr(obj, "href", None)
    if isinstance(href, str):
        return href

    if isinstance(obj, dict):
        nested_href = obj.get("href")
        if isinstance(nested_href, str):
            return nested_href

    return None


def get_item_asset_href(
    item: Any,
    *,
    asset_key: Optional[str] = None,
    media_type: Optional[str] = None,
    role: Optional[str] = None,
) -> str:
    """Resolve one asset href from a STAC item.

    Parameters
    ----------
    item:
        STAC item object or asset-like object.
    asset_key:
        Optional explicit asset key.
    media_type:
        Optional media type filter.
    role:
        Optional role filter.
    """

    if asset_key is None and isinstance(item, str):
        return item

    if asset_key is None:
        href = _coerce_href(item)
        if href is not None:
            return href

    assets = None
    if item is not None:
        assets = getattr(item, "assets", None)
        if assets is None and isinstance(item, dict):
            assets = item.get("assets")

    if assets is None:
        raise TypeError("Expected STAC item/dict with assets or direct URL.")

    if not isinstance(assets, dict):
        raise TypeError("Expected STAC item assets to be a mapping.")

    if asset_key is not None:
        if asset_key not in assets:
            raise KeyError(f"Asset '{asset_key}' not found")
        asset = assets[asset_key]
        href = _coerce_href(asset)
        if href is None:
            raise TypeError(f"Asset '{asset_key}' does not provide an href")
        return href

    candidates: List[Any] = list(assets.values())
    if media_type is not None:
        candidates = [
            asset
            for asset in candidates
            if getattr(asset, "media_type", None) == media_type
            or (isinstance(asset, dict) and asset.get("media_type") == media_type)
        ]
    if role is not None:
        filtered: List[Any] = []
        for asset in candidates:
            asset_roles = getattr(asset, "roles", None)
            if asset_roles is None and isinstance(asset, dict):
                asset_roles = asset.get("roles")
            if isinstance(asset_roles, str):
                has_role = asset_roles == role
            elif isinstance(asset_roles, Iterable):
                has_role = role in list(asset_roles)
            else:
                has_role = False
            if has_role:
                filtered.append(asset)
        candidates = filtered

    hrefs = []
    for asset in candidates:
        href = _coerce_href(asset)
        if href is not None:
            hrefs.append(href)

    if not hrefs:
        raise KeyError("No matching asset found for given filters.")
    if len(hrefs) > 1:
        raise ValueError("Multiple matching assets found; pass asset_key explicitly.")

    return hrefs[0]


def _item_datetime(item: Any, *, key: str = "datetime") -> datetime:
    value = None
    if isinstance(item, dict):
        value = item.get("properties", {}).get(key)
        if value is None:
            value = item.get(key)
    else:
        props = getattr(item, "properties", None)
        if isinstance(props, dict):
            value = props.get(key)
    if value is None:
        value = getattr(item, key, None)
    if isinstance(value, datetime):
        return value
    if value is None:
        raise ValueError(f"Item is missing datetime field '{key}'")
    normalized = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return parsed.replace(tzinfo=None)


def load_items_odc(
    items: Sequence[Any],
    *,
    bands: Optional[Sequence[str]] = None,
    crs: str = "utm",
    groupby: Optional[str] = "solar_day",
    resolution: Optional[float] = None,
    chunks: Any = {},
    **kwargs: Any,
):
    """Load multiple STAC items with ``odc.stac.load``.

    This mirrors common demo patterns from the DroneScape imagery notebook.
    """

    try:
        from odc.stac import load
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "odc-stac is not installed. Install with `pip install tern-stac[odc]`"
        ) from exc

    params = {
        "bands": bands,
        "crs": crs,
        "chunks": chunks,
    }
    if groupby is not None:
        params["groupby"] = groupby
    if resolution is not None:
        params["resolution"] = resolution
    params.update(kwargs)
    params = {k: v for k, v in params.items() if v is not None}
    try:
        return load(items, **params)
    except Exception as exc:
        if is_http_401_error(exc):
            warn_auth_required(context="load_items_odc")
            return None
        raise


def load_items_as_time_series(
    items: Sequence[Any],
    *,
    media_type: str = "application/xml",
    role: Optional[str] = None,
    asset_key: Optional[str] = None,
    time_key: str = "datetime",
    chunks: Any = True,
    clip_bounds: Optional[tuple[float, float, float, float]] = None,
    clip_bounds_crs: Optional[str] = None,
    to_numpy_nodata: bool = False,
    preprocess: Optional[Callable[[Any, Any], Any]] = None,
):
    """Open per-item raster assets with ``rioxarray.open_rasterio`` and concat on time."""

    if xr is None:
        raise ImportError(
            "xarray is not installed. Install with `pip install tern-stac[xarray]`"
        )

    try:
        import rioxarray as rxr
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "rioxarray is not installed. Install with `pip install tern-stac[xarray]`"
        ) from exc

    datasets = []
    for item in items:
        href = get_item_asset_href(
            item, asset_key=asset_key, media_type=media_type, role=role
        )
        try:
            ds = rxr.open_rasterio(href, chunks=chunks)
        except Exception as exc:
            if is_http_401_error(exc):
                warn_auth_required(context="load_items_as_time_series")
                continue
            raise

        if clip_bounds is not None:
            minx, miny, maxx, maxy = clip_bounds
            if clip_bounds_crs is not None:
                try:
                    data_crs = ds.rio.crs
                except Exception:
                    data_crs = None
                if data_crs is not None:
                    data_crs_str = str(data_crs)
                    if data_crs_str.upper() != clip_bounds_crs.upper():
                        try:
                            from rasterio.warp import transform_bounds
                        except Exception as exc:  # pragma: no cover
                            raise ImportError(
                                "rasterio is required for clip_bounds CRS transform. "
                                "Install with `pip install tern-stac[xarray]`"
                            ) from exc
                        minx, miny, maxx, maxy = transform_bounds(
                            clip_bounds_crs,
                            data_crs_str,
                            minx,
                            miny,
                            maxx,
                            maxy,
                            densify_pts=21,
                        )
            y_coord_desc = ds.y[0] > ds.y[-1]
            if y_coord_desc:
                ds = ds.sel(x=slice(minx, maxx), y=slice(maxy, miny))
            else:
                ds = ds.sel(x=slice(minx, maxx), y=slice(miny, maxy))

        if to_numpy_nodata:
            try:
                ds = ds.where(ds != ds.rio.nodata, float("nan"))
            except Exception:
                pass

        if preprocess is not None:
            ds = preprocess(ds, item)

        ds = ds.assign_coords(time=_item_datetime(item, key=time_key))
        datasets.append(ds)

    if not datasets:
        raise ValueError(
            "No datasets were loaded; check input items/asset filters, "
            "or verify authentication for protected asset URLs."
        )

    return xr.concat(sorted(datasets, key=lambda d: d.time.values.item()), dim="time")


# Re-export stackstac loader from this module for discoverability alongside the
# existing rioxarray-based `load_items_as_time_series` helper.
from .stackstac_utils import load_items_stackstac  # noqa: E402,F401
