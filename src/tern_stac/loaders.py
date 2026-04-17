"""Higher-level loaders for STAC-derived data workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable, List, Optional, Sequence

from .auth import is_http_401_error, warn_auth_required

try:
    import xarray as xr  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    xr = None  # type: ignore


def _geometry_bounds(geom_json: Any) -> Optional[tuple[float, float, float, float]]:
    """Compute bounds from a GeoJSON-like geometry mapping."""

    if not isinstance(geom_json, dict):
        return None

    bbox = geom_json.get("bbox")
    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
        try:
            return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        except Exception:
            pass

    coords = geom_json.get("coordinates")
    if coords is None:
        return None

    xs: list[float] = []
    ys: list[float] = []

    def _walk(node: Any) -> None:
        if isinstance(node, (list, tuple)):
            if (
                len(node) >= 2
                and isinstance(node[0], (int, float))
                and isinstance(node[1], (int, float))
            ):
                xs.append(float(node[0]))
                ys.append(float(node[1]))
            else:
                for child in node:
                    _walk(child)

    _walk(coords)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _point_in_bounds(
    point_xy: tuple[float, float], bounds: tuple[float, float, float, float]
) -> bool:
    x, y = point_xy
    minx, miny, maxx, maxy = bounds
    return minx <= x <= maxx and miny <= y <= maxy


def _bounds_intersect(
    lhs: tuple[float, float, float, float], rhs: tuple[float, float, float, float]
) -> bool:
    lminx, lminy, lmaxx, lmaxy = lhs
    rminx, rminy, rmaxx, rmaxy = rhs
    return not (lmaxx < rminx or rmaxx < lminx or lmaxy < rminy or rmaxy < lminy)


def _crs_equal(lhs: str, rhs: str) -> bool:
    try:
        from rasterio.crs import CRS

        return CRS.from_user_input(lhs) == CRS.from_user_input(rhs)
    except Exception:
        return str(lhs).upper() == str(rhs).upper()


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
    media_type: Optional[str] = None,
    role: Optional[str] = None,
    asset_key: Optional[str] = None,
    time_key: str = "datetime",
    chunks: Any = True,
    clip_bounds: Optional[tuple[float, float, float, float]] = None,
    clip_bounds_crs: Optional[str] = None,
    point: Optional[tuple[float, float]] = None,
    point_crs: str = "EPSG:4326",
    point_method: str = "nearest",
    to_numpy_nodata: bool = False,
    preprocess: Optional[Callable[[Any, Any], Any]] = None,
):
    """Open per-item raster assets with ``rioxarray.open_rasterio`` and concat on time.

    Defaults:
    - if ``clip_bounds`` is provided and ``preprocess`` is omitted, each item is reduced
      by spatial mean over ``x``/``y``.
    - if ``point`` is provided and ``preprocess`` is omitted, each item is sampled at
      the given coordinate (transformed from ``point_crs`` to data CRS when needed).
    """

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

    if point is not None and clip_bounds is not None:
        raise ValueError("Pass either `clip_bounds` or `point`, not both.")

    effective_preprocess = preprocess
    if effective_preprocess is None and point is not None:
        point_x, point_y = point

        def _sample_point(ds, _item):
            x_value, y_value = point_x, point_y
            if point_crs is not None:
                try:
                    data_crs = ds.rio.crs
                except Exception:
                    data_crs = None
                if data_crs is not None:
                    data_crs_str = str(data_crs)
                    same_crs = data_crs_str.upper() == point_crs.upper()
                    if not same_crs:
                        try:
                            from rasterio.crs import CRS

                            same_crs = CRS.from_user_input(data_crs_str) == CRS.from_user_input(
                                point_crs
                            )
                        except Exception:
                            same_crs = False
                    if not same_crs:
                        try:
                            from rasterio.warp import transform
                        except Exception as exc:  # pragma: no cover
                            raise ImportError(
                                "rasterio is required for point CRS transform. "
                                "Install with `pip install tern-stac[xarray]`"
                            ) from exc
                        xs, ys = transform(point_crs, data_crs_str, [x_value], [y_value])
                        x_value, y_value = xs[0], ys[0]
            return ds.sel(x=x_value, y=y_value, method=point_method)

        effective_preprocess = _sample_point
    elif effective_preprocess is None and clip_bounds is not None:
        def _per_item_reduce(ds, _item):
            return ds.mean(dim=("x", "y"), skipna=True)

        effective_preprocess = _per_item_reduce

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

        if effective_preprocess is not None:
            ds = effective_preprocess(ds, item)

        ds = ds.assign_coords(time=_item_datetime(item, key=time_key))
        datasets.append(ds)

    if not datasets:
        raise ValueError(
            "No datasets were loaded; check input items/asset filters, "
            "or verify authentication for protected asset URLs."
        )

    return xr.concat(sorted(datasets, key=lambda d: d.time.values.item()), dim="time")


def load_assets_as_time_series(
    assets: Sequence[dict],
    *,
    time_key: str = "datetime",
    chunks: Any = True,
    clip_bounds: Optional[tuple[float, float, float, float]] = None,
    clip_bounds_crs: Optional[str] = None,
    point: Optional[tuple[float, float]] = None,
    point_crs: str = "EPSG:4326",
    point_method: str = "nearest",
    to_numpy_nodata: bool = False,
    preprocess: Optional[Callable[[Any, Any], Any]] = None,
):
    """Open per-collection raster assets with ``rioxarray.open_rasterio`` and concat on time.

    Defaults:
    - if ``clip_bounds`` is provided and ``preprocess`` is omitted, assets are filtered
      by geometry intersection and reduced to one spatial mean value per timestamp using
      all intersecting assets.
    - if ``point`` is provided and ``preprocess`` is omitted, each item is sampled at
      the given coordinate (transformed from ``point_crs`` to data CRS when needed),
      after geometry-based filtering.
    """

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

    if point is not None and clip_bounds is not None:
        raise ValueError("Pass either `clip_bounds` or `point`, not both.")

    def _transform_point_to_crs(
        pt: tuple[float, float], src_crs: str, dst_crs: str
    ) -> tuple[float, float]:
        if _crs_equal(src_crs, dst_crs):
            return pt
        try:
            from rasterio.warp import transform
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "rasterio is required for point CRS transform. "
                "Install with `pip install tern-stac[xarray]`"
            ) from exc
        xs, ys = transform(src_crs, dst_crs, [pt[0]], [pt[1]])
        return xs[0], ys[0]

    def _clip_dataset(ds):
        if clip_bounds is None:
            return ds
        minx, miny, maxx, maxy = clip_bounds
        if clip_bounds_crs is not None:
            try:
                data_crs = ds.rio.crs
            except Exception:
                data_crs = None
            if data_crs is not None:
                data_crs_str = str(data_crs)
                if not _crs_equal(data_crs_str, clip_bounds_crs):
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
            return ds.sel(x=slice(minx, maxx), y=slice(maxy, miny))
        return ds.sel(x=slice(minx, maxx), y=slice(miny, maxy))

    # Geometry-based prefilter in EPSG:4326 using asset geometry json.
    point_wgs84: Optional[tuple[float, float]] = None
    bounds_wgs84: Optional[tuple[float, float, float, float]] = None
    if point is not None:
        src = point_crs or "EPSG:4326"
        point_wgs84 = _transform_point_to_crs(point, src, "EPSG:4326")
    elif clip_bounds is not None:
        src = clip_bounds_crs or "EPSG:4326"
        if _crs_equal(src, "EPSG:4326"):
            bounds_wgs84 = clip_bounds
        else:
            try:
                from rasterio.warp import transform_bounds
            except Exception as exc:  # pragma: no cover
                raise ImportError(
                    "rasterio is required for clip_bounds CRS transform. "
                    "Install with `pip install tern-stac[xarray]`"
                ) from exc
            bounds_wgs84 = transform_bounds(
                src,
                "EPSG:4326",
                clip_bounds[0],
                clip_bounds[1],
                clip_bounds[2],
                clip_bounds[3],
                densify_pts=21,
            )

    filtered_assets: list[dict] = []
    for asset in assets:
        geom_bounds = _geometry_bounds(asset.get("geometry"))
        if geom_bounds is None:
            filtered_assets.append(asset)
            continue
        if point_wgs84 is not None:
            if _point_in_bounds(point_wgs84, geom_bounds):
                filtered_assets.append(asset)
        elif bounds_wgs84 is not None:
            if _bounds_intersect(bounds_wgs84, geom_bounds):
                filtered_assets.append(asset)
        else:
            filtered_assets.append(asset)

    if not filtered_assets:
        raise ValueError(
            "No assets matched spatial filters from geometry metadata."
        )

    if preprocess is not None:
        datasets = []
        for asset in filtered_assets:
            href = asset["href"]
            try:
                ds = rxr.open_rasterio(href, chunks=chunks)
            except Exception as exc:
                if is_http_401_error(exc):
                    warn_auth_required(context="load_assets_as_time_series")
                    continue
                raise

            if clip_bounds is not None:
                ds = _clip_dataset(ds)

            if to_numpy_nodata:
                try:
                    ds = ds.where(ds != ds.rio.nodata, float("nan"))
                except Exception:
                    pass

            ds = preprocess(ds, asset)
            ds = ds.assign_coords(time=_item_datetime(asset, key=time_key))
            datasets.append(ds)

        if not datasets:
            raise ValueError(
                "No datasets were loaded; check input items/asset filters, "
                "or verify authentication for protected asset URLs."
            )
        return xr.concat(sorted(datasets, key=lambda d: d.time.values.item()), dim="time")

    # Default point mode: sample each relevant asset at point, then combine per timestamp.
    if point is not None:
        grouped: dict[datetime, list[Any]] = {}
        for asset in filtered_assets:
            href = asset["href"]
            try:
                ds = rxr.open_rasterio(href, chunks=chunks)
            except Exception as exc:
                if is_http_401_error(exc):
                    warn_auth_required(context="load_assets_as_time_series")
                    continue
                raise

            if to_numpy_nodata:
                try:
                    ds = ds.where(ds != ds.rio.nodata, float("nan"))
                except Exception:
                    pass

            x_value, y_value = point
            if point_crs is not None:
                try:
                    data_crs = ds.rio.crs
                except Exception:
                    data_crs = None
                if data_crs is not None:
                    data_crs_str = str(data_crs)
                    if not _crs_equal(data_crs_str, point_crs):
                        x_value, y_value = _transform_point_to_crs(
                            (x_value, y_value), point_crs, data_crs_str
                        )
            sampled = ds.sel(x=x_value, y=y_value, method=point_method)
            timestamp = _item_datetime(asset, key=time_key)
            grouped.setdefault(timestamp, []).append(sampled)

        if not grouped:
            raise ValueError(
                "No datasets were loaded; check input items/asset filters, "
                "or verify authentication for protected asset URLs."
            )

        datasets = []
        for timestamp in sorted(grouped):
            samples = grouped[timestamp]
            if len(samples) == 1:
                out = samples[0]
            else:
                out = xr.concat(samples, dim="asset").mean(dim="asset", skipna=True)
            out = out.assign_coords(time=timestamp)
            datasets.append(out)
        return xr.concat(datasets, dim="time")

    # Default clip mode: combine all intersecting assets per timestamp with weighted mean.
    if clip_bounds is not None:
        grouped_sum: dict[datetime, Any] = {}
        grouped_count: dict[datetime, Any] = {}

        for asset in filtered_assets:
            href = asset["href"]
            try:
                ds = rxr.open_rasterio(href, chunks=chunks)
            except Exception as exc:
                if is_http_401_error(exc):
                    warn_auth_required(context="load_assets_as_time_series")
                    continue
                raise

            ds = _clip_dataset(ds)
            if to_numpy_nodata:
                try:
                    ds = ds.where(ds != ds.rio.nodata, float("nan"))
                except Exception:
                    pass

            timestamp = _item_datetime(asset, key=time_key)
            tile_sum = ds.sum(dim=("x", "y"), skipna=True)
            tile_count = ds.count(dim=("x", "y"))

            if timestamp in grouped_sum:
                grouped_sum[timestamp] = grouped_sum[timestamp] + tile_sum
                grouped_count[timestamp] = grouped_count[timestamp] + tile_count
            else:
                grouped_sum[timestamp] = tile_sum
                grouped_count[timestamp] = tile_count

        if not grouped_sum:
            raise ValueError(
                "No datasets were loaded; check input items/asset filters, "
                "or verify authentication for protected asset URLs."
            )

        datasets = []
        for timestamp in sorted(grouped_sum):
            count = grouped_count[timestamp]
            out = grouped_sum[timestamp] / count.where(count > 0)
            out = out.assign_coords(time=timestamp)
            datasets.append(out)
        return xr.concat(datasets, dim="time")

    datasets = []
    for asset in filtered_assets:
        href = asset["href"]
        try:
            ds = rxr.open_rasterio(href, chunks=chunks)
        except Exception as exc:
            if is_http_401_error(exc):
                warn_auth_required(context="load_assets_as_time_series")
                continue
            raise

        if to_numpy_nodata:
            try:
                ds = ds.where(ds != ds.rio.nodata, float("nan"))
            except Exception:
                pass

        ds = ds.assign_coords(time=_item_datetime(asset, key=time_key))
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
