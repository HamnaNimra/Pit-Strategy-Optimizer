"""Preprocess and normalize lap-level race data. 
Adds stint identification (from pit stops), stint IDs per driver, and lap number
within each stint. Use stint_features for fuel-load and other derived features.
"""

from __future__ import annotations

import pandas as pd


def add_stint_identification(
    laps: pd.DataFrame,
    pit_stops: pd.DataFrame,
    driver_col: str = "DriverNumber",
    lap_col: str = "LapNumber",
    pit_lap_col: str = "LapNumber",
) -> pd.DataFrame:
    """Identify stints from pit stops and add stint_id and lap_in_stint per driver.

    Stints are defined by pit-stop boundaries: stint 1 = laps up to and including
    the in-lap of the first stop; stint 2 = laps after that until the next stop; etc.
    Drivers with no pit stops get a single stint (stint_id=1, lap_in_stint = LapNumber).

    Parameters
    ----------
    laps : pd.DataFrame
        Lap-level data with at least driver_col and lap_col (e.g. DriverNumber, LapNumber).
    pit_stops : pd.DataFrame
        One row per pit stop, with driver_col and pit_lap_col (lap on which driver pitted).
    driver_col : str
        Column identifying the driver in both laps and pit_stops.
    lap_col : str
        Column for lap number in laps.
    pit_lap_col : str
        Column for lap number of the pit stop in pit_stops (the in-lap).

    Returns
    -------
    pd.DataFrame
        Copy of laps with two new columns (overwritten if present):
        - stint_id : int, 1-based stint index per driver (1 = first stint, 2 = second, ...).
        - lap_in_stint : int, 1-based lap number within that stint (1 = first lap of stint).
    """
    if laps.empty:
        out = laps.copy()
        out["stint_id"] = pd.Series(dtype="Int64")
        out["lap_in_stint"] = pd.Series(dtype="Int64")
        return out

    out = laps.copy()
    driver_key = driver_col
    lap_key = lap_col

    # Required columns in laps
    if driver_key not in out.columns or lap_key not in out.columns:
        out["stint_id"] = 1
        out["lap_in_stint"] = out[lap_key] if lap_key in out.columns else 0
        return out

    # Per-driver: ordered pit lap numbers (in-laps)
    if pit_stops.empty or driver_col not in pit_stops.columns or pit_lap_col not in pit_stops.columns:
        pit_laps_by_driver = {}
    else:
        pit_laps_by_driver = (
            pit_stops.groupby(driver_col)[pit_lap_col]
            .apply(lambda s: sorted(s.dropna().unique().tolist()))
            .to_dict()
        )

    def stint_and_lap_in_stint(row: pd.Series) -> tuple[int, int]:
        driver = row[driver_key]
        lap_num = row[lap_key]
        if pd.isna(lap_num):
            return 1, 1
        lap_num = int(lap_num)
        pit_laps = pit_laps_by_driver.get(driver, [])
        # Stint 1 = laps up to and including in-lap of first stop; stint 2 = laps after that; etc.
        # stint_id = 1 + (number of pit in-laps strictly before this lap).
        stint_id = 1 + sum(1 for p in pit_laps if p < lap_num)
        # lap_in_stint: stint 1 = lap_num; stint k = lap_num - (in-lap of (k-1)-th stop).
        if stint_id == 1:
            lap_in_stint = lap_num
        else:
            lap_in_stint = lap_num - pit_laps[stint_id - 2]
        return stint_id, max(1, lap_in_stint)

    applied = out.apply(stint_and_lap_in_stint, axis=1)
    out["stint_id"] = [t[0] for t in applied]
    out["lap_in_stint"] = [t[1] for t in applied]
    return out


def prepare_laps(
    laps: pd.DataFrame,
    pit_stops: pd.DataFrame,
    driver_col: str = "DriverNumber",
    lap_col: str = "LapNumber",
) -> pd.DataFrame:
    """Prepare lap-level data with stint identification (convenience wrapper).

    Normalizes stint boundaries from pit stops and adds:
    - stint_id : 1-based stint index per driver.
    - lap_in_stint : 1-based lap number within each stint.

    Parameters
    ----------
    laps : pd.DataFrame
        Lap-level data (e.g. from load_race RaceData.laps).
    pit_stops : pd.DataFrame
        Pit stops (e.g. from load_race RaceData.pit_stops).

    Returns
    -------
    pd.DataFrame
        Laps with stint_id and lap_in_stint added.
    """
    return add_stint_identification(laps, pit_stops, driver_col=driver_col, lap_col=lap_col)
