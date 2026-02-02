"""End-to-end integration tests (synthetic data only; no FastF1 API)."""

import pandas as pd
import pytest

from src.data_pipeline import add_stint_features
from src.models.tire_degradation import TireDegradationModel
from src.strategy.optimizer import optimize_pit_window, recommended_pit_lap
from src.strategy.explanation import explain_strategy
from src.strategy.pit_loss import set_pit_loss_for_testing


def test_e2e_synthetic_laps_to_recommendation(synthetic_laps, synthetic_pit_stops):
    """Full flow: laps + pit_stops -> stint features -> fit model -> optimize -> recommend -> explain."""
    # 1. Stint features
    laps = add_stint_features(synthetic_laps, synthetic_pit_stops)
    assert not laps.empty
    assert "lap_in_stint" in laps.columns
    assert "estimated_fuel_kg" in laps.columns

    # 2. Fit degradation model for TestTrack
    model = TireDegradationModel()
    soft = laps[laps["Compound"] == "SOFT"].head(15)
    medium = laps[laps["Compound"] == "MEDIUM"].head(15)
    model.fit(soft, "TestTrack", "SOFT", lap_time_col="LapTime", lap_in_stint_col="lap_in_stint", fuel_col="estimated_fuel_kg")
    model.fit(medium, "TestTrack", "MEDIUM", lap_time_col="LapTime", lap_in_stint_col="lap_in_stint", fuel_col="estimated_fuel_kg")

    # 3. Pit loss override so we don't depend on built-in config
    overrides = set_pit_loss_for_testing("TestTrack", 22.0)

    # 4. Optimize at lap 10
    total_race_laps = int(laps["LapNumber"].max())
    results = optimize_pit_window(
        current_lap=10,
        current_compound="SOFT",
        lap_in_stint=10,
        total_race_laps=total_race_laps,
        track_id="TestTrack",
        new_compound="MEDIUM",
        degradation_model=model,
        pit_loss_overrides=overrides,
    )
    assert not results.empty
    assert results["rank"].iloc[0] == 1

    # 5. Recommendation
    rec = recommended_pit_lap(results)
    assert rec is None or (isinstance(rec, int) and rec >= 10)

    # 6. Explanation
    ex = explain_strategy(
        results,
        "TestTrack",
        "SOFT",
        pit_loss_sec=22.0,
        degradation_rate_sec_per_lap=0.1,
        degradation_model=model,
    )
    assert "why_pit_window_opens" in ex
    assert "summary" in ex
    assert len(ex["summary"]) > 0


def test_e2e_validation_flow(fitted_degradation_model, synthetic_laps, synthetic_pit_stops):
    """Validation flow: _validate_race with synthetic laps (no load_race)."""
    from src.validation.historical_validation import _validate_race

    laps = add_stint_features(synthetic_laps, synthetic_pit_stops)
    total_race_laps = int(laps["LapNumber"].max())

    rows = _validate_race(
        2023,
        laps,
        synthetic_pit_stops,
        "TestTrack",
        total_race_laps,
        fitted_degradation_model,
    )
    assert len(rows) == 2  # two pit stops (driver 1 at lap 20, driver 2 at lap 15)
    for r in rows:
        assert "actual_pit_lap" in r
        assert "recommended_pit_lap" in r or r.get("error")
        assert "lap_delta" in r or r.get("error")
        assert "alignment_within_3" in r
