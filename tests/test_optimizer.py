"""Unit tests for pit window optimizer (optimize_pit_window, recommended_pit_lap)."""

import pandas as pd
import pytest

from src.strategy.optimizer import (
    optimize_pit_window,
    pit_window_range,
    recommended_pit_lap,
)


def test_optimize_pit_window_returns_dataframe(fitted_degradation_model):
    """optimize_pit_window returns DataFrame with expected columns."""
    results = optimize_pit_window(
        current_lap=10,
        current_compound="SOFT",
        lap_in_stint=5,
        total_race_laps=57,
        track_id="TestTrack",
        new_compound="MEDIUM",
        degradation_model=fitted_degradation_model,
        pit_loss_overrides={"testtrack": 22.0},
    )
    assert "pit_lap" in results.columns
    assert "compound_after" in results.columns
    assert "total_time_sec" in results.columns
    assert "rank" in results.columns
    assert "time_delta_from_best_sec" in results.columns
    assert results["rank"].iloc[0] == 1
    assert results["time_delta_from_best_sec"].min() == 0.0


def test_optimize_pit_window_sorted_by_time(fitted_degradation_model):
    """Results are sorted by total_time_sec ascending."""
    results = optimize_pit_window(
        current_lap=10,
        current_compound="SOFT",
        lap_in_stint=5,
        total_race_laps=57,
        track_id="TestTrack",
        new_compound="MEDIUM",
        degradation_model=fitted_degradation_model,
        pit_loss_overrides={"testtrack": 22.0},
    )
    assert results["total_time_sec"].is_monotonic_increasing


def test_recommended_pit_lap_best_strategy(fitted_degradation_model):
    """recommended_pit_lap returns pit_lap of best row or None for stay-out."""
    results = optimize_pit_window(
        current_lap=10,
        current_compound="SOFT",
        lap_in_stint=5,
        total_race_laps=57,
        track_id="TestTrack",
        new_compound="MEDIUM",
        degradation_model=fitted_degradation_model,
        pit_loss_overrides={"testtrack": 22.0},
    )
    rec = recommended_pit_lap(results)
    # Best may be stay-out (NA) or a lap number
    assert rec is None or isinstance(rec, int)


def test_recommended_pit_lap_empty_returns_none():
    """recommended_pit_lap on empty DataFrame returns None."""
    assert recommended_pit_lap(pd.DataFrame()) is None


def test_pit_window_range_within_sec(fitted_degradation_model):
    """pit_window_range returns (min, max) of pit laps within threshold."""
    results = optimize_pit_window(
        current_lap=10,
        current_compound="SOFT",
        lap_in_stint=5,
        total_race_laps=57,
        track_id="TestTrack",
        new_compound="MEDIUM",
        degradation_model=fitted_degradation_model,
        pit_loss_overrides={"testtrack": 22.0},
    )
    pmin, pmax = pit_window_range(results, within_sec=2.0)
    if results.iloc[0].get("pit_lap") is not pd.NA and not pd.isna(results.iloc[0].get("pit_lap")):
        assert pmin is not None and pmax is not None
        assert pmin <= pmax
    else:
        assert (pmin, pmax) == (None, None)


def test_pit_window_range_stay_out_best():
    """pit_window_range returns (None, None) when best is stay-out."""
    # Synthetic results: best row is stay-out (pit_lap NA)
    df = pd.DataFrame(
        {
            "pit_lap": [pd.NA, 10, 11],
            "total_time_sec": [1000.0, 1002.0, 1005.0],
            "time_delta_from_best_sec": [0.0, 2.0, 5.0],
        }
    )
    pmin, pmax = pit_window_range(df, within_sec=2.0)
    assert (pmin, pmax) == (None, None)


def test_pit_window_range_empty():
    """pit_window_range on empty or missing columns returns (None, None)."""
    assert pit_window_range(pd.DataFrame(), within_sec=2.0) == (None, None)
    assert pit_window_range(pd.DataFrame({"x": [1]}), within_sec=2.0) == (None, None)
