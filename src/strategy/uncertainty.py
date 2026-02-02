"""Uncertainty-aware recommendation bundle for IRL use.

Single call returns recommended lap, pit window (laps X–Y), sensitivity messages
(pit loss, degradation), and one VSC scenario. No breaking changes to existing code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.strategy.optimizer import (
    optimize_pit_window,
    pit_window_range,
    recommended_pit_lap,
)
from src.strategy.sensitivity import (
    sensitivity_degradation,
    sensitivity_pit_loss,
    vsc_recommendation,
)
from src.utils.config import (
    DEGRADATION_SENSITIVITY_DELTA_SEC_PER_LAP,
    PIT_WINDOW_WITHIN_SEC,
    VSC_PIT_LOSS_FACTOR,
)

if TYPE_CHECKING:
    from src.models.tire_degradation import TireDegradationModel


def recommendation_bundle(
    current_lap: int,
    current_compound: str,
    lap_in_stint: int,
    total_race_laps: int,
    track_id: str,
    new_compound: str,
    *,
    within_sec: float = PIT_WINDOW_WITHIN_SEC,
    degradation_delta: float = DEGRADATION_SENSITIVITY_DELTA_SEC_PER_LAP,
    vsc_factor: float = VSC_PIT_LOSS_FACTOR,
    degradation_model: TireDegradationModel | None = None,
    pit_window_size: int = 10,
    initial_fuel_kg: float = 110.0,
    fuel_per_lap_kg: float = 1.8,
    track_temp: float | None = None,
    include_explanation: bool = True,
) -> dict:
    """
    Build a single IRL-usable block: recommended lap, pit window, sensitivities, VSC.

    Runs optimize_pit_window once, then sensitivity_pit_loss, sensitivity_degradation,
    and vsc_recommendation. Optionally includes explain_strategy summary.

    Returns
    -------
    dict
        recommended_lap, pit_window_min, pit_window_max, explanation (or summary_display),
        sensitivity_pit_loss_message, sensitivity_degradation_message, vsc_message.
    """
    from src.models.tire_degradation import get_degradation_model

    if degradation_model is None:
        degradation_model = get_degradation_model()

    results = optimize_pit_window(
        current_lap=current_lap,
        current_compound=current_compound,
        lap_in_stint=lap_in_stint,
        total_race_laps=total_race_laps,
        track_id=track_id,
        new_compound=new_compound,
        pit_window_size=pit_window_size,
        initial_fuel_kg=initial_fuel_kg,
        fuel_per_lap_kg=fuel_per_lap_kg,
        track_temp=track_temp,
        degradation_model=degradation_model,
    )

    rec = recommended_pit_lap(results)
    pmin, pmax = pit_window_range(results, within_sec=within_sec)

    sens_pl = sensitivity_pit_loss(
        current_lap=current_lap,
        current_compound=current_compound,
        lap_in_stint=lap_in_stint,
        total_race_laps=total_race_laps,
        track_id=track_id,
        new_compound=new_compound,
        pit_loss_delta_sec=2.0,
        degradation_model=degradation_model,
        pit_window_size=pit_window_size,
        initial_fuel_kg=initial_fuel_kg,
        fuel_per_lap_kg=fuel_per_lap_kg,
    )
    sens_deg = sensitivity_degradation(
        current_lap=current_lap,
        current_compound=current_compound,
        lap_in_stint=lap_in_stint,
        total_race_laps=total_race_laps,
        track_id=track_id,
        new_compound=new_compound,
        degradation_delta_sec_per_lap=degradation_delta,
        degradation_model=degradation_model,
        pit_window_size=pit_window_size,
        initial_fuel_kg=initial_fuel_kg,
        fuel_per_lap_kg=fuel_per_lap_kg,
        track_temp=track_temp,
    )
    vsc = vsc_recommendation(
        current_lap=current_lap,
        current_compound=current_compound,
        lap_in_stint=lap_in_stint,
        total_race_laps=total_race_laps,
        track_id=track_id,
        new_compound=new_compound,
        vsc_pit_loss_factor=vsc_factor,
        degradation_model=degradation_model,
        pit_window_size=pit_window_size,
        initial_fuel_kg=initial_fuel_kg,
        fuel_per_lap_kg=fuel_per_lap_kg,
        track_temp=track_temp,
    )

    explanation = None
    if include_explanation:
        try:
            from src.strategy.explanation import explain_strategy

            ex = explain_strategy(
                results, track_id, current_compound, degradation_model=degradation_model
            )
            explanation = ex.get("summary_display", ex.get("summary", ""))
        except Exception:  # pylint: disable=broad-except
            pass

    return {
        "recommended_lap": rec,
        "pit_window_min": pmin,
        "pit_window_max": pmax,
        "explanation": explanation,
        "sensitivity_pit_loss_message": sens_pl["message"],
        "sensitivity_degradation_message": sens_deg["message"],
        "vsc_message": vsc["message"],
    }
