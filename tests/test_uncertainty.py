"""Tests for uncertainty-aware recommendations: DegradationWrapper, sensitivity_degradation, vsc_recommendation, recommendation_bundle."""

import pytest

from src.strategy.sensitivity import (
    DegradationWrapper,
    sensitivity_degradation,
    vsc_recommendation,
)
from src.strategy.uncertainty import recommendation_bundle


def test_degradation_wrapper_returns_base_plus_delta(fitted_degradation_model):
    """DegradationWrapper returns base + (lap_in_stint - 1) * delta for a known model."""
    base = fitted_degradation_model
    delta = 0.02
    wrapper_plus = DegradationWrapper(base, delta)
    base_sec = base.predict_lap_time("TestTrack", "SOFT", 1, 100.0)
    wrapped_sec = wrapper_plus.predict_lap_time("TestTrack", "SOFT", 1, 100.0)
    assert wrapped_sec == pytest.approx(base_sec + 0)  # lap_in_stint 1 -> +0
    base_sec_5 = base.predict_lap_time("TestTrack", "SOFT", 5, 95.0)
    wrapped_sec_5 = wrapper_plus.predict_lap_time("TestTrack", "SOFT", 5, 95.0)
    assert wrapped_sec_5 == pytest.approx(base_sec_5 + (5 - 1) * delta)


def test_sensitivity_degradation_returns_dict(fitted_degradation_model):
    """sensitivity_degradation returns dict with expected keys and message mentions degradation."""
    out = sensitivity_degradation(
        current_lap=10,
        current_compound="SOFT",
        lap_in_stint=5,
        total_race_laps=57,
        track_id="TestTrack",
        new_compound="MEDIUM",
        degradation_delta_sec_per_lap=0.02,
        degradation_model=fitted_degradation_model,
        pit_window_size=10,
    )
    assert "base_rec_lap" in out
    assert "plus_delta_rec_lap" in out
    assert "minus_delta_rec_lap" in out
    assert "message" in out
    assert isinstance(out["message"], str)
    assert "degradation" in out["message"].lower() or "0.02" in out["message"]


def test_vsc_recommendation_returns_dict(fitted_degradation_model):
    """vsc_recommendation returns dict with vsc_rec_lap and message; vsc_rec_lap can differ when factor < 1."""
    out = vsc_recommendation(
        current_lap=10,
        current_compound="SOFT",
        lap_in_stint=5,
        total_race_laps=57,
        track_id="TestTrack",
        new_compound="MEDIUM",
        vsc_pit_loss_factor=0.5,
        degradation_model=fitted_degradation_model,
        pit_window_size=10,
    )
    assert "vsc_rec_lap" in out
    assert "message" in out
    assert isinstance(out["message"], str)
    assert "VSC" in out["message"] or "vsc" in out["message"].lower()


def test_recommendation_bundle_contains_all_fields(fitted_degradation_model):
    """recommendation_bundle returns dict with recommended_lap, pit_window_min/max, and three message fields."""
    bundle = recommendation_bundle(
        current_lap=10,
        current_compound="SOFT",
        lap_in_stint=5,
        total_race_laps=57,
        track_id="TestTrack",
        new_compound="MEDIUM",
        degradation_model=fitted_degradation_model,
        include_explanation=False,
    )
    assert "recommended_lap" in bundle
    assert "pit_window_min" in bundle
    assert "pit_window_max" in bundle
    assert "sensitivity_pit_loss_message" in bundle
    assert "sensitivity_degradation_message" in bundle
    assert "vsc_message" in bundle
    assert isinstance(bundle["sensitivity_pit_loss_message"], str)
    assert isinstance(bundle["sensitivity_degradation_message"], str)
    assert isinstance(bundle["vsc_message"], str)
