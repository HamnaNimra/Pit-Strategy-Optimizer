"""Unit tests for pit window optimizer (optimize_pit_window, recommended_pit_lap)."""

import pandas as pd
import pytest

from src.strategy.optimizer import optimize_pit_window, recommended_pit_lap


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
