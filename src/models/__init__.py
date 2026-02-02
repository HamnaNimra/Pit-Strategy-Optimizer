"""Models: tire degradation and diagnostics."""

from src.models.diagnostics import (
    cliff_laps,
    degradation_curve,
    degradation_rate_seconds_per_lap,
    detect_cliffs,
)
from src.models.tire_degradation import (
    TireDegradationModel,
    get_degradation_model,
    predict_lap_time,
)

__all__ = [
    "TireDegradationModel",
    "get_degradation_model",
    "predict_lap_time",
    "degradation_rate_seconds_per_lap",
    "degradation_curve",
    "detect_cliffs",
    "cliff_laps",
]
