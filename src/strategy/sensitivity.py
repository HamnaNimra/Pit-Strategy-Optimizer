"""Parameter sensitivity analysis: small changes, big impact.

Example: "If pit loss ±2 s, recommended pit lap changes by X."
Degradation sensitivity and VSC scenario (pit loss factor) for IRL use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.strategy.optimizer import optimize_pit_window, recommended_pit_lap
from src.strategy.pit_loss import get_pit_loss, set_pit_loss_for_testing

if TYPE_CHECKING:
    from src.models.tire_degradation import TireDegradationModel


class DegradationWrapper:
    """Wraps a TireDegradationModel to simulate worse or better degradation.

    predict_lap_time returns base_model.predict_lap_time(...) + (lap_in_stint - 1) * degradation_delta_sec_per_lap.
    Used for sensitivity analysis without modifying the underlying model or optimizer.
    """

    def __init__(
        self,
        base_model: TireDegradationModel,
        degradation_delta_sec_per_lap: float,
    ) -> None:
        self._base = base_model
        self._delta = degradation_delta_sec_per_lap

    def predict_lap_time(
        self,
        track_id: str,
        compound: str,
        lap_in_stint: float | int,
        fuel_kg: float,
        track_temp: float | None = None,
    ) -> float:
        base_sec = self._base.predict_lap_time(
            track_id, compound, lap_in_stint, fuel_kg, track_temp
        )
        lap_idx = int(lap_in_stint) if isinstance(lap_in_stint, (int, float)) else 1
        return base_sec + (lap_idx - 1) * self._delta


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


def sensitivity_degradation(
    current_lap: int,
    current_compound: str,
    lap_in_stint: int,
    total_race_laps: int,
    track_id: str,
    new_compound: str,
    *,
    degradation_delta_sec_per_lap: float = 0.02,
    degradation_model: TireDegradationModel | None = None,
    pit_window_size: int = 10,
    initial_fuel_kg: float = 110.0,
    fuel_per_lap_kg: float = 1.8,
    track_temp: float | None = None,
) -> dict:
    """
    Run optimizer with base model and with degradation ± delta; report how
    recommended pit lap changes. Uses DegradationWrapper; no change to real model.

    Returns
    -------
    dict
        base_rec_lap, plus_delta_rec_lap, minus_delta_rec_lap, message (e.g. "If
        degradation ±0.02 s/lap, recommended pit lap changes from lap 26 to 24–28").
    """
    from src.models.tire_degradation import get_degradation_model

    if degradation_model is None:
        degradation_model = get_degradation_model()

    wrapper_plus = DegradationWrapper(degradation_model, degradation_delta_sec_per_lap)
    wrapper_minus = DegradationWrapper(degradation_model, -degradation_delta_sec_per_lap)

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
        track_temp=track_temp,
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
        track_temp=track_temp,
        degradation_model=wrapper_plus,
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
        track_temp=track_temp,
        degradation_model=wrapper_minus,
    )

    base_rec = recommended_pit_lap(results_base)
    plus_rec = recommended_pit_lap(results_plus)
    minus_rec = recommended_pit_lap(results_minus)

    def _lap_str(lap: int | None) -> str:
        return str(lap) if lap is not None else "stay out"

    if base_rec is None and plus_rec is None and minus_rec is None:
        message = (
            f"If degradation ±{degradation_delta_sec_per_lap:.2f} s/lap, "
            "the recommendation stays \"stay out\" in all cases."
        )
    elif base_rec is None:
        message = (
            f"If degradation ±{degradation_delta_sec_per_lap:.2f} s/lap, "
            f"recommended pit lap: base = stay out; +delta → lap {_lap_str(plus_rec)}; "
            f"-delta → lap {_lap_str(minus_rec)}."
        )
    else:
        parts = [f"from lap {base_rec}"]
        if plus_rec is not None or minus_rec is not None:
            laps = [x for x in (plus_rec, minus_rec) if x is not None]
            if laps:
                parts.append(f"to {min(laps)}–{max(laps)}" if len(laps) > 1 else f"to {laps[0]}")
        message = (
            f"If degradation ±{degradation_delta_sec_per_lap:.2f} s/lap, "
            f"recommended pit lap changes {', '.join(parts)}."
        )

    return {
        "base_rec_lap": base_rec,
        "plus_delta_rec_lap": plus_rec,
        "minus_delta_rec_lap": minus_rec,
        "degradation_delta_sec_per_lap": degradation_delta_sec_per_lap,
        "message": message,
    }


def vsc_recommendation(
    current_lap: int,
    current_compound: str,
    lap_in_stint: int,
    total_race_laps: int,
    track_id: str,
    new_compound: str,
    *,
    vsc_pit_loss_factor: float = 0.5,
    degradation_model: TireDegradationModel | None = None,
    pit_window_size: int = 10,
    initial_fuel_kg: float = 110.0,
    fuel_per_lap_kg: float = 1.8,
    track_temp: float | None = None,
) -> dict:
    """
    Run optimizer with pit loss scaled by factor (e.g. 0.5 for VSC). Returns
    vsc_rec_lap and message for "If VSC next lap: pit on lap X".

    Parameters
    ----------
    vsc_pit_loss_factor : float
        Pit loss under VSC = base_pit_loss * factor (e.g. 0.5 = 50%).
    """
    from src.models.tire_degradation import get_degradation_model

    if degradation_model is None:
        degradation_model = get_degradation_model()

    base_pit_loss = get_pit_loss(track_id)
    vsc_pit_loss = base_pit_loss * vsc_pit_loss_factor
    overrides = set_pit_loss_for_testing(track_id, vsc_pit_loss)

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
        pit_loss_overrides=overrides,
    )
    vsc_rec = recommended_pit_lap(results)
    pct = int(vsc_pit_loss_factor * 100)
    message = (
        f"If VSC in the next lap (pit loss ~{pct}%), recommended pit lap: "
        f"{vsc_rec if vsc_rec is not None else 'stay out'}."
    )
    return {
        "vsc_rec_lap": vsc_rec,
        "vsc_pit_loss_factor": vsc_pit_loss_factor,
        "message": message,
    }
