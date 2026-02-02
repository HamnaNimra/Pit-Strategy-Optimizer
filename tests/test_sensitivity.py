"""Tests for parameter sensitivity (pit loss ± delta)."""

import pytest

from src.strategy.sensitivity import sensitivity_pit_loss


def test_sensitivity_pit_loss_returns_dict(fitted_degradation_model):
    """sensitivity_pit_loss returns dict with expected keys and human-readable message."""
    out = sensitivity_pit_loss(
        current_lap=10,
        current_compound="SOFT",
        lap_in_stint=5,
        total_race_laps=57,
        track_id="TestTrack",
        new_compound="MEDIUM",
        pit_loss_delta_sec=2.0,
        degradation_model=fitted_degradation_model,
        pit_window_size=10,
    )
    assert "base_pit_loss_sec" in out
    assert "base_rec_lap" in out
    assert "plus_delta_rec_lap" in out
    assert "minus_delta_rec_lap" in out
    assert "pit_loss_delta_sec" in out
    assert "message" in out
    assert isinstance(out["message"], str)
    assert len(out["message"]) > 0
    assert "pit loss" in out["message"].lower() or "2" in out["message"]


def test_sensitivity_pit_loss_message_mentions_delta(fitted_degradation_model):
    """message refers to delta (e.g. ±2 s)."""
    out = sensitivity_pit_loss(
        current_lap=10,
        current_compound="SOFT",
        lap_in_stint=5,
        total_race_laps=57,
        track_id="TestTrack",
        new_compound="MEDIUM",
        pit_loss_delta_sec=2.0,
        degradation_model=fitted_degradation_model,
    )
    assert "2" in out["message"]
