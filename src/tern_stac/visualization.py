"""Quick plotting helpers for quick inspection workflows."""

from __future__ import annotations

from typing import Any, Optional, Sequence


def _as_dataarray(dataset: Any, variable: Optional[str] = None):
    try:
        import xarray as xr
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "xarray is required for plotting helpers. Install with `pip install tern-stac[xarray]`"
        ) from exc

    if variable is not None and hasattr(dataset, "data_vars"):
        if variable not in dataset.data_vars:
            raise KeyError(f"Variable '{variable}' not found in dataset.")
        dataset = dataset[variable]
    if hasattr(dataset, "to_array"):
        if not isinstance(dataset, xr.DataArray):
            if variable is None and len(dataset.data_vars) == 1:
                dataset = next(iter(dataset.data_vars.values()))
            elif variable is None:
                raise ValueError(
                    "Dataset has multiple variables; pass variable explicitly."
                )
            dataset = getattr(dataset, variable) if variable else dataset
    if not isinstance(dataset, xr.DataArray):
        raise TypeError("Expected an xarray DataArray or Dataset.")
    return dataset


def preview_raster(
    dataset: Any,
    *,
    variable: Optional[str] = None,
    band: Any = None,
    time_index: int = -1,
    cmap: str = "viridis",
    robust: bool = True,
    figsize: tuple[int, int] = (10, 6),
    title: Optional[str] = None,
    ax=None,
    save_path: Optional[str] = None,
    close: bool = False,
):
    """Quick raster preview for 2D/3D geospatial outputs."""

    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "matplotlib and xarray are required. Install with `pip install tern-stac[plot]`"
        ) from exc

    da = _as_dataarray(dataset, variable=variable)
    da = da.astype("float64") if da.dtype != "float64" else da
    for dim in ("time",):
        if dim in da.dims:
            da = da.isel({dim: time_index}, drop=False)
    if "band" in da.dims and band is not None:
        da = (
            da.sel(band=band, drop=True)
            if band in da.coords.get("band", [])
            else da.isel(band=band)
        )
    if ax is not None:
        fig = ax.figure
        axis = ax
    else:
        fig, axis = plt.subplots(figsize=figsize)
    if hasattr(da, "isel") and "band" in da.dims and band is None:
        da = da.isel(band=0, drop=True)
    plot = da.plot.imshow(ax=axis, robust=robust, cmap=cmap)
    if title is None:
        title = _build_title(da, variable=variable, band=band, time_index=time_index)
    if title:
        try:
            if axis is not None:
                axis.set_title(title)
            else:
                plt.title(title)
        except Exception:
            pass
    if save_path:
        fig = fig if fig is not None else axis.get_figure()
        fig.savefig(save_path)
        if close:
            plt.close(fig)
            return None
    return plot


def plot_time_series(
    dataset: Any,
    *,
    variable: Optional[str] = None,
    time_dim: str = "time",
    space_dims: Sequence[str] = ("x", "y"),
    band_dim: str = "band",
    cmap: Optional[str] = None,
    figsize: tuple[int, int] = (12, 6),
    title: Optional[str] = None,
    save_path: Optional[str] = None,
    compute: bool = True,
):
    """Plot time-series of region-mean values."""

    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "matplotlib and numpy are required. Install with `pip install tern-stac[plot]`"
        ) from exc

    da = _as_dataarray(dataset, variable=variable)
    dims = set(da.dims)
    reduce_dims = [d for d in space_dims if d in dims]
    if time_dim not in dims:
        raise ValueError(f"Expected time dimension '{time_dim}' for time series plot.")

    ts = da.mean(dim=reduce_dims, skipna=True)
    if compute and hasattr(ts, "compute"):
        # Compute once to avoid repeated dask evaluations per plotted line.
        ts = ts.compute()
    fig, ax = plt.subplots(figsize=figsize)

    if band_dim in ts.dims:
        labels = ts[band_dim].values
        x_values = ts[time_dim].values
        y_values = np.asarray(ts.values)
        for i, label in enumerate(labels):
            ax.plot(x_values, y_values[:, i], label=str(label))
        ax.legend()
        if cmap is not None:
            for i, l in enumerate(ax.lines):
                l.set_color(cmap)
    else:
        ax.plot(ts[time_dim].values, np.asarray(ts.values), color=cmap or "tab:blue")

    ax.set_xlabel(time_dim)
    ax.set_ylabel(da.name or "value")
    if title:
        ax.set_title(title)
    if save_path:
        fig.savefig(save_path)
    return ax


def explore_odc(
    dataset: Any,
    *,
    variable: Optional[str] = None,
    tiles: str = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",  # noqa: E501
    attr: str = "Esri",
    name: str = "Background",
    band: Any = None,
    **kwargs: Any,
):
    """Try odc.explore (interactive map) for quick browser inspection."""

    da = _as_dataarray(dataset, variable=variable)
    if "band" in da.dims and band is not None:
        da = (
            da.isel(band=band, drop=True)
            if isinstance(band, int)
            else da.sel(band=band)
        )
    try:
        mapper = da.odc.explore(
            tiles=tiles,
            attr=attr,
            name=name,
            **kwargs,
        )
    except AttributeError as exc:
        raise ImportError(
            "odc-geo interactive plotting is required. Install with `pip install tern-stac[odc]`"
        ) from exc
    return mapper


def _build_title(da, *, variable: Optional[str], band: Any, time_index: int):
    parts = []
    if variable:
        parts.append(variable)
    if band is not None:
        parts.append(f"band={band}")
    if "time" in da.dims:
        parts.append(f"time={time_index}")
    if hasattr(da, "name") and da.name:
        parts.append(str(da.name))
    return " - ".join(parts) if parts else None
