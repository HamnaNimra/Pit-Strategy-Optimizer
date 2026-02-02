"""Degradation and lap time plots.

Predicted vs actual lap time curves and tire degradation profiles by compound.
All functions accept data as arguments; no hardcoded race or driver assumptions.
Plots are labeled and readable (axis labels, optional title, legend).
"""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _as_array(x: Any):
    """Convert to 1D numpy array for plotting."""
    if isinstance(x, pd.Series):
        return x.values
    return np.atleast_1d(np.asarray(x))


def _lap_time_to_seconds(series: pd.Series) -> pd.Series:
    """Convert lap time column to seconds (Timedelta or numeric)."""
    if pd.api.types.is_timedelta64_dtype(series):
        return series.dt.total_seconds()
    return pd.to_numeric(series, errors="coerce")


# Default figure size for readable, portfolio-ready plots
DEFAULT_FIGSIZE = (10, 5)


def plot_predicted_vs_actual(
    lap_numbers: np.ndarray | pd.Series | list,
    actual_seconds: np.ndarray | pd.Series | list,
    predicted_seconds: np.ndarray | pd.Series | list,
    *,
    ax: plt.Axes | None = None,
    figsize: tuple[float, float] = DEFAULT_FIGSIZE,
    title: str | None = None,
    actual_label: str = "Actual",
    predicted_label: str = "Predicted",
    xlabel: str = "Lap number",
    ylabel: str = "Lap time (s)",
) -> plt.Axes:
    """
    Plot predicted vs actual lap times (two lines).

    Parameters
    ----------
    lap_numbers : array-like
        Lap numbers (e.g. 1, 2, ..., N).
    actual_seconds : array-like
        Actual lap times in seconds (same length as lap_numbers).
    predicted_seconds : array-like
        Predicted lap times in seconds (same length as lap_numbers).
    ax : matplotlib Axes, optional
        Axes to plot on; if None, current axes or new figure.
    title : str, optional
        Plot title.
    actual_label, predicted_label : str
        Legend labels for the two lines.
    xlabel, ylabel : str
        Axis labels.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    lap = _as_array(lap_numbers)
    actual = _as_array(actual_seconds)
    pred = _as_array(predicted_seconds)
    ax.plot(lap, actual, "o-", label=actual_label, markersize=4, alpha=0.9)
    ax.plot(lap, pred, "s--", label=predicted_label, markersize=4, alpha=0.9)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return ax


def plot_predicted_vs_actual_from_laps(
    laps: pd.DataFrame,
    predicted_seconds: np.ndarray | pd.Series | list,
    *,
    lap_col: str = "LapNumber",
    lap_time_col: str = "LapTime",
    driver_filter: str | int | None = None,
    ax: plt.Axes | None = None,
    title: str | None = None,
    actual_label: str = "Actual",
    predicted_label: str = "Predicted",
) -> plt.Axes:
    """
    Plot predicted vs actual lap times from a laps DataFrame and predicted array.

    Filters to one driver if driver_filter is set (column DriverNumber).
    Converts lap_time_col to seconds if it is Timedelta. predicted_seconds must
    align with laps by index or length (same row order after filtering).

    Parameters
    ----------
    laps : pd.DataFrame
        Must contain lap_col and lap_time_col; optional DriverNumber.
    predicted_seconds : array-like
        Predicted lap times in seconds (length = len(laps) after filter).
    lap_col, lap_time_col : str
        Column names for lap number and lap time.
    driver_filter : str or int, optional
        If set, keep only rows where DriverNumber == driver_filter.
    ax, title, actual_label, predicted_label : optional
        Passed through to plot_predicted_vs_actual.

    Returns
    -------
    matplotlib.axes.Axes
    """
    subset = laps.copy()
    if driver_filter is not None:
        subset = subset[subset["DriverNumber"].astype(str) == str(driver_filter)]
    if (
        subset.empty
        or lap_col not in subset.columns
        or lap_time_col not in subset.columns
    ):
        if ax is None:
            _, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
        return ax
    lap_numbers = subset[lap_col].values
    actual = _lap_time_to_seconds(subset[lap_time_col]).values
    pred = _as_array(predicted_seconds)
    if len(pred) != len(lap_numbers):
        pred = pred[: len(lap_numbers)]
    return plot_predicted_vs_actual(
        lap_numbers,
        actual,
        pred,
        ax=ax,
        title=title,
        actual_label=actual_label,
        predicted_label=predicted_label,
    )


def plot_degradation_curve(
    curve: pd.DataFrame,
    *,
    lap_col: str = "lap_in_stint",
    time_col: str = "predicted_lap_time_sec",
    ax: plt.Axes | None = None,
    compound_label: str | None = None,
    title: str | None = None,
    xlabel: str = "Lap in stint",
    ylabel: str = "Predicted lap time (s)",
) -> plt.Axes:
    """
    Plot a single tire degradation curve (lap-in-stint vs predicted lap time).

    Parameters
    ----------
    curve : pd.DataFrame
        Must contain lap_col and time_col (e.g. from diagnostics.degradation_curve).
    lap_col, time_col : str
        Column names for x and y.
    ax : matplotlib Axes, optional
        Axes to plot on.
    compound_label : str, optional
        Legend label (e.g. "SOFT"); if None, no legend entry.
    title : str, optional
        Plot title.
    xlabel, ylabel : str
        Axis labels.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
    if curve.empty or lap_col not in curve.columns or time_col not in curve.columns:
        return ax
    x = curve[lap_col].values
    y = curve[time_col].values
    label = compound_label if compound_label else None
    ax.plot(x, y, "o-", label=label, markersize=3, alpha=0.9)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if label:
        ax.legend()
    ax.grid(True, alpha=0.3)
    return ax


def plot_degradation_curves_by_compound(
    curves: dict[str, pd.DataFrame],
    *,
    lap_col: str = "lap_in_stint",
    time_col: str = "predicted_lap_time_sec",
    ax: plt.Axes | None = None,
    title: str | None = None,
    xlabel: str = "Lap in stint",
    ylabel: str = "Predicted lap time (s)",
) -> plt.Axes:
    """
    Plot tire degradation curves for multiple compounds (one line per compound).

    Parameters
    ----------
    curves : dict[str, pd.DataFrame]
        Mapping compound name -> DataFrame with lap_col and time_col
        (e.g. {"SOFT": df_soft, "MEDIUM": df_med, "HARD": df_hard}).
    lap_col, time_col : str
        Column names for x and y in each DataFrame.
    ax : matplotlib Axes, optional
        Axes to plot on.
    title : str, optional
        Plot title.
    xlabel, ylabel : str
        Axis labels.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
    for compound, df in curves.items():
        if df.empty or lap_col not in df.columns or time_col not in df.columns:
            continue
        ax.plot(
            df[lap_col].values,
            df[time_col].values,
            "o-",
            label=compound,
            markersize=3,
            alpha=0.9,
        )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return ax


def plot_predicted_vs_actual_plotly(
    lap_numbers: np.ndarray | pd.Series | list,
    actual_seconds: np.ndarray | pd.Series | list,
    predicted_seconds: np.ndarray | pd.Series | list,
    *,
    title: str | None = None,
    actual_label: str = "Actual",
    predicted_label: str = "Predicted",
    xlabel: str = "Lap number",
    ylabel: str = "Lap time (s)",
):
    """
    Build an interactive plotly figure: predicted vs actual lap times.
    Use with export_plotly_html(fig, path) for portfolio display.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        raise ImportError("plotly is required for HTML export; pip install plotly") from None
    lap = np.asarray(lap_numbers)
    actual = np.asarray(actual_seconds)
    pred = np.asarray(predicted_seconds)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=lap.tolist(), y=actual.tolist(), mode="lines+markers", name=actual_label, line=dict(width=2)))
    fig.add_trace(go.Scatter(x=lap.tolist(), y=pred.tolist(), mode="lines+markers", name=predicted_label, line=dict(dash="dash", width=2)))
    fig.update_layout(
        title=title or "Predicted vs actual lap times",
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        font=dict(size=12),
        margin=dict(l=60, r=40, t=50, b=50),
    )
    return fig
