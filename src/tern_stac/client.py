"""Thin wrapper around :mod:`pystac_client` for TERN STAC data."""

from __future__ import annotations

from typing import Any, Mapping, Optional
import os
from urllib.parse import urljoin

from pystac_client import Client
from .auth import is_http_401_error, warn_auth_required

DEFAULT_TERN_STAC_URL = "https://stac-api-test.tern.org.au/"
TERN_STAC_ENV_VAR = "TERN_STAC_URL"


class TernStacClient:
    """Wrapper for a fixed-URL TERN STAC client.

    Parameters mirror ``pystac_client.Client.open`` and are passed through after
    resolving defaults.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        **client_kwargs: Any,
    ) -> None:
        self.api_url = api_url or os.getenv(TERN_STAC_ENV_VAR, DEFAULT_TERN_STAC_URL)
        self._client = Client.open(self.api_url, **client_kwargs)

    @property
    def client(self) -> Client:
        """Return the underlying :class:`pystac_client.client.Client`."""

        return self._client

    def search(self, *args: Any, **kwargs: Any):
        """Proxy to ``Client.search`` for STAC API-like backends."""

        return self._client.search(*args, **kwargs)

    def get_collection(self, *args: Any, **kwargs: Any):
        """Get a collection by ID from the STAC root/catalog."""

        return self._client.get_collection(*args, **kwargs)

    def get_item(self, *args: Any, **kwargs: Any):
        """Get an item by ID."""

        return self._client.get_item(*args, **kwargs)

    def get_root(self):
        """Return STAC root catalog from the connected endpoint."""

        return self._client

    def load_rasterio(self, stac_object: Any, asset_key: Optional[str] = None, **kwargs: Any):
        """Open raster data with rasterio and return the DatasetReader object."""

        try:
            import rasterio
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "rasterio is not installed. Install with `pip install tern-stac[rasterio]`"
            ) from exc

        href = _resolve_asset_href(stac_object, asset_key)
        try:
            return rasterio.open(href, **kwargs)
        except Exception as exc:
            if is_http_401_error(exc):
                warn_auth_required(context="load_rasterio")
                return None
            raise

    def load_xarray(self, stac_object: Any, asset_key: Optional[str] = None, **kwargs: Any):
        """Load raster-like STAC assets directly into xarray via rioxarray."""

        try:
            import rioxarray as rxr
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "rioxarray is not installed. Install with `pip install tern-stac[xarray]`"
            ) from exc

        href = _resolve_asset_href(stac_object, asset_key)
        try:
            return rxr.open_rasterio(href, **kwargs)
        except Exception as exc:
            if is_http_401_error(exc):
                warn_auth_required(context="load_xarray")
                return None
            raise

    def load_geodataframe(self, stac_object: Any, asset_key: Optional[str] = None, **kwargs: Any):
        """Load vector-like STAC assets directly into geopandas."""

        try:
            import geopandas as gpd
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "geopandas is not installed. Install with `pip install tern-stac[geopandas]`"
            ) from exc

        href = _resolve_asset_href(stac_object, asset_key)
        try:
            return gpd.read_file(href, **kwargs)
        except Exception as exc:
            if is_http_401_error(exc):
                warn_auth_required(context="load_geodataframe")
                return None
            raise


def _resolve_asset_href(stac_object: Any, asset_key: Optional[str]) -> str:
    """Resolve a STAC object, dict, or URL to a concrete asset href."""

    if isinstance(stac_object, str):
        return stac_object

    href = _coerce_href(stac_object)
    if href is not None:
        return href

    assets = getattr(stac_object, "assets", None)
    if assets is None and isinstance(stac_object, Mapping):
        assets = stac_object.get("assets")
    if assets is None:
        raise TypeError("Expected STAC item/collection/dict/asset object or URL string.")

    if not isinstance(assets, Mapping):
        raise TypeError("Expected object.assets to be a mapping of asset keys to assets")

    if asset_key is None:
        if len(assets) == 1:
            asset_key = next(iter(assets))
        elif len(assets) == 0:
            raise ValueError("STAC object has no assets")
        else:
            raise ValueError(
                "Multiple assets available; pass asset_key explicitly "
                f"(available: {', '.join(sorted(assets))})"
            )

    if asset_key not in assets:
        raise KeyError(f"Asset '{asset_key}' not found")

    asset = assets[asset_key]
    href = _coerce_href(asset)
    if href is None:
        raise TypeError(f"Asset '{asset_key}' does not provide an href")
    if href.startswith(".") and hasattr(stac_object, "get_self_href"):
        base = stac_object.get_self_href() or ""
        href = urljoin(base, href)
    return href


def _coerce_href(obj: Any) -> Optional[str]:
    """Attempt to extract href from common STAC-like objects."""

    if isinstance(obj, str):
        return obj

    href = getattr(obj, "href", None)
    if href:
        return href

    if isinstance(obj, Mapping):
        nested_href = obj.get("href") if isinstance(obj.get("href"), str) else None
        if nested_href:
            return nested_href

    return None


def load_from_tern(
    stac_object: Any,
    asset_key: Optional[str] = None,
    *,
    backend: str = "rasterio",
    **kwargs: Any,
):
    """Convenience helper using a fixed TERN client instance."""

    client = TernStacClient()
    if backend == "rasterio":
        return client.load_rasterio(stac_object, asset_key=asset_key, **kwargs)
    if backend == "xarray":
        return client.load_xarray(stac_object, asset_key=asset_key, **kwargs)
    if backend == "geopandas":
        return client.load_geodataframe(stac_object, asset_key=asset_key, **kwargs)
    raise ValueError("backend must be one of: rasterio, xarray, geopandas")
