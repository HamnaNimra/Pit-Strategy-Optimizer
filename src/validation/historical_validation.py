"""Historical validation of strategy recommendations.

For selected clean, dry races: run the optimizer at each real pit decision point,
compare recommended vs actual pit lap, compute lap delta and alignment metrics.
Results are stored in structured data (DataFrame + summary). Analysis limited to
dry races (load_race already enforces this).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from src.data_pipeline import add_stint_features, load_race
from src.strategy.optimizer import optimize_pit_window, recommended_pit_lap
from src.utils.config import VALIDATION_RESULTS_DIR

if TYPE_CHECKING:
    from src.models.tire_degradation import TireDegradationModel

# Acceptable window for alignment: recommendation within ± this many laps of actual (PRD §9)
ALIGNMENT_WINDOW_LAPS = 3


def _get_lap_value(laps: pd.DataFrame, driver: str | int, lap_num: int, col: str):
    """Return scalar value from laps for (driver, lap_num, col); None if missing."""
    dr = str(driver)
    subset = laps[
        (laps["DriverNumber"].astype(str) == dr) & (laps["LapNumber"] == lap_num)
    ]
    if subset.empty or col not in subset.columns:
        return None
    val = subset[col].iloc[0]
    return val if pd.notna(val) else None


def _validate_race(
    year: int,
    laps: pd.DataFrame,
    pit_stops: pd.DataFrame,
    track_id: str,
    total_race_laps: int,
    degradation_model: TireDegradationModel,
    *,
    pit_window_size: int = 10,
    initial_fuel_kg: float = 110.0,
    fuel_per_lap_kg: float = 1.8,
) -> list[dict]:
    """
    Run optimizer at each pit decision point for one race; return list of result rows.

    Each pit stop is a decision point: we simulate the optimizer as if at the start
    of that lap (current_lap = pit lap, current_compound and lap_in_stint from laps).
    """
    rows = []
    if pit_stops.empty or laps.empty:
        return rows
    if "lap_in_stint" not in laps.columns or "Compound" not in laps.columns:
        return rows

    for _, pit in pit_stops.iterrows():
        driver = pit.get("DriverNumber")
        actual_pit_lap = pit.get("LapNumber")
        new_compound = pit.get("Compound")
        if driver is None or pd.isna(actual_pit_lap) or pd.isna(new_compound):
            continue
        actual_pit_lap = int(actual_pit_lap)
        new_compound = str(new_compound).strip().upper()
        current_compound = _get_lap_value(laps, driver, actual_pit_lap, "Compound")
        lap_in_stint_val = _get_lap_value(laps, driver, actual_pit_lap, "lap_in_stint")
        if current_compound is None:
            current_compound = new_compound  # fallback
        if lap_in_stint_val is None:
            lap_in_stint_val = 1
        else:
            lap_in_stint_val = int(lap_in_stint_val)

        try:
            results = optimize_pit_window(
                current_lap=actual_pit_lap,
                current_compound=current_compound,
                lap_in_stint=lap_in_stint_val,
                total_race_laps=total_race_laps,
                track_id=track_id,
                new_compound=new_compound,
                pit_window_size=pit_window_size,
                initial_fuel_kg=initial_fuel_kg,
                fuel_per_lap_kg=fuel_per_lap_kg,
                degradation_model=degradation_model,
            )
        except Exception:  # pylint: disable=broad-except
            rows.append(
                {
                    "year": year,
                    "track_id": track_id,
                    "driver_number": str(driver),
                    "actual_pit_lap": actual_pit_lap,
                    "recommended_pit_lap": None,
                    "lap_delta": None,
                    "alignment_within_3": False,
                    "current_compound": current_compound,
                    "new_compound": new_compound,
                    "lap_in_stint": lap_in_stint_val,
                    "error": True,
                }
            )
            continue

        rec = recommended_pit_lap(results)
        if rec is not None:
            lap_delta = rec - actual_pit_lap
            alignment = abs(lap_delta) <= ALIGNMENT_WINDOW_LAPS
        else:
            lap_delta = None
            alignment = False  # we said stay out, they pitted

        rows.append(
            {
                "year": year,
                "track_id": track_id,
                "driver_number": str(driver),
                "actual_pit_lap": actual_pit_lap,
                "recommended_pit_lap": rec,
                "lap_delta": lap_delta,
                "alignment_within_3": alignment,
                "current_compound": current_compound,
                "new_compound": new_compound,
                "lap_in_stint": lap_in_stint_val,
                "error": False,
            }
        )
    return rows


def run_validation(
    races: list[tuple[int, str]],
    *,
    degradation_model: TireDegradationModel | None = None,
    pit_window_size: int = 10,
    initial_fuel_kg: float = 110.0,
    fuel_per_lap_kg: float = 1.8,
) -> tuple[pd.DataFrame, dict]:
    """
    Run historical validation for selected races (dry only).

    Loads each race (load_race enforces dry), adds stint features, then at each
    real pit stop runs the optimizer and compares recommended vs actual pit lap.
    Returns a details DataFrame and a summary dict.

    Parameters
    ----------
    races : list of (year, race_name)
        e.g. [(2023, "Bahrain"), (2023, "Monaco")]. Races must be loadable and dry.
    degradation_model : TireDegradationModel, optional
        Fitted model; default is get_degradation_model(). Must be fitted for
        each track/compound in the races.
    pit_window_size : int
        Passed to optimize_pit_window.
    initial_fuel_kg, fuel_per_lap_kg : float
        Fuel model for optimizer.

    Returns
    -------
    details : pd.DataFrame
        One row per pit decision. Columns: year, track_id, driver_number,
        actual_pit_lap, recommended_pit_lap, lap_delta, alignment_within_3,
        current_compound, new_compound, lap_in_stint, error.
    summary : dict
        total_decisions, count_within_3, pct_within_3, mean_abs_lap_delta,
        count_errors. mean_abs_lap_delta excludes None and error rows.
    """
    from src.models.tire_degradation import get_degradation_model

    if degradation_model is None:
        degradation_model = get_degradation_model()

    all_rows = []
    for year, race_name in races:
        try:
            data = load_race(year, race_name)
        except Exception:  # pylint: disable=broad-except
            continue
        laps = add_stint_features(data.laps, data.pit_stops)
        if laps.empty:
            continue
        total_race_laps = int(laps["LapNumber"].max())
        track_id = race_name
        rows = _validate_race(
            year,
            laps,
            data.pit_stops,
            track_id,
            total_race_laps,
            degradation_model,
            pit_window_size=pit_window_size,
            initial_fuel_kg=initial_fuel_kg,
            fuel_per_lap_kg=fuel_per_lap_kg,
        )
        all_rows.extend(rows)

    details = pd.DataFrame(all_rows)

    # Summary
    total = len(details)
    errors = details.get("error", pd.Series(dtype=bool))
    if "error" in details.columns:
        valid = details[~details["error"]]
    else:
        valid = details
    count_within_3 = (
        int(valid["alignment_within_3"].sum())
        if not valid.empty and "alignment_within_3" in valid.columns
        else 0
    )
    n_valid = len(valid)
    pct = (100.0 * count_within_3 / n_valid) if n_valid else 0.0
    deltas = valid["lap_delta"].dropna()
    mean_abs = float(deltas.abs().mean()) if len(deltas) else float("nan")
    count_errors = int(errors.sum()) if "error" in details.columns else 0

    summary = {
        "total_decisions": total,
        "count_within_3": count_within_3,
        "pct_within_3": round(pct, 2),
        "mean_abs_lap_delta": round(mean_abs, 2) if pd.notna(mean_abs) else None,
        "count_errors": count_errors,
    }
    return details, summary


def save_validation_results(
    details: pd.DataFrame,
    summary: dict,
    path: Path | str | None = None,
) -> Path:
    """
    Store validation results in structured form (CSV for details, summary in a small file).

    Parameters
    ----------
    details : pd.DataFrame
        Output details from run_validation.
    summary : dict
        Output summary from run_validation.
    path : Path or str, optional
        Directory to write to. Default: config VALIDATION_RESULTS_DIR.

    Returns
    -------
    Path
        Directory into which results were written.
    """
    dest = Path(path) if path is not None else VALIDATION_RESULTS_DIR
    dest.mkdir(parents=True, exist_ok=True)
    details.to_csv(dest / "validation_details.csv", index=False)
    with open(dest / "validation_summary.txt", "w", encoding="utf-8") as f:
        for k, v in summary.items():
            f.write(f"{k}: {v}\n")
    return dest


def load_validation_results(
    path: Path | str | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Load previously saved validation results.

    Parameters
    ----------
    path : Path or str, optional
        Directory containing validation_details.csv and validation_summary.txt.

    Returns
    -------
    details : pd.DataFrame
    summary : dict
    """
    dest = Path(path) if path is not None else VALIDATION_RESULTS_DIR
    details = (
        pd.read_csv(dest / "validation_details.csv")
        if (dest / "validation_details.csv").exists()
        else pd.DataFrame()
    )
    summary = {}
    summary_path = dest / "validation_summary.txt"
    if summary_path.exists():
        with open(summary_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    try:
                        v = int(v)
                    except ValueError:
                        try:
                            v = float(v)
                        except ValueError:
                            pass
                    summary[k] = v
    return details, summary
