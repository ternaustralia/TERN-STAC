"""Example: stackstac workflow using the dataset pattern from the gif tutorial.

This example intentionally uses non-TERN data because current TERN assets are
not suitable for stackstac in the same way.

Reference:
https://stackstac.readthedocs.io/en/latest/examples/gif.html
"""

from __future__ import annotations

from itertools import islice
from pathlib import Path

from tern_stac import (
    get_array_bounds,
    get_array_epsg,
    load_items_stackstac,
    mosaic_time,
    plot_time_series,
    preview_raster,
)

# This example intentionally uses non-TERN data because current TERN assets are
# not suitable for stackstac in the same way.
STAC_API_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION_ID = "landsat-8-c2-l2"
START_DATE = "2013-01-01"
END_DATE = "2023-12-31"
REGION_BOUNDS = (-69.95, 41.62, -69.88, 41.67)  # Cape Cod, lon/lat (gif example area)
MAX_ITEMS = 100


def main() -> None:
    """Load STAC items into a lazy DataArray and run stackstac operations."""

    try:
        import planetary_computer as pc
        import pystac_client
    except Exception as exc:
        raise ImportError(
            "This example requires `planetary-computer`. "
            "Install with `pip install planetary-computer`."
        ) from exc

    Path("outputs").mkdir(exist_ok=True)

    catalog = pystac_client.Client.open(STAC_API_URL)
    search = catalog.search(
        collections=[COLLECTION_ID],
        datetime=f"{START_DATE}/{END_DATE}",
        bbox=[REGION_BOUNDS[0], REGION_BOUNDS[1], REGION_BOUNDS[2], REGION_BOUNDS[3]],
    )
    items = list(islice(search.items(), MAX_ITEMS))
    if not items:
        raise RuntimeError("No items returned. Update collection/date/bbox placeholders.")
    items = [pc.sign(item) for item in items]

    arr = load_items_stackstac(
        items,
        assets=["SR_B4", "SR_B3", "SR_B2", "QA_PIXEL"],
        bounds_latlon=REGION_BOUNDS,
        # chunksize=1024,
        epsg=32619,
    )

    # Match stackstac gif tutorial style for harmonized band names.
    if "common_name" in arr.coords:
        arr = arr.assign_coords(band=arr.common_name.fillna(arr.band).rename("band"))

    print("EPSG:", get_array_epsg(arr, default=None))
    print("Bounds:", get_array_bounds(arr, to_epsg=4326))

    # Cloud mask from QA bits (dilated cloud, cirrus, cloud, cloud shadow)
    mask_bitfields = [1, 2, 3, 4]
    bitmask = 0
    for field in mask_bitfields:
        bitmask |= 1 << field
    qa = arr.sel(band="QA_PIXEL").astype("uint16")
    good = arr.where((qa & bitmask) == 0)
    # good.time.diff("time").dt.days.plot.hist()

    rgb = good.sel(band=["red", "green", "blue"])

    # Time mosaic and simple biannual composites
    mosaic = mosaic_time(rgb)
    _ = mosaic  # keeps example explicit without forcing a full compute here
    composites = rgb.resample(time="2Q").median("time").ffill("time")[1:]

    preview_raster(
        composites,
        rgb_bands=["red", "green", "blue"],
        time_index=-1,
        save_path="outputs/stackstac_rgb_composite_last.png",
        title="stackstac RGB composite (last timestep)",
    )

    # Spatial mean through time/bands for quick QC plot
    arr_mean = composites.mean(dim=("x", "y"), skipna=True)
    plot_time_series(
        arr_mean,
        band_dim="band",
        save_path="outputs/stackstac_time_series.png",
        title="stackstac ROI mean by band",
    )


if __name__ == "__main__":
    main()
