"""Lidar-specific helpers."""

from __future__ import annotations

from typing import Optional


def laz_to_canopy_height(
    source,
    resolution: float = 1.0,
    save_tif: Optional[str] = "chm.tif",
):
    """Convert COPC/LAS/LAZ source to canopy-height model."""

    try:
        import numpy as np
        import xarray as xr
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "xarray and numpy are required. Install with `pip install tern-stac[lidar]`"
        ) from exc

    try:
        import laspy
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "laspy and xarray are required. Install with `pip install tern-stac[lidar]`"
        ) from exc

    try:
        with laspy.CopcReader.open(source) as crdr:
            try:
                points = crdr.read_points()
                las = laspy.LasData(header=crdr.header, points=points)
            except Exception:
                points = crdr.query()
                las = laspy.lasdata.LasData(header=crdr.header, points=points)
    except Exception:
        las = laspy.read(source)

    x, y, z = las.x, las.y, las.z

    xmin, xmax = x.min(), x.max()
    ymin, ymax = y.min(), y.max()
    nx = int(np.ceil((xmax - xmin) / resolution))
    ny = int(np.ceil((ymax - ymin) / resolution))

    ix = ((x - xmin) / resolution).astype(np.int32)
    iy = ((ymax - y) / resolution).astype(np.int32)  # flip y for raster coords
    ix = np.clip(ix, 0, nx - 1)
    iy = np.clip(iy, 0, ny - 1)
    flat_idx = iy * nx + ix

    dem = np.full(nx * ny, np.inf, dtype=np.float32)
    dsm = np.full(nx * ny, -np.inf, dtype=np.float32)

    np.minimum.at(dem, flat_idx, z)
    np.maximum.at(dsm, flat_idx, z)

    dem[dem == np.inf] = np.nan
    dsm[dsm == -np.inf] = np.nan

    chm = (dsm - dem).reshape((ny, nx))
    chm[chm < 0] = 0

    x_coords = xmin + (np.arange(nx) + 0.5) * resolution
    y_coords = ymax - (np.arange(ny) + 0.5) * resolution
    chm_da = xr.DataArray(
        chm,
        coords={"y": y_coords, "x": x_coords},
        dims=("y", "x"),
        name="canopy_height",
    )

    crs = None
    try:
        crs = las.header.parse_crs()
    except Exception:
        pass

    if crs is not None:
        try:
            from odc.geo.xr import assign_crs

            chm_da = assign_crs(chm_da, crs=crs)
            chm_da.attrs["crs"] = crs.to_wkt()
        except Exception:
            chm_da.attrs["crs"] = crs.to_wkt()
    else:
        chm_da.attrs["crs"] = None

    if save_tif is not None:
        try:
            chm_da.odc.write_cog(save_tif, overwrite=True)
        except AttributeError as exc:
            raise ImportError(
                "odc-geo is required to write COG with .odc.write_cog(). "
                "Install with `pip install tern-stac[lidar]`"
            ) from exc

    return chm_da
