"""Example: LiDAR CHM workflow via STAC API search."""

from __future__ import annotations

from pathlib import Path

from tern_stac import TernStacClient
from tern_stac import get_item_asset_href, preview_raster
from tern_stac import laz_to_canopy_height

# Fill in from your catalog values
COLLECTION_ID = "<lidar_collection_id>"
POINT_CLOUD_ITEM_ID = "<item_id>"
POINT_CLOUD_ASSET_KEY = "<asset_key>"  # e.g., "point_cloud" or similar
POINT_CLOUD_MEDIA_TYPE = None  # e.g., "application/vnd.las+las", if preferred
POINT_CLOUD_ROLE = None  # e.g., "data"


def main() -> None:
    """Find a LiDAR item from STAC API and build CHM."""

    Path("outputs").mkdir(exist_ok=True)

    client = TernStacClient()
    search = client.search(
        collections=[COLLECTION_ID],
    )
    items = list(search.items())

    item = None
    for candidate in items:
        if candidate.id == POINT_CLOUD_ITEM_ID:
            item = candidate
            break

    if item is None:
        raise RuntimeError(
            "Item ID not found in results. Set POINT_CLOUD_ITEM_ID to a valid item id."
        )

    asset_href = get_item_asset_href(
        item,
        asset_key=POINT_CLOUD_ASSET_KEY if POINT_CLOUD_ASSET_KEY != "<asset_key>" else None,
        media_type=POINT_CLOUD_MEDIA_TYPE,
        role=POINT_CLOUD_ROLE,
    )

    chm = laz_to_canopy_height(
        asset_href,
        resolution=1.0,
        save_tif="outputs/drone_lidar_chm.tif",
    )

    preview_raster(
        chm,
        cmap="viridis",
        title="Canopy height model",
        save_path="outputs/drone_lidar_chm_preview.png",
    )


if __name__ == "__main__":
    main()
