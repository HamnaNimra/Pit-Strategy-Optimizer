"""Strategy: pit loss, optimizer, and explanation."""

from src.strategy.explanation import (
    explain_cost_of_advancing,
    explain_cost_of_delaying,
    explain_strategy,
    explain_when_degradation_overtakes,
    explain_why_pit_window_opens,
)
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
    "explain_why_pit_window_opens",
    "explain_when_degradation_overtakes",
    "explain_cost_of_delaying",
    "explain_cost_of_advancing",
    "explain_strategy",
]
