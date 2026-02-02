"""Shared pytest fixtures for pit strategy optimizer tests."""

import json
import os
import sys
import tempfile
from pathlib import Path

# #region agent log
_LOG_PATH = Path(__file__).resolve().parent.parent / ".cursor" / "debug.log"
_tests_dir = Path(__file__).resolve().parent
_project_root = _tests_dir.parent
try:
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "hypothesisId": "H1",
                    "location": "conftest.py:before_import",
                    "message": "sys.path and cwd",
                    "data": {
                        "sys_path": sys.path,
                        "cwd": os.getcwd(),
                        "project_root": str(_project_root),
                        "project_in_path": str(_project_root) in sys.path,
                        "tests_dir": str(_tests_dir),
                    },
                    "sessionId": "debug-session",
                    "runId": "conftest_load",
                    "timestamp": __import__("time").time() * 1000,
                }
            )
            + "\n"
        )
        f.write(
            json.dumps(
                {
                    "hypothesisId": "H2",
                    "location": "conftest.py:before_import",
                    "message": "first sys.path entry",
                    "data": {"first_path": sys.path[0] if sys.path else None},
                    "sessionId": "debug-session",
                    "runId": "conftest_load",
                    "timestamp": __import__("time").time() * 1000,
                }
            )
            + "\n"
        )
except Exception as e:
    pass
# #endregion

# Ensure project root is on sys.path so "src" is importable (pytest adds tests/ first)
_PROJECT_ROOT_FOR_PATH = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT_FOR_PATH) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT_FOR_PATH))

import pandas as pd
import pytest

from src.models.tire_degradation import TireDegradationModel

# #region agent log (post-fix verification)
try:
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "hypothesisId": "H1",
                    "location": "conftest.py:after_import",
                    "message": "post-fix",
                    "data": {
                        "project_in_path": str(_PROJECT_ROOT_FOR_PATH) in sys.path,
                        "import_ok": True,
                    },
                    "sessionId": "debug-session",
                    "runId": "post-fix",
                    "timestamp": __import__("time").time() * 1000,
                }
            )
            + "\n"
        )
except Exception:
    pass
# #endregion

# Use a temp dir under the project so sandbox/CI can write (system temp may be restricted)
_TESTS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TESTS_DIR.parent


@pytest.fixture
def synthetic_laps():
    """Minimal laps DataFrame with Compound, LapNumber, lap_in_stint, estimated_fuel_kg, LapTime (timedelta)."""
    n = 60
    lap_times_sec = [90.0 + 0.1 * (i % 30) for i in range(n)]
    return pd.DataFrame(
        {
            "DriverNumber": ["1"] * 30 + ["2"] * 30,
            "LapNumber": list(range(1, 31)) + list(range(1, 31)),
            "Compound": ["SOFT"] * 20
            + ["MEDIUM"] * 10
            + ["SOFT"] * 15
            + ["MEDIUM"] * 15,
            "lap_in_stint": list(range(1, 21))
            + list(range(1, 11))
            + list(range(1, 16))
            + list(range(1, 16)),
            "estimated_fuel_kg": [110.0 - (i - 1) * 1.8 for i in range(1, 31)]
            + [110.0 - (i - 1) * 1.8 for i in range(1, 31)],
            "LapTime": pd.to_timedelta(lap_times_sec, unit="s"),
        }
    )


@pytest.fixture
def synthetic_pit_stops():
    """Pit stops: driver 1 pits at lap 20, driver 2 at lap 15."""
    return pd.DataFrame(
        {
            "DriverNumber": ["1", "2"],
            "LapNumber": [20, 15],
            "Compound": ["MEDIUM", "MEDIUM"],
        }
    )


@pytest.fixture
def fitted_degradation_model(synthetic_laps):
    """TireDegradationModel fitted for TestTrack with SOFT and MEDIUM from synthetic_laps."""
    model = TireDegradationModel()
    laps = synthetic_laps.copy()
    soft = laps[laps["Compound"] == "SOFT"].head(15)
    medium = laps[laps["Compound"] == "MEDIUM"].head(15)
    model.fit(
        soft,
        "TestTrack",
        "SOFT",
        lap_time_col="LapTime",
        lap_in_stint_col="lap_in_stint",
        fuel_col="estimated_fuel_kg",
    )
    model.fit(
        medium,
        "TestTrack",
        "MEDIUM",
        lap_time_col="LapTime",
        lap_in_stint_col="lap_in_stint",
        fuel_col="estimated_fuel_kg",
    )
    return model


@pytest.fixture
def temp_models_dir():
    """Temporary directory for save/load tests (under project so sandbox can write)."""
    import shutil

    d = tempfile.mkdtemp(dir=str(_PROJECT_ROOT), prefix=".tmp_models_")
    try:
        yield Path(d)
    finally:
        shutil.rmtree(d, ignore_errors=True)
