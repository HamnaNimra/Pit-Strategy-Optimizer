"""Export helpers for portfolio-ready figures: PNG and interactive HTML."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import matplotlib.figure
    import plotly.graph_objects as go


def export_figure_png(
    fig: matplotlib.figure.Figure,
    path: str | Path,
    *,
    dpi: int = 150,
    bbox_inches: str = "tight",
) -> Path:
    """
    Save a matplotlib Figure as PNG for clear, readable display.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to save (e.g. ax.get_figure()).
    path : str or Path
        Output file path (.png).
    dpi : int
        Resolution (default 150 for portfolio).
    bbox_inches : str
        Passed to savefig (default "tight").

    Returns
    -------
    Path
        Resolved output path.
    """
    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches=bbox_inches)
    return path.resolve()


def export_plotly_html(
    fig,  # plotly.graph_objects.Figure
    path: str | Path,
    *,
    config: dict | None = None,
) -> Path:
    """
    Save a plotly Figure as standalone interactive HTML.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
        Plotly figure.
    path : str or Path
        Output file path (.html).
    config : dict, optional
        plotly.write_html config (e.g. config={"displayModeBar": True}).

    Returns
    -------
    Path
        Resolved output path.
    """
    import plotly.graph_objects as go

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(path), config=config or {})
    return path.resolve()
