"""Unit tests for stint_features (add_fuel_load_estimate, add_stint_features)."""

import pandas as pd
import pytest

from src.data_pipeline.stint_features import (
    add_fuel_load_estimate,
    add_stint_features,
    DEFAULT_INITIAL_FUEL_KG,
    DEFAULT_FUEL_PER_LAP_KG,
)


def test_add_fuel_load_estimate_empty():
    """Empty laps returns empty with estimated_fuel_kg column."""
    out = add_fuel_load_estimate(pd.DataFrame())
    assert out.empty
    assert "estimated_fuel_kg" in out.columns


def test_add_fuel_load_estimate_linear_decay():
    """Fuel decreases by fuel_per_lap_kg per lap from initial."""
    laps = pd.DataFrame({"LapNumber": [1, 2, 3]})
    out = add_fuel_load_estimate(laps, initial_fuel_kg=100.0, fuel_per_lap_kg=2.0)
    assert list(out["estimated_fuel_kg"]) == [100.0, 98.0, 96.0]


def test_add_fuel_load_estimate_clips_min():
    """Fuel is clipped to min_fuel_kg."""
    laps = pd.DataFrame({"LapNumber": [1, 50]})
    out = add_fuel_load_estimate(laps, initial_fuel_kg=10.0, fuel_per_lap_kg=1.0, min_fuel_kg=2.0)
    assert out["estimated_fuel_kg"].iloc[1] == 2.0


def test_add_stint_features_adds_stint_and_fuel():
    """add_stint_features adds stint_id, lap_in_stint, estimated_fuel_kg."""
    laps = pd.DataFrame({
        "DriverNumber": ["1", "1"],
        "LapNumber": [1, 2],
        "Compound": ["SOFT", "SOFT"],
    })
    pit_stops = pd.DataFrame(columns=["DriverNumber", "LapNumber"])
    out = add_stint_features(laps, pit_stops)
    assert "stint_id" in out.columns
    assert "lap_in_stint" in out.columns
    assert "estimated_fuel_kg" in out.columns
