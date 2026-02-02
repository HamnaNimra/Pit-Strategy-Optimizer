"""Unit tests for strategy explanation (rule-based, no ML)."""

import pandas as pd
import pytest

from src.strategy.explanation import (
    explain_why_pit_window_opens,
    explain_when_degradation_overtakes,
    explain_cost_of_delaying,
    explain_cost_of_advancing,
    explain_strategy,
)


def test_explain_why_pit_window_opens():
    """Explanation mentions pit loss and degradation."""
    text = explain_why_pit_window_opens(
        pit_loss_sec=22.0, degradation_rate_sec_per_lap=0.1
    )
    assert "22" in text or "pit loss" in text.lower()
    assert "degradation" in text.lower()


def test_explain_when_degradation_overtakes():
    """Break-even lap count is approximately pit_loss / rate."""
    text = explain_when_degradation_overtakes(
        pit_loss_sec=20.0, degradation_rate_sec_per_lap=1.0
    )
    assert "lap" in text.lower()
    assert "20" in text or "220" in text  # 20 s / 1 s/lap ≈ 20 laps


def test_explain_cost_of_delaying():
    """Cost of delaying mentions degradation rate."""
    text = explain_cost_of_delaying(degradation_rate_sec_per_lap=0.15)
    assert "0.15" in text or "delay" in text.lower()


def test_explain_cost_of_advancing_from_results():
    """Cost of advancing uses time_delta_from_best_sec from results."""
    results = pd.DataFrame(
        {
            "pit_lap": [10, 11, pd.NA],
            "time_delta_from_best_sec": [0.0, 1.5, 0.0],
            "compound_after": ["MEDIUM", "MEDIUM", "SOFT"],
        }
    )
    text = explain_cost_of_advancing(results, best_pit_lap=10)
    assert "1.5" in text or "earlier" in text.lower()


def test_explain_strategy_returns_dict(fitted_degradation_model):
    """explain_strategy returns dict with expected keys."""
    from src.strategy.optimizer import optimize_pit_window

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
    ex = explain_strategy(
        results,
        "TestTrack",
        "SOFT",
        pit_loss_sec=22.0,
        degradation_rate_sec_per_lap=0.1,
        degradation_model=fitted_degradation_model,
    )
    assert "why_pit_window_opens" in ex
    assert "when_degradation_overtakes" in ex
    assert "cost_of_delaying" in ex
    assert "cost_of_advancing" in ex
    assert "summary" in ex
    assert "summary_display" in ex
    assert "\n" in ex["summary_display"] or "•" in ex["summary_display"]
