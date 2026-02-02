"""Rule-based strategy explanation layer. PRD: §8 Strategy Explanation Layer.

Human-readable explanations from intermediate calculations only: why the pit
window opens, when degradation overtakes pit loss, and cost of delaying or
advancing the stop. No machine learning or language models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.strategy.pit_loss import get_pit_loss

if TYPE_CHECKING:
    from src.models.tire_degradation import TireDegradationModel


def _format_sec(sec: float) -> str:
    """Format seconds to one decimal for display."""
    return f"{sec:.1f}"


def explain_why_pit_window_opens(
    pit_loss_sec: float,
    degradation_rate_sec_per_lap: float,
    *,
    break_even_laps: float | None = None,
) -> str:
    """
    Rule-based explanation: why the pit window opens.

    Uses pit loss and degradation rate only. The window opens when staying out
    would cost more (cumulative degradation) than pitting (pit loss).

    Parameters
    ----------
    pit_loss_sec : float
        Track pit loss in seconds.
    degradation_rate_sec_per_lap : float
        Current compound degradation rate (s/lap) from the model.
    break_even_laps : float, optional
        If provided, used instead of pit_loss / degradation_rate.

    Returns
    -------
    str
        Human-readable sentence(s).
    """
    if break_even_laps is None and degradation_rate_sec_per_lap > 0:
        break_even_laps = pit_loss_sec / degradation_rate_sec_per_lap
    if break_even_laps is None or degradation_rate_sec_per_lap <= 0:
        return (
            "The pit window opens when the time lost to tire degradation would "
            f"exceed the fixed pit loss ({_format_sec(pit_loss_sec)} s). "
            "Degradation rate is zero or negative in the model, so the break-even "
            "lap count is not defined."
        )
    n = int(round(break_even_laps))
    return (
        "The pit window opens when staying out would cost more than pitting. "
        f"Pit loss is {_format_sec(pit_loss_sec)} seconds; degradation on current tires "
        f"is {_format_sec(degradation_rate_sec_per_lap)} seconds per lap. "
        f"After about {n} laps, cumulative degradation overtakes pit loss."
    )


def explain_when_degradation_overtakes(
    pit_loss_sec: float,
    degradation_rate_sec_per_lap: float,
) -> str:
    """
    Rule-based explanation: when degradation overtakes pit loss.

    Break-even lap count N such that N × degradation_rate ≈ pit_loss.

    Parameters
    ----------
    pit_loss_sec : float
        Track pit loss in seconds.
    degradation_rate_sec_per_lap : float
        Degradation rate (s/lap) for current compound.

    Returns
    -------
    str
        Human-readable sentence(s).
    """
    if degradation_rate_sec_per_lap <= 0:
        return (
            "Degradation does not overtake pit loss in the model "
            "(degradation rate is zero or negative)."
        )
    n = pit_loss_sec / degradation_rate_sec_per_lap
    n_round = int(round(n))
    return (
        f"Degradation overtakes pit loss after about {n_round} laps "
        f"({n_round} × {_format_sec(degradation_rate_sec_per_lap)} seconds per lap "
        f"≈ {_format_sec(pit_loss_sec)} seconds pit loss)."
    )


def explain_cost_of_delaying(
    degradation_rate_sec_per_lap: float,
    *,
    laps_delayed: int = 1,
) -> str:
    """
    Rule-based explanation: cost of delaying the pit stop.

    Each extra lap on degrading tires costs approximately degradation_rate seconds.

    Parameters
    ----------
    degradation_rate_sec_per_lap : float
        Degradation rate (s/lap) for current compound.
    laps_delayed : int
        Number of laps delayed (default 1).

    Returns
    -------
    str
        Human-readable sentence(s).
    """
    cost = laps_delayed * degradation_rate_sec_per_lap
    if laps_delayed == 1:
        return (
            f"Each lap delayed costs about {_format_sec(degradation_rate_sec_per_lap)} seconds "
            "(current compound degradation rate)."
        )
    return (
        f"Delaying the stop by {laps_delayed} laps costs about {_format_sec(cost)} seconds "
        f"({laps_delayed} × {_format_sec(degradation_rate_sec_per_lap)} seconds per lap)."
    )


def explain_cost_of_advancing(
    results: pd.DataFrame,
    best_pit_lap: int | None,
) -> str:
    """
    Rule-based explanation: cost of pitting one lap earlier than optimal.

    Uses optimizer results only: finds the strategy that pits one lap earlier
    than the best and reports its time_delta_from_best_sec.

    Parameters
    ----------
    results : pd.DataFrame
        Output of optimize_pit_window (columns: pit_lap, time_delta_from_best_sec).
    best_pit_lap : int or None
        Recommended pit lap (None = stay out). From recommended_pit_lap(results).

    Returns
    -------
    str
        Human-readable sentence(s).
    """
    if results.empty or "time_delta_from_best_sec" not in results.columns:
        return "Cost of advancing cannot be derived from the given results."

    if best_pit_lap is None:
        # Best is stay-out; "advancing" = pitting now. Cost = delta of first pit option.
        pit_rows = results[results["pit_lap"].notna()]
        if pit_rows.empty:
            return "No pit scenario in results; cost of advancing is not defined."
        delta = pit_rows["time_delta_from_best_sec"].iloc[0]
        return (
            f"Pitting now (instead of staying out) costs about {_format_sec(delta)} seconds "
            "versus the optimal stay-out strategy."
        )

    # Best strategy pits on best_pit_lap. Strategy that pits one lap earlier = pit_lap == best_pit_lap - 1
    earlier = results[results["pit_lap"] == best_pit_lap - 1]
    if earlier.empty:
        return (
            f"The optimizer did not evaluate pitting one lap earlier than lap {best_pit_lap}; "
            "cost of advancing is not available."
        )
    delta = earlier["time_delta_from_best_sec"].iloc[0]
    return (
        f"Pitting one lap earlier than optimal (lap {best_pit_lap - 1} instead of {best_pit_lap}) "
        f"costs about {_format_sec(delta)} seconds."
    )


def explain_strategy(
    results: pd.DataFrame,
    track_id: str,
    current_compound: str,
    *,
    pit_loss_sec: float | None = None,
    degradation_rate_sec_per_lap: float | None = None,
    degradation_model: TireDegradationModel | None = None,
    pit_loss_overrides: dict[str, float] | None = None,
) -> dict[str, str]:
    """
    Build a full set of rule-based strategy explanations from intermediate data.

    Uses optimizer results, pit loss, and degradation rate only. No ML or
    language models. All text is from fixed templates and computed numbers.

    Parameters
    ----------
    results : pd.DataFrame
        Output of optimize_pit_window (columns: pit_lap, time_delta_from_best_sec, etc.).
    track_id : str
        Track identifier (for pit loss and degradation lookup).
    current_compound : str
        Current tire compound (for degradation rate).
    pit_loss_sec : float, optional
        If None, obtained from get_pit_loss(track_id, overrides=pit_loss_overrides).
    degradation_rate_sec_per_lap : float, optional
        If None, obtained from diagnostics.degradation_rate_seconds_per_lap.
    degradation_model : TireDegradationModel, optional
        Passed to degradation_rate_seconds_per_lap if rate not provided.
    pit_loss_overrides : dict, optional
        Passed to get_pit_loss for testing.

    Returns
    -------
    dict[str, str]
        Keys: why_pit_window_opens, when_degradation_overtakes, cost_of_delaying,
        cost_of_advancing, summary. Values are human-readable strings.
    """
    if pit_loss_sec is None:
        pit_loss_sec = get_pit_loss(track_id, overrides=pit_loss_overrides)
    if degradation_rate_sec_per_lap is None:
        from src.models.diagnostics import degradation_rate_seconds_per_lap
        degradation_rate_sec_per_lap = degradation_rate_seconds_per_lap(
            track_id, current_compound.strip().upper(), model=degradation_model
        )

    from src.strategy.optimizer import recommended_pit_lap
    best_pit_lap = recommended_pit_lap(results)

    why = explain_why_pit_window_opens(
        pit_loss_sec, degradation_rate_sec_per_lap
    )
    when = explain_when_degradation_overtakes(
        pit_loss_sec, degradation_rate_sec_per_lap
    )
    cost_delay = explain_cost_of_delaying(degradation_rate_sec_per_lap)
    cost_advance = explain_cost_of_advancing(results, best_pit_lap)

    summary_parts = [why, when, cost_delay, cost_advance]
    summary = " ".join(summary_parts)
    # Human-readable display: one line per section (for CLI / portfolio)
    summary_display = "\n".join(
        ["• " + why, "• " + when, "• " + cost_delay, "• " + cost_advance]
    )

    return {
        "why_pit_window_opens": why,
        "when_degradation_overtakes": when,
        "cost_of_delaying": cost_delay,
        "cost_of_advancing": cost_advance,
        "summary": summary,
        "summary_display": summary_display,
    }
