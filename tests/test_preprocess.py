"""Unit tests for preprocess (add_stint_identification, prepare_laps)."""

import pandas as pd
import pytest

from src.data_pipeline.preprocess import add_stint_identification, prepare_laps


def test_add_stint_identification_empty_laps():
    """Empty laps returns empty with stint columns."""
    out = add_stint_identification(pd.DataFrame(), pd.DataFrame())
    assert out.empty
    assert "stint_id" in out.columns
    assert "lap_in_stint" in out.columns


def test_add_stint_identification_no_pits_single_stint():
    """Driver with no pit stops gets stint_id=1, lap_in_stint=LapNumber."""
    laps = pd.DataFrame({"DriverNumber": ["1", "1", "1"], "LapNumber": [1, 2, 3]})
    pit_stops = pd.DataFrame(columns=["DriverNumber", "LapNumber"])
    out = add_stint_identification(laps, pit_stops)
    assert list(out["stint_id"]) == [1, 1, 1]
    assert list(out["lap_in_stint"]) == [1, 2, 3]


def test_add_stint_identification_one_pit():
    """Driver with one pit at lap 2: stint 1 = laps 1-2, stint 2 = lap 3+."""
    laps = pd.DataFrame({
        "DriverNumber": ["1", "1", "1", "1"],
        "LapNumber": [1, 2, 3, 4],
    })
    pit_stops = pd.DataFrame({"DriverNumber": ["1"], "LapNumber": [2]})
    out = add_stint_identification(laps, pit_stops)
    assert list(out["stint_id"]) == [1, 1, 2, 2]
    assert list(out["lap_in_stint"]) == [1, 2, 1, 2]


def test_prepare_laps_wrapper():
    """prepare_laps adds stint_id and lap_in_stint."""
    laps = pd.DataFrame({"DriverNumber": ["1"], "LapNumber": [1]})
    pit_stops = pd.DataFrame(columns=["DriverNumber", "LapNumber"])
    out = prepare_laps(laps, pit_stops)
    assert "stint_id" in out.columns
    assert "lap_in_stint" in out.columns
    assert out["stint_id"].iloc[0] == 1
    assert out["lap_in_stint"].iloc[0] == 1
