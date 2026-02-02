"""Unit tests for tire degradation model (fit, predict, coefficients, save/load)."""

import pandas as pd
import pytest

from src.models.tire_degradation import TireDegradationModel, predict_lap_time


def test_fit_requires_compound_in_slick_set():
    """fit raises for compound not in SOFT, MEDIUM, HARD."""
    model = TireDegradationModel()
    laps = pd.DataFrame({
        "LapNumber": [1, 2],
        "lap_in_stint": [1, 2],
        "estimated_fuel_kg": [110, 108],
        "LapTime": pd.to_timedelta([90, 91], unit="s"),
        "Compound": ["SOFT", "SOFT"],
    })
    with pytest.raises(ValueError, match="Compound must be"):
        model.fit(laps, "TestTrack", "INTERMEDIATE")


def test_fit_and_predict(fitted_degradation_model):
    """Fitted model returns numeric prediction for (track, compound, lap_in_stint, fuel)."""
    model = fitted_degradation_model
    t = model.predict_lap_time("TestTrack", "SOFT", lap_in_stint=5, fuel_kg=100.0)
    assert isinstance(t, (int, float))
    assert t > 0


def test_get_coefficients(fitted_degradation_model):
    """get_coefficients returns intercept and feature coefficients."""
    model = fitted_degradation_model
    coefs = model.get_coefficients("TestTrack", "SOFT")
    assert "intercept" in coefs
    assert "lap_in_stint" in coefs
    assert "estimated_fuel_kg" in coefs


def test_predict_raises_for_unfitted_track_compound():
    """predict_lap_time raises when (track, compound) not fitted."""
    model = TireDegradationModel()
    with pytest.raises(ValueError, match="No fitted model"):
        model.predict_lap_time("UnknownTrack", "SOFT", 1, 100.0)


def test_save_and_load(fitted_degradation_model, temp_models_dir):
    """save then load restores models; predict matches."""
    model = fitted_degradation_model
    model.save(temp_models_dir)
    loaded = TireDegradationModel()
    loaded.load(temp_models_dir)
    t1 = model.predict_lap_time("TestTrack", "SOFT", 3, 105.0)
    t2 = loaded.predict_lap_time("TestTrack", "SOFT", 3, 105.0)
    assert t1 == t2


def test_predict_lap_time_module_function(fitted_degradation_model):
    """predict_lap_time(model=...) uses provided model."""
    t = predict_lap_time("TestTrack", "SOFT", 2, 108.0, model=fitted_degradation_model)
    assert isinstance(t, (int, float))
    assert t > 0
