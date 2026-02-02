"""Diagnostic utilities for the tire degradation model.

Analyzes model behavior only: degradation rate (s/lap), simple cliff detection via
slope changes, and reproducible degradation curve outputs. No strategy logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from src.models.tire_degradation import TireDegradationModel

# Default range for curve and cliff detection (lap-in-stint)
DEFAULT_LAP_IN_STINT_MIN = 1
DEFAULT_LAP_IN_STINT_MAX = 50

# Cliff detection: flag lap where slope (s/lap) increases by more than this (seconds per lap)
DEFAULT_CLIFF_SLOPE_CHANGE_THRESHOLD = 0.05


def degradation_rate_seconds_per_lap(
    track_id: str,
    compound: str,
    model: TireDegradationModel | None = None,
) -> float:
    """
    Return the degradation rate (seconds per lap) from the linear model coefficients.

    The coefficient for lap_in_stint is the rate at which predicted lap time
    increases per additional lap in stint (tire aging). Positive value =
    lap time gets slower (worse) as stint progresses.

    Parameters
    ----------
    track_id : str
        Track identifier (must match a fitted model).
    compound : str
        Tire compound (SOFT, MEDIUM, HARD).
    model : TireDegradationModel, optional
        Fitted model; default is the module default from tire_degradation.

    Returns
    -------
    float
        Degradation rate in seconds per lap (positive = slower laps over stint).
    """
    from src.models.tire_degradation import get_degradation_model

    if model is None:
        model = get_degradation_model()
    coefs = model.get_coefficients(track_id, compound)
    # lap_in_stint coefficient is seconds per lap
    return float(coefs.get("lap_in_stint", 0.0))


def degradation_curve(
    track_id: str,
    compound: str,
    fuel_kg: float,
    *,
    track_temp: float | None = None,
    lap_in_stint_min: int = DEFAULT_LAP_IN_STINT_MIN,
    lap_in_stint_max: int = DEFAULT_LAP_IN_STINT_MAX,
    model: TireDegradationModel | None = None,
) -> pd.DataFrame:
    """
    Reproducible degradation curve: predicted lap time (seconds) vs lap-in-stint.

    Same inputs (track_id, compound, fuel_kg, track_temp, range) and same fitted
    model produce the same DataFrame. No randomness.

    Parameters
    ----------
    track_id : str
        Track identifier.
    compound : str
        Tire compound (SOFT, MEDIUM, HARD).
    fuel_kg : float
        Fuel mass (kg) used for all laps in the curve (constant for simplicity).
    track_temp : float, optional
        Track temperature if the model was fitted with it.
    lap_in_stint_min : int
        First lap-in-stint value (inclusive).
    lap_in_stint_max : int
        Last lap-in-stint value (inclusive).
    model : TireDegradationModel, optional
        Fitted model; default is the module default.

    Returns
    -------
    pd.DataFrame
        Columns: lap_in_stint (int), predicted_lap_time_sec (float).
        One row per lap from lap_in_stint_min to lap_in_stint_max.
    """
    from src.models.tire_degradation import get_degradation_model

    if model is None:
        model = get_degradation_model()

    laps = np.arange(lap_in_stint_min, lap_in_stint_max + 1, dtype=float)
    times = np.array(
        [
            model.predict_lap_time(track_id, compound, lap, fuel_kg, track_temp)
            for lap in laps
        ]
    )
    return pd.DataFrame(
        {
            "lap_in_stint": laps.astype(int),
            "predicted_lap_time_sec": times,
        }
    )


def detect_cliffs(
    track_id: str,
    compound: str,
    fuel_kg: float,
    *,
    track_temp: float | None = None,
    lap_in_stint_min: int = DEFAULT_LAP_IN_STINT_MIN,
    lap_in_stint_max: int = DEFAULT_LAP_IN_STINT_MAX,
    slope_change_threshold: float = DEFAULT_CLIFF_SLOPE_CHANGE_THRESHOLD,
    model: TireDegradationModel | None = None,
) -> pd.DataFrame:
    """
    Simple cliff detection using slope changes on the degradation curve.

    Computes predicted lap time vs lap-in-stint, then first difference (slope =
    seconds per lap) and second difference (change in slope). A "cliff" candidate
    is a lap where the slope increases by more than slope_change_threshold
    (degradation suddenly worsens). For a linear model the slope is constant so
    no cliffs are typically detected; this supports future non-linear models.

    Parameters
    ----------
    track_id : str
        Track identifier.
    compound : str
        Tire compound (SOFT, MEDIUM, HARD).
    fuel_kg : float
        Fuel mass (kg) for the curve.
    track_temp : float, optional
        Track temperature if the model was fitted with it.
    lap_in_stint_min, lap_in_stint_max : int
        Lap-in-stint range for the curve.
    slope_change_threshold : float
        Minimum increase in slope (s/lap) to flag as cliff candidate.
    model : TireDegradationModel, optional
        Fitted model; default is the module default.

    Returns
    -------
    pd.DataFrame
        Columns: lap_in_stint, slope_sec_per_lap (first difference),
        slope_change (second difference), is_cliff_candidate (bool).
        One row per lap; first lap has NaN slope; first two laps have NaN slope_change.
    """
    curve = degradation_curve(
        track_id,
        compound,
        fuel_kg,
        track_temp=track_temp,
        lap_in_stint_min=lap_in_stint_min,
        lap_in_stint_max=lap_in_stint_max,
        model=model,
    )
    t = curve["predicted_lap_time_sec"].values
    lap = curve["lap_in_stint"].values

    # First difference: slope (s/lap) from previous lap to this lap
    slope = np.full_like(t, np.nan, dtype=float)
    slope[1:] = np.diff(t)

    # Second difference: change in slope (acceleration of degradation)
    slope_change = np.full_like(t, np.nan, dtype=float)
    slope_change[2:] = np.diff(slope[1:])

    # Cliff = lap where slope increases by more than threshold (degradation worsens)
    is_cliff = np.zeros(len(t), dtype=bool)
    is_cliff[2:] = slope_change[2:] >= slope_change_threshold

    return pd.DataFrame(
        {
            "lap_in_stint": lap,
            "slope_sec_per_lap": slope,
            "slope_change": slope_change,
            "is_cliff_candidate": is_cliff,
        }
    )


def cliff_laps(
    track_id: str,
    compound: str,
    fuel_kg: float,
    *,
    track_temp: float | None = None,
    lap_in_stint_min: int = DEFAULT_LAP_IN_STINT_MIN,
    lap_in_stint_max: int = DEFAULT_LAP_IN_STINT_MAX,
    slope_change_threshold: float = DEFAULT_CLIFF_SLOPE_CHANGE_THRESHOLD,
    model: TireDegradationModel | None = None,
) -> list[int]:
    """
    Return list of lap-in-stint values flagged as cliff candidates.

    Convenience wrapper around detect_cliffs; returns only the lap numbers
    where is_cliff_candidate is True. Reproducible for fixed inputs.
    """
    df = detect_cliffs(
        track_id,
        compound,
        fuel_kg,
        track_temp=track_temp,
        lap_in_stint_min=lap_in_stint_min,
        lap_in_stint_max=lap_in_stint_max,
        slope_change_threshold=slope_change_threshold,
        model=model,
    )
    return df.loc[df["is_cliff_candidate"], "lap_in_stint"].astype(int).tolist()
