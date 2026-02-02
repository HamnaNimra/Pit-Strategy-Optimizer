"""Parameter sensitivity analysis: small changes, big impact.

Example: "If pit loss ±2 s, recommended pit lap changes by X."
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.strategy.optimizer import optimize_pit_window, recommended_pit_lap
from src.strategy.pit_loss import get_pit_loss, set_pit_loss_for_testing

if TYPE_CHECKING:
    from src.models.tire_degradation import TireDegradationModel


def sensitivity_pit_loss(
    current_lap: int,
    current_compound: str,
    lap_in_stint: int,
    total_race_laps: int,
    track_id: str,
    new_compound: str,
    *,
    pit_loss_delta_sec: float = 2.0,
    degradation_model: TireDegradationModel | None = None,
    pit_window_size: int = 10,
    initial_fuel_kg: float = 110.0,
    fuel_per_lap_kg: float = 1.8,
) -> dict:
    """
    Run optimizer with base pit loss and with pit loss ± delta; report how
    recommended pit lap changes. Human-readable summary for portfolio display.

    Parameters
    ----------
    current_lap, current_compound, lap_in_stint, total_race_laps, track_id, new_compound
        Same as optimize_pit_window.
    pit_loss_delta_sec : float
        Delta in seconds (e.g. 2.0 for ±2 s).
    degradation_model, pit_window_size, initial_fuel_kg, fuel_per_lap_kg
        Passed to optimize_pit_window.

    Returns
    -------
    dict
        base_pit_loss_sec, base_rec_lap, plus_delta_rec_lap, minus_delta_rec_lap,
        message (human-readable), e.g. "If pit loss ±2.0 s, recommended pit lap
        changes by ±1 (from lap 25 to 24–26)."
    """
    from src.models.tire_degradation import get_degradation_model

    if degradation_model is None:
        degradation_model = get_degradation_model()

    base_pit_loss = get_pit_loss(track_id)
    overrides_plus = set_pit_loss_for_testing(track_id, base_pit_loss + pit_loss_delta_sec)
    overrides_minus = set_pit_loss_for_testing(track_id, base_pit_loss - pit_loss_delta_sec)

    results_base = optimize_pit_window(
        current_lap=current_lap,
        current_compound=current_compound,
        lap_in_stint=lap_in_stint,
        total_race_laps=total_race_laps,
        track_id=track_id,
        new_compound=new_compound,
        pit_window_size=pit_window_size,
        initial_fuel_kg=initial_fuel_kg,
        fuel_per_lap_kg=fuel_per_lap_kg,
        degradation_model=degradation_model,
    )
    results_plus = optimize_pit_window(
        current_lap=current_lap,
        current_compound=current_compound,
        lap_in_stint=lap_in_stint,
        total_race_laps=total_race_laps,
        track_id=track_id,
        new_compound=new_compound,
        pit_window_size=pit_window_size,
        initial_fuel_kg=initial_fuel_kg,
        fuel_per_lap_kg=fuel_per_lap_kg,
        degradation_model=degradation_model,
        pit_loss_overrides=overrides_plus,
    )
    results_minus = optimize_pit_window(
        current_lap=current_lap,
        current_compound=current_compound,
        lap_in_stint=lap_in_stint,
        total_race_laps=total_race_laps,
        track_id=track_id,
        new_compound=new_compound,
        pit_window_size=pit_window_size,
        initial_fuel_kg=initial_fuel_kg,
        fuel_per_lap_kg=fuel_per_lap_kg,
        degradation_model=degradation_model,
        pit_loss_overrides=overrides_minus,
    )

    base_rec = recommended_pit_lap(results_base)
    plus_rec = recommended_pit_lap(results_plus)
    minus_rec = recommended_pit_lap(results_minus)

    def _lap_str(lap: int | None) -> str:
        return str(lap) if lap is not None else "stay out"

    # Human-readable message
    if base_rec is None and plus_rec is None and minus_rec is None:
        message = (
            f"If pit loss changes by ±{pit_loss_delta_sec:.1f} s (base {base_pit_loss:.1f} s), "
            "the recommendation stays \"stay out\" in all cases."
        )
    elif base_rec is None:
        message = (
            f"If pit loss changes by ±{pit_loss_delta_sec:.1f} s (base {base_pit_loss:.1f} s), "
            f"recommended pit lap shifts: base = stay out; +{pit_loss_delta_sec:.1f} s → lap {_lap_str(plus_rec)}; "
            f"-{pit_loss_delta_sec:.1f} s → lap {_lap_str(minus_rec)}."
        )
    else:
        delta_plus = (plus_rec - base_rec) if plus_rec is not None else None
        delta_minus = (minus_rec - base_rec) if minus_rec is not None else None
        changes = []
        if delta_plus is not None and delta_plus != 0:
            changes.append(f"+{pit_loss_delta_sec:.1f} s → {delta_plus:+d} lap(s)")
        if delta_minus is not None and delta_minus != 0:
            changes.append(f"-{pit_loss_delta_sec:.1f} s → {delta_minus:+d} lap(s)")
        if changes:
            message = (
                f"If pit loss changes by ±{pit_loss_delta_sec:.1f} s (base {base_pit_loss:.1f} s), "
                f"recommended pit lap changes: from lap {base_rec} to "
                f"+{pit_loss_delta_sec:.1f} s: lap {_lap_str(plus_rec)}; "
                f"-{pit_loss_delta_sec:.1f} s: lap {_lap_str(minus_rec)}. "
                f"Small change in pit loss, noticeable impact on optimal lap."
            )
        else:
            message = (
                f"If pit loss changes by ±{pit_loss_delta_sec:.1f} s (base {base_pit_loss:.1f} s), "
                f"recommended pit lap stays at lap {base_rec}."
            )

    return {
        "base_pit_loss_sec": base_pit_loss,
        "base_rec_lap": base_rec,
        "plus_delta_rec_lap": plus_rec,
        "minus_delta_rec_lap": minus_rec,
        "pit_loss_delta_sec": pit_loss_delta_sec,
        "message": message,
    }
