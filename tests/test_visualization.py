"""Tests for visualization: strategy timeline (matplotlib + plotly), plotly color handling."""

import pytest

from src.visualization.strategy_plots import (
    DEFAULT_COMPOUND_COLORS,
    DEFAULT_COMPOUND_COLORS_PLOTLY,
    plot_strategy_timeline,
    plot_strategy_timeline_plotly,
    plot_strategy_timeline_from_laps,
)
from src.visualization.strategy_plots import _plotly_color


def test_plotly_color_maps_matplotlib_cycle():
    """_plotly_color maps C0/C1/C2 to hex for Plotly."""
    assert _plotly_color("C0") == "#1f77b4"
    assert _plotly_color("C1") == "#ff7f0e"
    assert _plotly_color("C2") == "#2ca02c"


def test_plotly_color_passthrough_valid():
    """_plotly_color passes through hex and CSS names."""
    assert _plotly_color("#ff0000") == "#ff0000"
    assert _plotly_color("green") == "green"
    assert _plotly_color("gray") == "gray"


def test_plot_strategy_timeline_returns_axes():
    """plot_strategy_timeline returns matplotlib Axes with stints."""
    stints = [(1, 20, "SOFT"), (21, 57, "MEDIUM")]
    ax = plot_strategy_timeline(
        stints, pit_laps=[20], pit_window=(18, 22), title="Test"
    )
    assert ax is not None
    assert ax.get_title() == "Test"


def test_plot_strategy_timeline_plotly_returns_figure_valid_colors():
    """plot_strategy_timeline_plotly returns Plotly figure; default colors are Plotly-valid (no C0)."""
    stints = [(1, 20, "SOFT"), (21, 40, "MEDIUM")]
    fig = plot_strategy_timeline_plotly(
        stints, pit_laps=[20], pit_window=(18, 22), title="Test"
    )
    assert fig is not None
    # Layout shapes (vrects) must not use matplotlib "C0" etc.
    layout_str = str(fig.layout)
    assert "C0" not in layout_str
    assert "C1" not in layout_str
    assert "C2" not in layout_str


def test_plot_strategy_timeline_plotly_with_explicit_hex_colors():
    """plot_strategy_timeline_plotly accepts compound_colors with hex."""
    stints = [(1, 10, "SOFT")]
    fig = plot_strategy_timeline_plotly(
        stints,
        compound_colors={"SOFT": "#1f77b4"},
        title="Test",
    )
    assert fig is not None
    assert fig.layout.title.text == "Test"


def test_plot_strategy_timeline_from_laps_empty_pit_stops():
    """plot_strategy_timeline_from_laps handles empty pit_stops."""
    import pandas as pd

    laps = pd.DataFrame(
        {
            "DriverNumber": ["1", "1", "1"],
            "LapNumber": [1, 2, 3],
            "Compound": ["SOFT", "SOFT", "SOFT"],
            "stint_id": [1, 1, 1],
        }
    )
    pit_stops = pd.DataFrame(columns=["DriverNumber", "LapNumber"])
    ax = plot_strategy_timeline_from_laps(
        laps, pit_stops, driver_filter="1", title="Test"
    )
    assert ax is not None
