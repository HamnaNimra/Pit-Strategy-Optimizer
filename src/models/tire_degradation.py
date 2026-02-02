"""Linear tire degradation model per track and compound.

Separate linear regression per (track_id, compound). Inputs: lap-in-stint, fuel load,
optional track temperature. Output: predicted lap time (seconds). Models are persisted
to disk for reuse. Explainability: plain linear coefficients.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.utils.config import DEGRADATION_MODELS_DIR, SLICK_COMPOUNDS

# Feature names used at fit/predict (order must match)
FEATURE_LAP_IN_STINT = "lap_in_stint"
FEATURE_FUEL_KG = "estimated_fuel_kg"
FEATURE_TRACK_TEMP = "track_temp"

DEFAULT_LAP_TIME_COL = "LapTime"
DEFAULT_LAP_IN_STINT_COL = "lap_in_stint"
DEFAULT_FUEL_COL = "estimated_fuel_kg"
DEFAULT_TRACK_TEMP_COL = "track_temp"


def _lap_time_to_seconds(series: pd.Series) -> pd.Series:
    """Convert lap time column to seconds (handles pd.Timedelta or numeric)."""
    if pd.api.types.is_timedelta64_dtype(series):
        return series.dt.total_seconds()
    return pd.to_numeric(series, errors="coerce")


class TireDegradationModel:
    """
    Linear lap-time model per track and compound.

    One scikit-learn LinearRegression per (track_id, compound). Features:
    lap_in_stint, estimated_fuel_kg, and optionally track_temp. Target: lap time
    in seconds. Focus on explainability: coefficients are degradation (s/lap),
    fuel effect (s/kg), and optional temperature effect.
    """

    def __init__(self) -> None:
        # (track_id, compound) -> {"model": LinearRegression, "feature_names": list[str]}
        self._models: dict[tuple[str, str], dict[str, Any]] = {}

    def fit(
        self,
        laps: pd.DataFrame,
        track_id: str,
        compound: str,
        *,
        lap_time_col: str = DEFAULT_LAP_TIME_COL,
        lap_in_stint_col: str = DEFAULT_LAP_IN_STINT_COL,
        fuel_col: str = DEFAULT_FUEL_COL,
        track_temp_col: str | None = DEFAULT_TRACK_TEMP_COL,
    ) -> None:
        """
        Fit a linear degradation model for the given track and compound.

        Uses lap_in_stint, fuel load, and (if column present) track temperature
        to predict lap time. Only rows with valid numeric values are used.
        Compound is normalized to uppercase and must be in SLICK_COMPOUNDS.

        Parameters
        ----------
        laps : pd.DataFrame
            Lap-level data including the target and feature columns.
        track_id : str
            Identifier for the track (e.g. "Bahrain", "Monaco").
        compound : str
            Tire compound: SOFT, MEDIUM, or HARD.
        lap_time_col : str
            Column name for lap time (Timedelta or numeric seconds).
        lap_in_stint_col : str
            Column name for lap number within stint.
        fuel_col : str
            Column name for estimated fuel mass (kg).
        track_temp_col : str, optional
            Column name for track temperature; if None or missing, temperature
            is not used as a feature.
        """
        compound = compound.strip().upper()
        if compound not in SLICK_COMPOUNDS:
            raise ValueError(
                f"Compound must be one of {sorted(SLICK_COMPOUNDS)}, got {compound!r}"
            )

        if laps.empty or lap_time_col not in laps.columns:
            raise ValueError("laps must be non-empty and contain lap time column")

        # Filter to this compound
        compound_col = "Compound"
        if compound_col in laps.columns:
            subset = laps[laps[compound_col].str.upper().str.strip() == compound].copy()
        else:
            subset = laps.copy()

        if subset.empty:
            raise ValueError(
                f"No laps found for compound {compound} at track {track_id}"
            )

        # Build feature matrix (order defines predict interface)
        feature_names: list[str] = [FEATURE_LAP_IN_STINT, FEATURE_FUEL_KG]
        X_list: list[pd.Series] = [
            pd.to_numeric(subset[lap_in_stint_col], errors="coerce"),
            pd.to_numeric(subset[fuel_col], errors="coerce"),
        ]
        if track_temp_col and track_temp_col in subset.columns:
            feature_names.append(FEATURE_TRACK_TEMP)
            X_list.append(pd.to_numeric(subset[track_temp_col], errors="coerce"))

        X = pd.concat(X_list, axis=1)
        X.columns = feature_names
        y = _lap_time_to_seconds(subset[lap_time_col])

        # Drop rows with any NaN in X or y
        mask = X.notna().all(axis=1) & y.notna()
        X = X.loc[mask]
        y = y.loc[mask]
        if len(X) < 2:
            raise ValueError(
                f"Too few valid rows for {track_id} / {compound} (need at least 2)"
            )

        reg = LinearRegression()
        reg.fit(X.values, y.values)

        key = (str(track_id), compound)
        self._models[key] = {"model": reg, "feature_names": feature_names}

    def predict_lap_time(
        self,
        track_id: str,
        compound: str,
        lap_in_stint: float | int,
        fuel_kg: float,
        track_temp: float | None = None,
    ) -> float:
        """
        Predict lap time (seconds) for the given track, compound, and inputs.

        The model for (track_id, compound) must have been fitted previously.
        If that model was fitted with track temperature, pass track_temp;
        otherwise it is ignored.

        Parameters
        ----------
        track_id : str
            Track identifier (must match fit).
        compound : str
            Tire compound: SOFT, MEDIUM, or HARD.
        lap_in_stint : float or int
            Lap number within the stint (1 = first lap on this tyre set).
        fuel_kg : float
            Estimated fuel mass (kg) at start of lap.
        track_temp : float, optional
            Track temperature (e.g. °C). Used only if the model was fitted with it.

        Returns
        -------
        float
            Predicted lap time in seconds.
        """
        compound = compound.strip().upper()
        key = (str(track_id), compound)
        if key not in self._models:
            raise ValueError(
                f"No fitted model for track={track_id!r} compound={compound!r}. "
                "Call fit() first or load models from disk."
            )

        entry = self._models[key]
        model: LinearRegression = entry["model"]
        feature_names: list[str] = entry["feature_names"]

        # Build feature vector in same order as fit
        row: list[float] = [float(lap_in_stint), float(fuel_kg)]
        if FEATURE_TRACK_TEMP in feature_names:
            row.append(float(track_temp) if track_temp is not None else np.nan)
        X = np.array([row])
        return float(model.predict(X)[0])

    def get_coefficients(self, track_id: str, compound: str) -> dict[str, float]:
        """
        Return intercept and feature coefficients for the fitted model (explainability).

        Keys: 'intercept', then one per feature (e.g. 'lap_in_stint', 'estimated_fuel_kg',
        'track_temp'). Coefficients are in seconds per unit of the feature.
        """
        compound = compound.strip().upper()
        key = (str(track_id), compound)
        if key not in self._models:
            raise ValueError(
                f"No fitted model for track={track_id!r} compound={compound!r}"
            )

        entry = self._models[key]
        model: LinearRegression = entry["model"]
        feature_names: list[str] = entry["feature_names"]

        out: dict[str, float] = {"intercept": float(model.intercept_)}
        for i, name in enumerate(feature_names):
            out[name] = float(model.coef_[i])
        return out

    def save(self, path: Path | str | None = None) -> Path:
        """
        Persist all fitted models to disk. Uses joblib.

        Parameters
        ----------
        path : Path or str, optional
            Directory to write to. Default: config DEGRADATION_MODELS_DIR.

        Returns
        -------
        Path
            Directory into which models were written.
        """
        try:
            import joblib
        except ImportError:
            raise ImportError(
                "Persisting models requires joblib; install with: pip install joblib"
            )

        dest = Path(path) if path is not None else DEGRADATION_MODELS_DIR
        dest.mkdir(parents=True, exist_ok=True)

        payload = {
            "version": 1,
            "models": {
                f"{t}_{c}": {"model": e["model"], "feature_names": e["feature_names"]}
                for (t, c), e in self._models.items()
            },
        }
        joblib.dump(payload, dest / "degradation_models.joblib")
        return dest

    def load(self, path: Path | str | None = None) -> Path:
        """
        Load fitted models from disk. Replaces any currently held models.

        Parameters
        ----------
        path : Path or str, optional
            Directory containing degradation_models.joblib. Default: config DEGRADATION_MODELS_DIR.

        Returns
        -------
        Path
            Directory from which models were loaded.
        """
        try:
            import joblib
        except ImportError as exc:
            raise ImportError(
                "Loading models requires joblib; install with: pip install joblib"
            ) from exc

        dest = Path(path) if path is not None else DEGRADATION_MODELS_DIR
        filepath = dest / "degradation_models.joblib"
        if not filepath.exists():
            raise FileNotFoundError(f"No saved models at {filepath}")

        payload = joblib.load(filepath)
        models_raw = payload.get("models", payload)
        self._models = {}
        for k, v in models_raw.items():
            if "_" not in k:
                continue
            parts = k.rsplit("_", 1)
            if len(parts) != 2:
                continue
            track_id, compound = parts[0], parts[1]
            self._models[(track_id, compound)] = {
                "model": v["model"],
                "feature_names": v["feature_names"],
            }
        return dest

    def list_fitted(self) -> list[tuple[str, str]]:
        """Return list of (track_id, compound) pairs that have been fitted or loaded."""
        return sorted(self._models.keys())


# Module-level singleton for convenience; callers can also instantiate TireDegradationModel()
_default_store: TireDegradationModel | None = None


def get_degradation_model() -> TireDegradationModel:
    """Return the default TireDegradationModel instance (lazy singleton)."""
    global _default_store
    if _default_store is None:
        _default_store = TireDegradationModel()
    return _default_store


def predict_lap_time(
    track_id: str,
    compound: str,
    lap_in_stint: float | int,
    fuel_kg: float,
    track_temp: float | None = None,
    *,
    model: TireDegradationModel | None = None,
) -> float:
    """
    Predict lap time (seconds) using the linear degradation model.

    Uses the default TireDegradationModel unless model= is provided.
    The model for (track_id, compound) must already be fitted or loaded.

    Parameters
    ----------
    track_id : str
        Track identifier.
    compound : str
        Tire compound (SOFT, MEDIUM, HARD).
    lap_in_stint : float or int
        Lap number within stint.
    fuel_kg : float
        Estimated fuel mass (kg).
    track_temp : float, optional
        Track temperature if the model was fitted with it.
    model : TireDegradationModel, optional
        Model instance to use; default is the module singleton.

    Returns
    -------
    float
        Predicted lap time in seconds.
    """
    if model is None:
        model = get_degradation_model()
    return model.predict_lap_time(track_id, compound, lap_in_stint, fuel_kg, track_temp)
