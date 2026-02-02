"""CLI entry point for the Motorsports Pit Strategy Optimizer.

Example:
    python run_strategy.py --year 2024 --race Monaco --driver VER
    python run_strategy.py --year 2024 --race Monaco --driver VER --lap 20 --new-compound MEDIUM
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pit strategy analysis for a race and driver.",
        epilog="Loads race data, runs the optimizer at the given lap, and prints recommendation and explanation.",
    )
    parser.add_argument(
        "--year", type=int, required=True, help="Season year (e.g. 2024)"
    )
    parser.add_argument(
        "--race",
        type=str,
        required=True,
        help="Race name or location (e.g. Monaco, Bahrain)",
    )
    parser.add_argument(
        "--driver", type=str, required=True, help="Driver code or number (e.g. VER, 1)"
    )
    parser.add_argument(
        "--lap",
        type=int,
        default=None,
        help="Lap number at which to evaluate strategy (default: 10)",
    )
    parser.add_argument(
        "--new-compound",
        type=str,
        default="MEDIUM",
        choices=["SOFT", "MEDIUM", "HARD"],
        help="Compound to fit at pit stop (default: MEDIUM)",
    )
    return parser.parse_args()


def _driver_laps(laps, driver: str):
    """Filter laps to one driver; match Driver (3-letter) or DriverNumber."""
    driver_str = str(driver).strip().upper()
    if "Driver" in laps.columns:
        mask = laps["Driver"].astype(str).str.upper() == driver_str
        if mask.any():
            return laps.loc[mask].sort_values("LapNumber")
    if "DriverNumber" in laps.columns:
        mask = laps["DriverNumber"].astype(str) == driver_str
        if mask.any():
            return laps.loc[mask].sort_values("LapNumber")
    return laps.iloc[0:0]


def _state_at_lap(driver_laps, lap: int):
    """Get current_compound and lap_in_stint at given lap; (compound, lap_in_stint) or (None, None)."""
    row = driver_laps[driver_laps["LapNumber"] == lap]
    if row.empty:
        # Nearest lap
        idx = (driver_laps["LapNumber"] - lap).abs().idxmin()
        row = driver_laps.loc[[idx]]
    if row.empty:
        return None, None
    compound = row["Compound"].iloc[0] if "Compound" in row.columns else None
    lap_in_stint = (
        row["lap_in_stint"].iloc[0] if "lap_in_stint" in row.columns else None
    )
    if compound is None:
        return None, None
    if pd.isna(lap_in_stint):
        lap_in_stint = 1
    return str(compound).strip().upper() if compound else None, (
        int(lap_in_stint) if lap_in_stint is not None else 1
    )


def main() -> int:
    args = _parse_args()
    year = args.year
    race_name = args.race.strip()
    driver = args.driver.strip()
    lap = args.lap
    new_compound = args.new_compound.strip().upper()

    # 1. Load race data
    try:
        from src.data_pipeline import add_stint_features, load_race

        data = load_race(year, race_name)
    except ValueError as e:
        if "Wet" in str(e) or "dry" in str(e).lower():
            print(
                "Error: This race was run in wet conditions. Only dry races are supported.",
                file=sys.stderr,
            )
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error loading race data: {e}", file=sys.stderr)
        return 1

    laps = add_stint_features(data.laps, data.pit_stops)
    if laps.empty:
        print("Error: No lap data after processing.", file=sys.stderr)
        return 1

    driver_laps = _driver_laps(laps, driver)
    if driver_laps.empty:
        print(
            f"Error: No laps found for driver '{driver}'. Check --driver (e.g. VER or driver number).",
            file=sys.stderr,
        )
        return 1

    total_race_laps = int(laps["LapNumber"].max())
    if lap is None:
        lap = 10
    lap = max(1, min(lap, total_race_laps))

    current_compound, lap_in_stint = _state_at_lap(driver_laps, lap)
    if current_compound is None:
        print(
            f"Error: Could not determine compound for driver at lap {lap}.",
            file=sys.stderr,
        )
        return 1

    track_id = race_name

    # 2. Ensure degradation model is fitted for this track and compounds (fit from race data if missing)
    try:
        from src.models.tire_degradation import get_degradation_model

        model = get_degradation_model()
        compounds_needed = {current_compound, new_compound}
        for comp in compounds_needed:
            try:
                model.predict_lap_time(track_id, comp, 1, 100.0)
            except ValueError:
                # Not fitted: fit from this race's laps
                model.fit(
                    laps,
                    track_id,
                    comp,
                    lap_time_col="LapTime",
                    lap_in_stint_col="lap_in_stint",
                    fuel_col="estimated_fuel_kg",
                )
        try:
            model.save()
        except OSError:
            print(
                "Warning: Could not save degradation model to disk; results still use in-memory model.",
                file=sys.stderr,
            )
    except ValueError as e:
        if "No laps found" in str(e) or "Too few valid" in str(e):
            print(
                f"Error: Not enough lap data to fit degradation for {track_id} / {compounds_needed}. Try another race or fit models manually (see docs/CASE_STUDIES.md).",
                file=sys.stderr,
            )
        else:
            print(f"Error fitting degradation model: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error preparing degradation model: {e}", file=sys.stderr)
        return 1

    # 3. Run optimizer
    try:
        from src.strategy.optimizer import (
            optimize_pit_window,
            pit_window_range,
            recommended_pit_lap,
        )
        from src.utils.config import (
            DEGRADATION_SENSITIVITY_DELTA_SEC_PER_LAP,
            PIT_WINDOW_WITHIN_SEC,
            VSC_PIT_LOSS_FACTOR,
        )

        results = optimize_pit_window(
            current_lap=lap,
            current_compound=current_compound,
            lap_in_stint=lap_in_stint,
            total_race_laps=total_race_laps,
            track_id=track_id,
            new_compound=new_compound,
            degradation_model=model,
        )
    except ValueError as e:
        if "fitted model" in str(e).lower() or "fit" in str(e).lower():
            print(
                "Error: No fitted degradation model for this track/compound. Fit models first (see docs/CASE_STUDIES.md).",
                file=sys.stderr,
            )
        else:
            print(f"Error running optimizer: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error running optimizer: {e}", file=sys.stderr)
        return 1

    rec = recommended_pit_lap(results)

    # 4. Explanation
    try:
        from src.strategy.explanation import explain_strategy

        ex = explain_strategy(
            results, track_id, current_compound, degradation_model=model
        )
    except Exception as e:
        ex = None
        print(f"Warning: Could not generate explanation: {e}", file=sys.stderr)

    # 5. Pit window (within 2 s)
    try:
        pmin, pmax = pit_window_range(results, within_sec=PIT_WINDOW_WITHIN_SEC)
    except Exception:  # pylint: disable=broad-except
        pmin, pmax = None, None

    # 6. Print recommendation and explanation
    print(f"Race: {year} {race_name}  |  Driver: {driver}  |  At lap: {lap}")
    print(
        f"Current compound: {current_compound}  |  Lap in stint: {lap_in_stint}  |  New compound: {new_compound}"
    )
    print()
    if rec is None:
        print("Recommendation: Stay out (no pit).")
    else:
        print(f"Recommendation: Pit on lap {rec}.")
    if pmin is not None and pmax is not None:
        print(f"Pit window (within {PIT_WINDOW_WITHIN_SEC} s): laps {pmin}–{pmax}")
    print()
    if ex:
        print("Explanation:")
        print(ex.get("summary_display", ex["summary"]))
        # Parameter sensitivity: pit loss ±2 s impact
        try:
            from src.strategy.sensitivity import sensitivity_pit_loss

            sens = sensitivity_pit_loss(
                current_lap=lap,
                current_compound=current_compound,
                lap_in_stint=lap_in_stint,
                total_race_laps=total_race_laps,
                track_id=track_id,
                new_compound=new_compound,
                pit_loss_delta_sec=2.0,
                degradation_model=model,
            )
            print("\nSensitivity (pit loss ±2 s):", sens["message"])
        except Exception:  # pylint: disable=broad-except
            pass
        # Sensitivity: degradation ±0.02 s/lap
        try:
            from src.strategy.sensitivity import sensitivity_degradation

            sens_deg = sensitivity_degradation(
                current_lap=lap,
                current_compound=current_compound,
                lap_in_stint=lap_in_stint,
                total_race_laps=total_race_laps,
                track_id=track_id,
                new_compound=new_compound,
                degradation_delta_sec_per_lap=DEGRADATION_SENSITIVITY_DELTA_SEC_PER_LAP,
                degradation_model=model,
            )
            print(
                f"\nSensitivity (degradation ±{DEGRADATION_SENSITIVITY_DELTA_SEC_PER_LAP} s/lap):",
                sens_deg["message"],
            )
        except Exception:  # pylint: disable=broad-except
            pass
        # VSC scenario
        try:
            from src.strategy.sensitivity import vsc_recommendation

            vsc = vsc_recommendation(
                current_lap=lap,
                current_compound=current_compound,
                lap_in_stint=lap_in_stint,
                total_race_laps=total_race_laps,
                track_id=track_id,
                new_compound=new_compound,
                vsc_pit_loss_factor=VSC_PIT_LOSS_FACTOR,
                degradation_model=model,
            )
            print("\nIf VSC next lap:", vsc["message"])
        except Exception:  # pylint: disable=broad-except
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
