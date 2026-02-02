"""Unit tests for data pipeline (preprocess + stint_features; no load_race to avoid network)."""

import pandas as pd
import pytest

from src.data_pipeline import add_stint_features, prepare_laps


def test_add_stint_identification_via_prepare_laps():
    """prepare_laps adds stint_id and lap_in_stint from pit stops."""
    laps = pd.DataFrame({
        "DriverNumber": ["1", "1", "1", "1"],
        "LapNumber": [1, 2, 3, 4],
    })
    pit_stops = pd.DataFrame({"DriverNumber": ["1"], "LapNumber": [2]})
    out = prepare_laps(laps, pit_stops)
    assert list(out["stint_id"]) == [1, 1, 2, 2]
    assert list(out["lap_in_stint"]) == [1, 2, 1, 2]


def test_add_stint_features_adds_all_derived():
    """add_stint_features adds stint_id, lap_in_stint, estimated_fuel_kg."""
    laps = pd.DataFrame({
        "DriverNumber": ["1", "1", "1"],
        "LapNumber": [1, 2, 3],
        "Compound": ["SOFT", "SOFT", "SOFT"],
    })
    pit_stops = pd.DataFrame(columns=["DriverNumber", "LapNumber"])
    out = add_stint_features(laps, pit_stops)
    assert "stint_id" in out.columns
    assert "lap_in_stint" in out.columns
    assert "estimated_fuel_kg" in out.columns
    assert out["estimated_fuel_kg"].iloc[0] == 110.0
    assert out["estimated_fuel_kg"].iloc[1] == 110.0 - 1.8
