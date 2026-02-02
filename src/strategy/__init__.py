"""Strategy: pit loss, optimizer, and explanation."""

from src.strategy.optimizer import optimize_pit_window, recommended_pit_lap
from src.strategy.pit_loss import (
    DEFAULT_PIT_LOSS_SECONDS,
    TRACK_PIT_LOSS_SECONDS,
    get_pit_loss,
    set_pit_loss_for_testing,
)

__all__ = [
    "get_pit_loss",
    "DEFAULT_PIT_LOSS_SECONDS",
    "TRACK_PIT_LOSS_SECONDS",
    "set_pit_loss_for_testing",
    "optimize_pit_window",
    "recommended_pit_lap",
]
