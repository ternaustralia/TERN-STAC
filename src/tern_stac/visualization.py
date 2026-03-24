"""Quick plotting helpers for quick inspection workflows."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from .auth import is_http_401_error, warn_auth_required


def _as_dataarray(dataset: Any, variable: Optional[str] = None):
    try:
        import xarray as xr
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "xarray is required for plotting helpers. Install with `pip install tern-stac[xarray]`"
        ) from exc

    if hasattr(dataset, "data_vars") and not isinstance(dataset, xr.DataArray):
        if variable is not None:
            if variable not in dataset.data_vars:
                raise KeyError(f"Variable '{variable}' not found in dataset.")
            dataset = dataset[variable]
        elif len(dataset.data_vars) == 1:
            dataset = next(iter(dataset.data_vars.values()))
        else:
            # Match notebook behavior: convert multi-var Dataset to a plottable stack.
            dataset = dataset.to_array(dim="variable")
    if not isinstance(dataset, xr.DataArray):
        raise TypeError("Expected an xarray DataArray or Dataset.")
    return dataset


def preview_raster(
    dataset: Any,
    *,
    variable: Optional[str] = None,
    band: Any = None,
    rgb_bands: Optional[Sequence[Any]] = None,
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
        import xarray as xr
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "matplotlib and xarray are required. Install with `pip install tern-stac[plot]`"
        ) from exc

    da = _as_dataarray(dataset, variable=variable)
    da = da.astype("float64") if da.dtype != "float64" else da
    for dim in ("time",):
        if dim in da.dims:
            da = da.isel({dim: time_index}, drop=False)
    series_dim = None
    if "band" in da.dims:
        series_dim = "band"
    elif "variable" in da.dims:
        series_dim = "variable"

    if ax is not None:
        fig = ax.figure
        axis = ax
    else:
        fig, axis = plt.subplots(figsize=figsize)

    if rgb_bands is not None:
        if band is not None:
            raise ValueError("Pass either `band` or `rgb_bands`, not both.")
        if len(rgb_bands) != 3:
            raise ValueError("`rgb_bands` must contain exactly 3 entries.")
        if series_dim is None:
            raise ValueError(
                "RGB plotting requires a `band` or `variable` dimension with 3 channels."
            )

        selected = []
        for key in rgb_bands:
            if isinstance(key, int):
                selected.append(da.isel({series_dim: key}))
            else:
                selected.append(da.sel({series_dim: key}))
        da_rgb = xr.concat(selected, dim="band")
        da_rgb = da_rgb.assign_coords(band=["R", "G", "B"])
        if "y" in da_rgb.dims and "x" in da_rgb.dims:
            da_rgb = da_rgb.transpose("y", "x", "band")
        try:
            plot = da_rgb.plot.imshow(ax=axis, robust=robust, rgb="band")
        except Exception as exc:
            if is_http_401_error(exc):
                warn_auth_required(context="preview_raster")
                return None
            raise
    else:
        if series_dim is not None and band is not None:
            da = (
                da.sel({series_dim: band}, drop=True)
                if series_dim in da.coords and band in da.coords.get(series_dim, [])
                else da.isel({series_dim: band})
            )
        if hasattr(da, "isel") and series_dim is not None and band is None:
            da = da.isel({series_dim: 0}, drop=True)
        try:
            plot = da.plot.imshow(ax=axis, robust=robust, cmap=cmap)
        except Exception as exc:
            if is_http_401_error(exc):
                warn_auth_required(context="preview_raster")
                return None
            raise

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
        try:
            ts = ts.compute()
        except Exception as exc:
            if is_http_401_error(exc):
                warn_auth_required(context="plot_time_series")
                return None
            raise
    fig, ax = plt.subplots(figsize=figsize)

    series_dim = band_dim if band_dim in ts.dims else None
    if series_dim is None and "variable" in ts.dims:
        series_dim = "variable"

    if series_dim is not None:
        ts_plot = ts.transpose(time_dim, series_dim)
        labels = ts_plot[series_dim].values
        x_values = ts_plot[time_dim].values
        y_values = np.asarray(ts_plot.values)
        if not np.isfinite(y_values).any():
            raise ValueError(
                "No finite values available for plotting. "
                "Check ROI bounds, nodata masking, and selected items."
            )
        for i, label in enumerate(labels):
            if y_values.shape[0] == 1:
                ax.scatter(x_values, y_values[:, i], label=str(label))
            else:
                ax.plot(x_values, y_values[:, i], label=str(label))
        ax.legend()
        if cmap is not None:
            for i, l in enumerate(ax.lines):
                l.set_color(cmap)
    else:
        ts_plot = ts.transpose(time_dim, ...)
        x_values = ts_plot[time_dim].values
        y_values = np.asarray(ts_plot.values)
        if not np.isfinite(y_values).any():
            raise ValueError(
                "No finite values available for plotting. "
                "Check ROI bounds, nodata masking, and selected items."
            )
        if y_values.shape[0] == 1:
            ax.scatter(x_values, y_values, color=cmap or "tab:blue")
        else:
            ax.plot(x_values, y_values, color=cmap or "tab:blue")

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
    except Exception as exc:
        if is_http_401_error(exc):
            warn_auth_required(context="explore_odc")
            return None
        raise
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
