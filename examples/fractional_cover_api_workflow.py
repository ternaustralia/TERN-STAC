"""Example: fractional cover workflow via STAC API with a time stack."""

from __future__ import annotations

from itertools import islice
from pathlib import Path

from tern_stac import (
    TernStacClient,
    load_items_as_time_series,
    plot_time_series,
)

# Fill in from your catalog values
COLLECTION_ID = "gov_qld_fractional_cover_v3_landsat_fractional_cover__seasonal"
START_DATE = "2020-01-01"
END_DATE = "2025-01-01"
REGION_BOUNDS = (
    110.52056451798,
    -44.60861516917,
    154.15082095686,
    -6.5048011649277,
)  # (minx, miny, maxx, maxy)


def main() -> None:
    """Open seasonal fractional-cover assets and plot ROI mean through time."""

    Path("outputs").mkdir(exist_ok=True)

    client = TernStacClient()
    search = client.search(
        collections=[COLLECTION_ID],
        datetime=f"{START_DATE}/{END_DATE}",
        bbox=[REGION_BOUNDS[0], REGION_BOUNDS[1], REGION_BOUNDS[2], REGION_BOUNDS[3]],
    )
    items = list(islice(search.items(), 10))

    if not items:
        raise RuntimeError(
            "No items returned. Update collection/date/bbox placeholders."
        )

    def per_item_reduce(ds, _item):
        # Reduce per scene before concat to keep memory usage small.
        return ds.mean(dim=("x", "y"), skipna=True)

    ds = load_items_as_time_series(
        items,
        media_type="application/xml",
        role="data",
        chunks=True,
        clip_bounds=REGION_BOUNDS,
        to_numpy_nodata=True,
        preprocess=per_item_reduce,
    )

    plot_time_series(
        ds,
        band_dim="band",
        figsize=(12, 6),
        compute=True,
        save_path="outputs/fractional_cover_time_series.png",
        title="Fractional cover ROI mean by band",
    )


if __name__ == "__main__":
    main()
