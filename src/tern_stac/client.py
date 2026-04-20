"""Thin wrapper around :mod:`pystac_client` for TERN STAC data."""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional
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
        """Proxy to :meth:`pystac_client.Client.search`.

        Mirrors STAC API item-search parameters and returns an
        :class:`pystac_client.ItemSearch` (deferred query). No request is sent
        until you iterate results (for example via ``items()`` or ``pages()``).

        Parameters
        ----------
        method: The HTTP method to use when making a request to the service.
        This must be either "GET", "POST", or None. If None, this will default to "POST".
        If a "POST" request receives a 405 status for the response,
        it will automatically retry with "GET" for all subsequent requests.

        max_items: The maximum number of items to return from the search,even if there are more matching results.
        This client to limit the total number of Items returned from the items(), item_collections(), and items_as_dicts methods().
        The client will continue to request pages of items until the number of max items is reached.
        Setting this to None will allow iteration over a possibly very large number of results.

        limit: A recommendation to the service as to the number of items to return per page of results. Defaults to 100.

        ids: List of one or more Item ids to filter on.

        collections: List of one or more Collection IDs or pystac.Collection instances.
        Only Items in one of the provided Collections will be searched

        bbox: A list, tuple, or iterator representing a bounding box of 2D or 3D coordinates.
        Results will be filtered to only those intersecting the bounding box.

        intersects: A string or dictionary representing a GeoJSON geometry,
        or an object that implements a __geo_interface__ property, as supported by several libraries
        including Shapely, ArcPy, PySAL, and geojson. Results filtered to only those intersecting the geometry.

        datetime: Either a single datetime or datetime range used to filter results.
        You may express a single datetime using a datetime.datetime instance,
        a RFC 3339-compliant timestamp, or a simple date string (see below).
        Instances of datetime.datetime may be either timezone aware or unaware.
        Timezone aware instances will be converted to a UTC timestamp before being passed to the endpoint.
        Timezone unaware instances are assumed to represent UTC timestamps.
        You may represent a datetime range using a "/" separated string as described in the spec,
        or a list, tuple, or iterator of 2 timestamps or datetime instances.
        For open-ended ranges, use either ".." ('2020-01-01:00:00:00Z/..', ['2020-01-01:00:00:00Z', '..']) or a value of None (['2020-01-01:00:00:00Z', None]).

        If using a simple date string, the datetime can be specified in YYYY-mm-dd format,
        optionally truncating to YYYY-mm or just YYYY.
        Simple date strings will be expanded to include the entire time period, for example:

        2017 expands to 2017-01-01T00:00:00Z/2017-12-31T23:59:59Z

        2017-06 expands to 2017-06-01T00:00:00Z/2017-06-30T23:59:59Z

        2017-06-10 expands to 2017-06-10T00:00:00Z/2017-06-10T23:59:59Z

        If used in a range, the end of the range expands to the end of that day/month/year, for example:

        2017/2018 expands to 2017-01-01T00:00:00Z/2018-12-31T23:59:59Z

        2017-06/2017-07 expands to 2017-06-01T00:00:00Z/2017-07-31T23:59:59Z

        2017-06-10/2017-06-11 expands to 2017-06-10T00:00:00Z/2017-06-11T23:59:59Z

        query: List or JSON of query parameters as per the STAC API query extension

        filter: JSON of query parameters as per the STAC API filter extension

        filter_lang: Language variant used in the filter body.
        If filter is a dictionary or not provided, defaults to 'cql2-json'. If filter is a string, defaults to cql2-text.

        sortby: A single field or list of fields to sort the response by

        fields: A list of fields to include in the response.
        Note this may result in invalid STAC objects, as they may not have required fields. Use items_as_dicts to avoid object unmarshalling errors.

        Returns
        -------
        A deferred item search object.

        Return type
        -----------
        pystac_client.ItemSearch

        Reference:
        https://pystac-client.readthedocs.io/en/stable/api.html#pystac_client.Client.search
        """  # noqa: E501

        return self._client.search(*args, **kwargs)

    def collection_search(self, *args: Any, **kwargs: Any):
        """Proxy to ``Client.collection_search`` with conservative pagination.

        Mirrors STAC API collection-search parameters and returns a
        :class:`pystac_client.CollectionSearch` (deferred query). No request is
        sent until iterating results (for example via ``collections()`` or
        ``pages()``).

        Parameters
        ----------
        url: The URL to the search page of the STAC API.

        max_collections: The maximum number of collections to return from the search, even if there are more matching results.
        This client to limit the total number of Collections returned from the collections(), collection_list(), and collections_as_dicts methods().
        The client will continue to request pages of collections until the number of max collections is reached.
        Setting this to None will allow iteration over a possibly very large number of results.

        stac_io: An instance of StacIO for retrieving results.
        Normally comes from the Client that returns this CollectionSearch client:
        An instance of a root Client used to set the root on resulting Collections.

        client: An instance of Client for retrieving results.
        This is normally populated by the client that returns this CollectionSearch instance.

        limit: A recommendation to the service as to the number of collections to return per page of results. Defaults and capped to 5.

        bbox: A list, tuple, or iterator representing a bounding box of 2D or 3D coordinates.
        Results will be filtered to only those intersecting the bounding box.

        datetime: Either a single datetime or datetime range used to filter results.
        You may express a single datetime using a datetime.datetime instance, a RFC 3339-compliant timestamp, or a simple date string (see below).
        Instances of datetime.datetime may be either timezone aware or unaware.
        Timezone aware instances will be converted to a UTC timestamp before being passed to the endpoint.
        Timezone unaware instances are assumed to represent UTC timestamps.
        You may represent a datetime range using a "/" separated string as described in the spec,
        or a list, tuple, or iterator of 2 timestamps or datetime instances.
        For open-ended ranges, use either ".." ('2020-01-01:00:00:00Z/..', ['2020-01-01:00:00:00Z', '..']) or a value of None (['2020-01-01:00:00:00Z', None]).

        If using a simple date string, the datetime can be specified in YYYY-mm-dd format,
        optionally truncating to YYYY-mm or just YYYY. Simple date strings will be expanded to include the entire time period, for example:

        2017 expands to 2017-01-01T00:00:00Z/2017-12-31T23:59:59Z

        2017-06 expands to 2017-06-01T00:00:00Z/2017-06-30T23:59:59Z

        2017-06-10 expands to 2017-06-10T00:00:00Z/2017-06-10T23:59:59Z

        If used in a range, the end of the range expands to the end of that day/month/year, for example:

        2017/2018 expands to 2017-01-01T00:00:00Z/2018-12-31T23:59:59Z

        2017-06/2017-07 expands to 2017-06-01T00:00:00Z/2017-07-31T23:59:59Z

        2017-06-10/2017-06-11 expands to 2017-06-10T00:00:00Z/2017-06-11T23:59:59Z

        q: Free-text search query. See the STAC API - Free Text Extension Spec for syntax.

        query: List or JSON of query parameters as per the STAC API query extension

        filter: JSON of query parameters as per the STAC API filter extension

        filter_lang: Language variant used in the filter body.
        If filter is a dictionary or not provided, defaults to 'cql2-json'. If filter is a string, defaults to cql2-text.

        sortby: A single field or list of fields to sort the response by

        fields: A list of fields to include in the response.
        Note this may result in invalid STAC objects, as they may not have required fields.
        Use collections_as_dicts to avoid object unmarshalling errors.

        modifier: A callable that modifies the children collection and items returned by this Client.
        This can be useful for injecting authentication parameters into child assets to access data from non-public sources.

        The callable should expect a single argument, which will be one of the following types:

        pystac.Collection

        pystac.Item

        pystac.ItemCollection

        A STAC item-like dict

        A STAC collection-like dict

        The callable should mutate the argument in place and return None.

        modifier propagates recursively to children of this Client.
        After getting a child collection with, e.g. Client.get_collection(),
        the child items of that collection will still be signed with modifier.

        Returns
        -------
        A deferred collection search object.

        Return type
        -----------
        pystac_client.CollectionSearch

        Reference:
        https://pystac-client.readthedocs.io/en/stable/api.html#pystac_client.Client.collection_search
        """  # noqa: E501

        limit = kwargs.get("limit", 5)
        if limit is None:
            limit = 5
        try:
            limit = int(limit)
        except (TypeError, ValueError) as exc:
            raise ValueError("collection_search limit must be an integer") from exc
        kwargs["limit"] = min(limit, 5)
        return self._client.collection_search(*args, **kwargs)

    def get_collection(self, *args: Any, **kwargs: Any):
        """Proxy to :meth:`pystac_client.Client.get_collection`.

        Fetches one collection by ``collection_id`` from the connected root
        catalog/API.

        Parameters
        ----------
        collection_id: The Collection ID to get

        Returns
        -------
        The matching STAC collection object from the API/catalog.

        Return type
        -----------
        Union[pystac.Collection, pystac_client.CollectionClient]

        Reference:
        https://pystac-client.readthedocs.io/en/stable/api.html#pystac_client.Client.get_collection
        """

        return self._client.get_collection(*args, **kwargs)

    def get_items(self, *args: Any, **kwargs: Any):
        """Proxy to :meth:`pystac_client.Client.get_items`.

        Fetches one item by ``id`` (and optional ``recursive`` behavior per the
        underlying PySTAC/PySTAC-Client implementation).

        Parameters
        ----------
        ids: Zero or more item ids to find.

        recursive: unused in pystac-client, but needed for falling back to pystac

        Returns
        -------
        The matching STAC item, if found.

        Return type
        -----------
        Optional[pystac.Item]

        Reference:
        https://pystac-client.readthedocs.io/en/stable/api.html#pystac_client.CollectionClient.get_item
        """

        return self._client.get_items(*args, **kwargs)

    def load_rasterio(
        self, stac_object: Any, asset_key: Optional[str] = None, **kwargs: Any
    ):
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

    def load_xarray(
        self, stac_object: Any, asset_key: Optional[str] = None, **kwargs: Any
    ):
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

    def load_geodataframe(
        self, stac_object: Any, asset_key: Optional[str] = None, **kwargs: Any
    ):
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
        raise TypeError(
            "Expected STAC item/collection/dict/asset object or URL string."
        )

    if not isinstance(assets, Mapping):
        raise TypeError(
            "Expected object.assets to be a mapping of asset keys to assets"
        )

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
