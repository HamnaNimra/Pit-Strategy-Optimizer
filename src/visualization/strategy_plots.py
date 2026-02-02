"""Strategy timeline and stint plots.

Strategy timelines with pit windows and stint segments. All data passed in;
no hardcoded race or driver assumptions. Plots are labeled and readable.
"""

from __future__ import annotations

from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Default figure size for readable, portfolio-ready plots
DEFAULT_FIGSIZE = (10, 4)

# Default colors for compounds (caller can override)
DEFAULT_COMPOUND_COLORS = {
    "SOFT": "C0",
    "MEDIUM": "C1",
    "HARD": "C2",
}


def plot_strategy_timeline(
    stints: Sequence[tuple[int, int, str]],
    *,
    pit_laps: Sequence[int] | None = None,
    pit_window: tuple[int, int] | None = None,
    ax: plt.Axes | None = None,
    figsize: tuple[float, float] = DEFAULT_FIGSIZE,
    title: str | None = None,
    xlabel: str = "Lap number",
    compound_colors: dict[str, str] | None = None,
) -> plt.Axes:
    """
    Plot a strategy timeline: stint segments, pit laps, and optional pit window.

    Stints are drawn as horizontal segments (start_lap to end_lap) colored by
    compound. Pit laps are vertical lines; pit window is a shaded band.

    Parameters
    ----------
    stints : sequence of (start_lap, end_lap, compound)
        Ordered stints (e.g. [(1, 28, "SOFT"), (29, 57, "MEDIUM")]).
        start_lap and end_lap are inclusive.
    pit_laps : sequence of int, optional
        Lap numbers where pit stops occurred (vertical lines).
    pit_window : (lap_min, lap_max), optional
        Recommended pit window as shaded region (lap_min and lap_max inclusive).
    ax : matplotlib Axes, optional
        Axes to plot on.
    title : str, optional
        Plot title.
    xlabel : str
        X-axis label.
    compound_colors : dict[str, str], optional
        Map compound name -> matplotlib color. Default: SOFT/MEDIUM/HARD -> C0/C1/C2.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    colors = compound_colors if compound_colors is not None else DEFAULT_COMPOUND_COLORS

    # Stint segments: horizontal bars at y=0, length = end - start + 1
    # Legend: only add label once per compound (avoid duplicate legend entries)
    seen_compounds = set()
    y_pos = 0
    for start, end, compound in stints:
        compound_upper = str(compound).upper()
        color = colors.get(compound_upper, "gray")
        label = compound_upper if compound_upper not in seen_compounds else None
        if label:
            seen_compounds.add(compound_upper)
        ax.barh(
            y_pos,
            end - start + 1,
            left=start,
            height=0.5,
            color=color,
            label=label,
            edgecolor="black",
            linewidth=0.5,
        )
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([0])
    ax.set_yticklabels(["Stint"])
    ax.set_xlabel(xlabel)
    if title:
        ax.set_title(title)

    # Pit laps: vertical lines
    if pit_laps:
        for lap in pit_laps:
            ax.axvline(x=lap, color="black", linestyle="--", linewidth=1, alpha=0.7)
        # Single legend entry for pit stops
        ax.axvline(
            x=-1,
            color="black",
            linestyle="--",
            linewidth=1,
            alpha=0.7,
            label="Pit stop",
        )

    # Pit window: shaded region
    if pit_window is not None:
        lap_min, lap_max = pit_window
        ax.axvspan(
            lap_min - 0.5, lap_max + 0.5, alpha=0.2, color="green", label="Pit window"
        )

    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, axis="x", alpha=0.3)
    return ax


def plot_strategy_timeline_from_laps(
    laps: pd.DataFrame,
    pit_stops: pd.DataFrame,
    *,
    driver_filter: str | int | None = None,
    lap_col: str = "LapNumber",
    compound_col: str = "Compound",
    stint_col: str = "stint_id",
    pit_lap_col: str = "LapNumber",
    pit_window: tuple[int, int] | None = None,
    ax: plt.Axes | None = None,
    title: str | None = None,
) -> plt.Axes:
    """
    Build stint list from laps and pit_stops, then plot strategy timeline.

    Infers stints from laps (group by driver and stint_col) or from pit_stops
    (stint boundaries). If driver_filter is set, only that driver is plotted.
    Laps and pit_stops must have DriverNumber; laps must have lap_col, compound_col,
    and optionally stint_col; pit_stops must have pit_lap_col.

    Parameters
    ----------
    laps : pd.DataFrame
        Lap-level data with lap_col, compound_col, DriverNumber; optional stint_col.
    pit_stops : pd.DataFrame
        One row per pit; DriverNumber, pit_lap_col.
    driver_filter : str or int, optional
        If set, filter to this driver.
    lap_col, compound_col, stint_col, pit_lap_col : str
        Column names.
    pit_window : (lap_min, lap_max), optional
        Passed to plot_strategy_timeline.
    ax, title : optional
        Passed to plot_strategy_timeline.

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
        or compound_col not in subset.columns
    ):
        if ax is None:
            _, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
        return ax

    # Build stints: by stint_id or by compound change
    stints = []
    subset = subset.sort_values(lap_col)
    if stint_col in subset.columns:
        for _, grp in subset.groupby(stint_col):
            grp = grp.sort_values(lap_col)
            start = int(grp[lap_col].min())
            end = int(grp[lap_col].max())
            compound = grp[compound_col].mode().iloc[0] if not grp.empty else "UNKNOWN"
            stints.append((start, end, str(compound).strip().upper()))
    else:
        cur_start = cur_end = None
        cur_compound = None
        for _, row in subset.iterrows():
            lap = int(row[lap_col])
            comp = str(row[compound_col]).strip().upper()
            if cur_compound is None or comp != cur_compound:
                if cur_compound is not None:
                    stints.append((cur_start, cur_end, cur_compound))
                cur_start = cur_end = lap
                cur_compound = comp
            else:
                cur_end = lap
        if cur_compound is not None:
            stints.append((cur_start, cur_end, cur_compound))
    stints = sorted(stints, key=lambda s: s[0])

    pit_laps_list = None
    if (
        not pit_stops.empty
        and "DriverNumber" in pit_stops.columns
        and pit_lap_col in pit_stops.columns
    ):
        ps = pit_stops.copy()
        if driver_filter is not None:
            ps = ps[ps["DriverNumber"].astype(str) == str(driver_filter)]
        if not ps.empty:
            pit_laps_list = ps[pit_lap_col].dropna().astype(int).tolist()
            pit_laps_list = sorted(set(pit_laps_list))

    return plot_strategy_timeline(
        stints,
        pit_laps=pit_laps_list,
        pit_window=pit_window,
        ax=ax,
        title=title,
    )


def plot_strategy_timeline_plotly(
    stints: Sequence[tuple[int, int, str]],
    *,
    pit_laps: Sequence[int] | None = None,
    pit_window: tuple[int, int] | None = None,
    title: str | None = None,
    xlabel: str = "Lap number",
    compound_colors: dict[str, str] | None = None,
):
    """
    Build an interactive plotly figure: strategy timeline with stints, pit stops, pit window.
    Use with export_plotly_html(fig, path) for portfolio display.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        raise ImportError("plotly is required for HTML export; pip install plotly") from None
    colors = compound_colors if compound_colors is not None else DEFAULT_COMPOUND_COLORS
    fig = go.Figure()
    seen_compounds = set()
    for start, end, compound in stints:
        comp_upper = str(compound).upper()
        color = colors.get(comp_upper, "gray")
        name = comp_upper if comp_upper not in seen_compounds else None
        if name:
            seen_compounds.add(comp_upper)
        fig.add_vrect(
            x0=start - 0.5,
            x1=end + 0.5,
            fillcolor=color,
            opacity=0.6,
            layer="below",
            line_width=0,
        )
        # Legend entry (invisible trace)
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=12, color=color, symbol="square"),
                name=name or comp_upper,
                showlegend=bool(name),
            )
        )
    if pit_laps:
        for lap in pit_laps:
            fig.add_vline(x=lap, line_dash="dash", line_color="black", line_width=1)
    if pit_window is not None:
        lap_min, lap_max = pit_window
        fig.add_vrect(x0=lap_min - 0.5, x1=lap_max + 0.5, fillcolor="green", opacity=0.2)
    x_min = min(s[0] for s in stints) - 1 if stints else 0
    x_max = max(s[1] for s in stints) + 1 if stints else 60
    fig.update_layout(
        title=title or "Strategy timeline",
        xaxis_title=xlabel,
        xaxis=dict(range=[x_min, x_max]),
        yaxis=dict(visible=False, range=[0, 1]),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        font=dict(size=12),
        margin=dict(l=40, r=40, t=50, b=50),
    )
    return fig
