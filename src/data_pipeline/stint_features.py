"""Derived stint and lap-level features for strategy modeling.

Adds estimated fuel load (linear decay from lap number) and documents all derived
fields for use by the degradation model and optimizer.
"""

from __future__ import annotations

import pandas as pd

# Default fuel model (PRD §13: fuel load estimated with simplified linear model)
# Typical F1: ~110 kg at start, ~1.5–2 kg/lap depending on track
DEFAULT_INITIAL_FUEL_KG = 110.0
DEFAULT_FUEL_PER_LAP_KG = 1.8
DEFAULT_MIN_FUEL_KG = 0.0


def add_fuel_load_estimate(
    laps: pd.DataFrame,
    lap_col: str = "LapNumber",
    initial_fuel_kg: float = DEFAULT_INITIAL_FUEL_KG,
    fuel_per_lap_kg: float = DEFAULT_FUEL_PER_LAP_KG,
    min_fuel_kg: float = DEFAULT_MIN_FUEL_KG,
) -> pd.DataFrame:
    """Add estimated fuel remaining (kg) using a simple linear decay model.

    Assumes fuel at start of lap 1 = initial_fuel_kg and constant consumption
    per lap. Fuel at start of lap N = initial_fuel_kg - (N - 1) * fuel_per_lap_kg,
    clamped to min_fuel_kg. No refuelling (F1 2010+); pit stops do not add fuel.

    Derived column
    --------------
    estimated_fuel_kg : float
        Estimated fuel mass (kg) at the start of this lap. Used by degradation
        and strategy models to normalize lap time (lighter car = faster laps).
    """
    if laps.empty:
        out = laps.copy()
        out["estimated_fuel_kg"] = pd.Series(dtype=float)
        return out

    out = laps.copy()
    if lap_col not in out.columns:
        out["estimated_fuel_kg"] = initial_fuel_kg
        return out

    lap_num = out[lap_col].astype("Int64")
    # Fuel at start of lap N: consumed (N-1) laps worth
    fuel = initial_fuel_kg - (lap_num - 1).astype(float) * fuel_per_lap_kg
    out["estimated_fuel_kg"] = fuel.clip(lower=min_fuel_kg)
    return out


def add_stint_features(
    laps: pd.DataFrame,
    pit_stops: pd.DataFrame,
    initial_fuel_kg: float = DEFAULT_INITIAL_FUEL_KG,
    fuel_per_lap_kg: float = DEFAULT_FUEL_PER_LAP_KG,
    lap_col: str = "LapNumber",
    driver_col: str = "DriverNumber",
) -> pd.DataFrame:
    """Add stint identification and fuel estimate to lap-level data.

    Applies preprocessing (stint_id, lap_in_stint from pit stops) and fuel
    estimate (linear decay). Use after load_race; laps are expected to have
    LapNumber and DriverNumber; pit_stops to have LapNumber and DriverNumber.

    Derived columns added
    ---------------------
    stint_id : int
        1-based stint index per driver (1 = first stint, 2 = second after one pit, ...).
    lap_in_stint : int
        1-based lap number within that stint (1 = first lap on this tyre set).
    estimated_fuel_kg : float
        Estimated fuel mass (kg) at start of lap (linear decay from lap 1).
    """
    from src.data_pipeline.preprocess import add_stint_identification

    laps_with_stint = add_stint_identification(
        laps, pit_stops, lap_col=lap_col, driver_col=driver_col
    )
    laps_with_fuel = add_fuel_load_estimate(
        laps_with_stint,
        lap_col=lap_col,
        initial_fuel_kg=initial_fuel_kg,
        fuel_per_lap_kg=fuel_per_lap_kg,
    )
    return laps_with_fuel
