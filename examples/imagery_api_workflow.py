"""Example: drone imagery-style workflow via TERN STAC API."""

from __future__ import annotations

from pathlib import Path

from tern_stac import TernStacClient
from tern_stac import load_items_odc
from tern_stac import mean_over_dims, spatial_slice
from tern_stac import plot_time_series, preview_raster


# Fill in from your catalog values
COLLECTION_ID = "uas_dronescape_saagaw0009_20241001__imagery_multispec"
START_DATE = "2024-01-01"
END_DATE = "2024-12-31"
BANDS = ["b5", "b4", "b3"]
REGION_BOUNDS = (135.0, -31.0, 136.0, -30.0)  # (minx, miny, maxx, maxy)
REGION_BOUNDS_CRS = "EPSG:4326"


def main() -> None:
    """Load matching items from API and produce quick raster previews."""

    Path("outputs").mkdir(exist_ok=True)

    client = TernStacClient()
    search = client.search(
        collections=[COLLECTION_ID],
        datetime=f"{START_DATE}/{END_DATE}",
        bbox=[REGION_BOUNDS[0], REGION_BOUNDS[1], REGION_BOUNDS[2], REGION_BOUNDS[3]],
    )
    items = list(search.items())

    if not items:
        raise RuntimeError("No items returned. Update collection/date/bbox placeholders.")

    ds = load_items_odc(
        items,
        bands=BANDS,
        crs="utm",
        groupby="solar_day",
        chunks={},
    )

    roi = spatial_slice(ds, REGION_BOUNDS, bounds_crs=REGION_BOUNDS_CRS)
    preview_raster(
        roi,
        band=0,
        time_index=-1,
        save_path="outputs/imagery_roi_last.png",
        title="Imagery ROI (last timestep, first band)",
    )

    summary = mean_over_dims(roi, dims=("x", "y"))
    plot_time_series(
        summary,
        band_dim="band",
        save_path="outputs/imagery_time_series.png",
        title="Imagery ROI mean through time",
    )


if __name__ == "__main__":
    main()
