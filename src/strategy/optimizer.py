"""Pit window optimization engine. PRD: §7 Pit Window Optimization Engine.

Single-car only: simulates pitting on the current lap and N future laps, applies
pit loss and degradation projections, computes total projected time per scenario,
and ranks strategies by net time. No traffic, safety car, or multi-car logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.strategy.pit_loss import get_pit_loss

if TYPE_CHECKING:
    from src.models.tire_degradation import TireDegradationModel

# Default number of future lap options to evaluate (pit on current, current+1, ..., current+N)
DEFAULT_PIT_WINDOW_SIZE = 10


def _project_stint_time(
    model: TireDegradationModel,
    track_id: str,
    compound: str,
    lap_start: int,
    lap_end: int,
    lap_in_stint_start: int,
    initial_fuel_kg: float,
    fuel_per_lap_kg: float,
    track_temp: float | None,
) -> float:
    """Sum predicted lap times (seconds) for laps lap_start..lap_end (inclusive)."""
    total = 0.0
    for lap in range(lap_start, lap_end + 1):
        fuel = initial_fuel_kg - (lap - 1) * fuel_per_lap_kg
        lap_in_stint = lap_in_stint_start + (lap - lap_start)
        total += model.predict_lap_time(
            track_id, compound, lap_in_stint, fuel, track_temp
        )
    return total


def optimize_pit_window(
    current_lap: int,
    current_compound: str,
    lap_in_stint: int,
    total_race_laps: int,
    track_id: str,
    new_compound: str,
    *,
    pit_window_size: int = DEFAULT_PIT_WINDOW_SIZE,
    initial_fuel_kg: float = 110.0,
    fuel_per_lap_kg: float = 1.8,
    track_temp: float | None = None,
    degradation_model: TireDegradationModel | None = None,
    pit_loss_overrides: dict[str, float] | None = None,
) -> pd.DataFrame:
    """
    Simulate pitting on the current lap and N future laps; rank strategies by total time.

    For each scenario: project lap times using the degradation model, add pit loss
    when applicable, sum to get total projected time from current_lap to end of race.
    Strategies are ranked by total time (ascending); best is rank 1.

    Single-car only. No traffic, safety car, or multi-car logic.

    Parameters
    ----------
    current_lap : int
        Race lap number we are about to start (1-based).
    current_compound : str
        Tire compound currently on car (SOFT, MEDIUM, HARD).
    lap_in_stint : int
        Lap number on this tyre set (1 = first lap of stint).
    total_race_laps : int
        Total number of laps in the race.
    track_id : str
        Track identifier (for degradation model and pit loss).
    new_compound : str
        Compound to fit at the pit stop.
    pit_window_size : int
        Number of future lap options: pit on current_lap, current_lap+1, ...,
        current_lap+pit_window_size (capped by total_race_laps).
    initial_fuel_kg : float
        Fuel mass (kg) at start of lap 1.
    fuel_per_lap_kg : float
        Fuel consumption per lap (kg).
    track_temp : float, optional
        Track temperature if the degradation model was fitted with it.
    degradation_model : TireDegradationModel, optional
        Fitted model; default is get_degradation_model().
    pit_loss_overrides : dict, optional
        Passed to get_pit_loss(..., overrides=...) for testing.

    Returns
    -------
    pd.DataFrame
        Columns: pit_lap (int or pd.NA for stay out), compound_after (str),
        total_time_sec (float), rank (int), time_delta_from_best_sec (float).
        Sorted by total_time_sec ascending (best first).
    """
    from src.models.tire_degradation import get_degradation_model

    if degradation_model is None:
        degradation_model = get_degradation_model()

    if current_lap > total_race_laps:
        return pd.DataFrame(
            columns=[
                "pit_lap",
                "compound_after",
                "total_time_sec",
                "rank",
                "time_delta_from_best_sec",
            ]
        )

    pit_loss_sec = get_pit_loss(track_id, overrides=pit_loss_overrides)

    # Valid pit laps: current_lap through min(current_lap + pit_window_size, total_race_laps)
    max_pit_lap = min(current_lap + pit_window_size, total_race_laps)
    pit_laps = list(range(current_lap, max_pit_lap + 1))

    rows = []

    # Stay-out scenario: no pit, current compound to end
    stay_out_time = _project_stint_time(
        degradation_model,
        track_id,
        current_compound.strip().upper(),
        current_lap,
        total_race_laps,
        lap_in_stint,
        initial_fuel_kg,
        fuel_per_lap_kg,
        track_temp,
    )
    rows.append({
        "pit_lap": pd.NA,
        "compound_after": current_compound.strip().upper(),
        "total_time_sec": stay_out_time,
    })

    # Pit-on-lap-P scenarios
    for pit_lap in pit_laps:
        # Laps on current tires: current_lap .. pit_lap (inclusive)
        time_current = _project_stint_time(
            degradation_model,
            track_id,
            current_compound.strip().upper(),
            current_lap,
            pit_lap,
            lap_in_stint,
            initial_fuel_kg,
            fuel_per_lap_kg,
            track_temp,
        )
        # Laps on new tires: pit_lap+1 .. total_race_laps, lap_in_stint 1,2,...
        laps_after_pit = total_race_laps - pit_lap
        if laps_after_pit > 0:
            fuel_at_pit_exit = initial_fuel_kg - pit_lap * fuel_per_lap_kg
            time_new = _project_stint_time(
                degradation_model,
                track_id,
                new_compound.strip().upper(),
                pit_lap + 1,
                total_race_laps,
                1,  # lap_in_stint starts at 1 after pit
                fuel_at_pit_exit,
                fuel_per_lap_kg,
                track_temp,
            )
        else:
            time_new = 0.0
        total_time = time_current + pit_loss_sec + time_new
        rows.append({
            "pit_lap": pit_lap,
            "compound_after": new_compound.strip().upper(),
            "total_time_sec": total_time,
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("total_time_sec", ascending=True).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    best_time = df["total_time_sec"].iloc[0]
    df["time_delta_from_best_sec"] = df["total_time_sec"] - best_time
    return df


def recommended_pit_lap(
    results: pd.DataFrame,
    *,
    prefer_stay_out: bool = False,
) -> int | None:
    """
    Return the recommended pit lap from optimizer results (best strategy).

    If the best strategy is stay-out, returns None. If prefer_stay_out is True
    and the best strategy is a tie with stay-out, returns None; otherwise
    returns the pit_lap of the best row (which may be the first pit option).

    Parameters
    ----------
    results : pd.DataFrame
        Output of optimize_pit_window (must have pit_lap, total_time_sec, rank).
    prefer_stay_out : bool
        If True and best time is tied with stay-out, return None.

    Returns
    -------
    int or None
        Recommended pit lap (None = stay out).
    """
    if results.empty:
        return None
    best = results.iloc[0]
    if pd.isna(best.get("pit_lap")):
        return None
    if prefer_stay_out:
        # If any row has same total_time_sec and is stay-out, prefer stay-out
        best_time = best["total_time_sec"]
        stay_out = results[results["pit_lap"].isna()]
        if not stay_out.empty and (stay_out["total_time_sec"] <= best_time).any():
            return None
    return int(best["pit_lap"])


def pit_window_range(
    results: pd.DataFrame,
    *,
    within_sec: float = 2.0,
) -> tuple[int | None, int | None]:
    """
    Return the pit lap range (min, max) among strategies within `within_sec` of the best.

    Only considers rows with numeric pit_lap (excludes stay-out). If the best
    strategy is stay-out, or no pit-on-lap rows are within the threshold,
    returns (None, None).

    Parameters
    ----------
    results : pd.DataFrame
        Output of optimize_pit_window (must have pit_lap, time_delta_from_best_sec).
    within_sec : float
        Include strategies with time_delta_from_best_sec <= within_sec.

    Returns
    -------
    tuple of (int or None, int or None)
        (min_pit_lap, max_pit_lap) for the window, or (None, None) if no pit window.
    """
    if results.empty or "pit_lap" not in results.columns or "time_delta_from_best_sec" not in results.columns:
        return (None, None)
    best = results.iloc[0]
    if pd.isna(best.get("pit_lap")):
        return (None, None)
    pit_rows = results.loc[results["pit_lap"].notna() & (results["time_delta_from_best_sec"] <= within_sec)]
    if pit_rows.empty:
        return (None, None)
    min_lap = int(pit_rows["pit_lap"].min())
    max_lap = int(pit_rows["pit_lap"].max())
    return (min_lap, max_lap)
