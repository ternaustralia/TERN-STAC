"""TERN STAC convenience library."""

from ._version import __version__
from .client import TernStacClient, load_from_tern
from .lidar import laz_to_canopy_height
from .loaders import (
    get_item_asset_href,
    load_assets_as_time_series,
    load_items_as_time_series,
    load_items_odc,
)
from .roi import bounds_from_geodataframe, mean_over_dims, spatial_slice
from .stackstac_utils import (
    get_array_bounds,
    get_array_epsg,
    load_items_stackstac,
    mosaic_time,
)
from .visualization import explore_odc, plot_time_series, preview_raster

__all__ = [
    "TernStacClient",
    "load_from_tern",
    "__version__",
    "laz_to_canopy_height",
    "get_item_asset_href",
    "load_items_as_time_series",
    "load_assets_as_time_series",
    "load_items_odc",
    "load_items_stackstac",
    "mosaic_time",
    "get_array_bounds",
    "get_array_epsg",
    "bounds_from_geodataframe",
    "mean_over_dims",
    "spatial_slice",
    "preview_raster",
    "plot_time_series",
    "explore_odc",
]
