"""Load race sessions via FastF1; extract lap times, compounds, pit stops, weather; cache dry races only.

- Data sources: FastF1 (lap times, sector times, tire compounds/stint, pit timing, weather).
- Pipeline: load race on demand, extract/normalize into structured datasets, cache locally.
- Scope: dry races only (slick compounds).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from src.utils.config import FASTF1_CACHE_DIR, PROCESSED_RACES_DIR


class RaceData(NamedTuple):
    """Clean race data: lap times, compounds, pit stops, and weather (dry races only)."""

    laps: pd.DataFrame
    pit_stops: pd.DataFrame
    weather: pd.DataFrame


def _sanitize_race_name(name: str) -> str:
    """Sanitize race/location name for cache directory and filenames."""
    s = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"[-\s]+", "_", s).strip("_") or "race"


def _cache_dir_for_race(year: int, race_name: str) -> Path:
    """Path to the cache subdirectory for a given year and race."""
    key = f"{year}_{_sanitize_race_name(race_name)}"
    return PROCESSED_RACES_DIR / key


def _is_dry_race(weather_df: pd.DataFrame) -> bool:
    """Return True if the session had no rainfall (dry race)."""
    if weather_df is None or weather_df.empty:
        return True
    if "Rainfall" not in weather_df.columns:
        return True
    return not weather_df["Rainfall"].fillna(False).astype(bool).any()


def _extract_laps(session) -> pd.DataFrame:
    """Extract a clean laps DataFrame from a FastF1 session."""
    raw = session.laps
    if raw is None or len(raw) == 0:
        return pd.DataFrame()

    cols = [
        "Time",
        "Driver",
        "DriverNumber",
        "LapTime",
        "LapNumber",
        "Stint",
        "Compound",
        "TyreLife",
        "FreshTyre",
        "Team",
        "PitInTime",
        "PitOutTime",
        "Sector1Time",
        "Sector2Time",
        "Sector3Time",
        "Position",
        "TrackStatus",
        "LapStartTime",
        "LapStartDate",
    ]
    available = [c for c in cols if c in raw.columns]
    out = raw[available].copy()
    return pd.DataFrame(out)


def _extract_pit_stops(session) -> pd.DataFrame:
    """Extract pit stops from session laps (laps where driver entered the pit)."""
    raw = session.laps
    if raw is None or len(raw) == 0:
        return pd.DataFrame()

    if "PitInTime" not in raw.columns:
        return pd.DataFrame()

    pit = raw[raw["PitInTime"].notna()].copy()
    if pit.empty:
        return pd.DataFrame(
            columns=[
                "DriverNumber",
                "Driver",
                "LapNumber",
                "PitInTime",
                "PitOutTime",
                "Compound",
                "TyreLife",
                "Stint",
                "Team",
            ]
        )

    cols = [
        "DriverNumber",
        "Driver",
        "LapNumber",
        "PitInTime",
        "PitOutTime",
        "Compound",
        "TyreLife",
        "Stint",
        "Team",
    ]
    available = [c for c in cols if c in pit.columns]
    out = pit[available].copy()
    if "PitInTime" in out.columns and "PitOutTime" in out.columns:
        out["PitDuration"] = out["PitOutTime"] - out["PitInTime"]
    return pd.DataFrame(out)


def _extract_weather(session) -> pd.DataFrame:
    """Extract weather DataFrame from session."""
    raw = getattr(session, "weather_data", None)
    if raw is None or (hasattr(raw, "empty") and raw.empty):
        return pd.DataFrame()
    return pd.DataFrame(raw.copy())


def load_race(
    year: int,
    race_name: str,
    cache_dir: Path | None = None,
    use_cache: bool = True,
) -> RaceData:
    """
    Load a race session by year and race name; return clean DataFrames.

    Only dry races are supported. Wet sessions (any Rainfall in weather data)
    raise ValueError.

    Parameters
    ----------
    year : int
        Season year (e.g. 2023).
    race_name : str
        Event name or location (e.g. "Bahrain", "Monaco", "French Grand Prix").
    cache_dir : Path, optional
        Override directory for processed race cache. Default uses config.
    use_cache : bool, default True
        If True, read/write processed DataFrames from/to local cache to avoid
        repeated FastF1 API calls.

    Returns
    -------
    RaceData
        NamedTuple with:
        - laps : lap times, compounds, stint, sector times, pit in/out, etc.
        - pit_stops : one row per pit stop (lap, driver, compound, duration, etc.)
        - weather : session weather (AirTemp, TrackTemp, Rainfall, etc.)

    Raises
    ------
    ValueError
        If the session was run in wet conditions (Rainfall reported).
    """
    import fastf1

    processed_base = cache_dir if cache_dir is not None else PROCESSED_RACES_DIR
    race_cache_dir = processed_base / f"{year}_{_sanitize_race_name(race_name)}"

    # Try cache first
    if use_cache:
        laps_path = race_cache_dir / "laps.parquet"
        pit_path = race_cache_dir / "pit_stops.parquet"
        weather_path = race_cache_dir / "weather.parquet"
        if laps_path.exists() and pit_path.exists() and weather_path.exists():
            laps = pd.read_parquet(laps_path)
            pit_stops = pd.read_parquet(pit_path)
            weather = pd.read_parquet(weather_path)
            return RaceData(laps=laps, pit_stops=pit_stops, weather=weather)

    # Ensure FastF1 and our cache dirs exist
    FASTF1_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        fastf1.Cache.enable_cache(str(FASTF1_CACHE_DIR))
    except Exception:
        pass
    race_cache_dir.mkdir(parents=True, exist_ok=True)

    # Load session from API
    session = fastf1.get_session(year, race_name, "R")
    session.load(laps=True, weather=True, telemetry=False, messages=False)

    weather_df = _extract_weather(session)
    if not _is_dry_race(weather_df):
        raise ValueError(
            "Wet race: session has Rainfall in weather data. Only dry races are supported."
        )

    laps_df = _extract_laps(session)
    pit_stops_df = _extract_pit_stops(session)

    # Write cache
    if use_cache:
        laps_df.to_parquet(race_cache_dir / "laps.parquet", index=False)
        pit_stops_df.to_parquet(race_cache_dir / "pit_stops.parquet", index=False)
        weather_df.to_parquet(race_cache_dir / "weather.parquet", index=False)

    return RaceData(laps=laps_df, pit_stops=pit_stops_df, weather=weather_df)
