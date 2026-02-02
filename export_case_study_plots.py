"""
Export case study visualizations: predicted vs actual lap times and strategy timelines.

Runs 3–5 dry races from CASE_STUDIES, generates readable labeled plots, and exports
as PNG and interactive HTML for portfolio display. Reproducible: same inputs → same outputs.

Usage (from project root):
    python export_case_study_plots.py

Outputs:
    data/processed/figures/{year}_{race_slug}/predicted_vs_actual_{driver}.png
    data/processed/figures/{year}_{race_slug}/predicted_vs_actual_{driver}.html
    data/processed/figures/{year}_{race_slug}/strategy_timeline_{driver}.png
    data/processed/figures/{year}_{race_slug}/strategy_timeline_{driver}.html
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

# Case studies: (year, race_name) — dry races from CASE_STUDIES
CASE_STUDY_RACES = [
    (2023, "Bahrain"),
    (2023, "Spain"),
    (2023, "Monaco"),
    (2023, "Silverstone"),
    (2023, "Monza"),
]


def _race_slug(year: int, race_name: str) -> str:
    """Safe directory name: e.g. 2023_Monaco."""
    slug = re.sub(r"[^\w\s-]", "", race_name).strip().replace(" ", "_") or "race"
    return f"{year}_{slug}"


def _driver_for_plots(laps) -> str | None:
    """Pick one driver with enough laps (first by driver number)."""
    if laps.empty or "DriverNumber" not in laps.columns:
        return None
    counts = laps.groupby("DriverNumber").size()
    # Prefer driver with at least 20 laps
    for dr, cnt in counts.items():
        if cnt >= 20:
            return str(dr)
    return str(counts.index[0]) if len(counts) else None


def main() -> int:
    from src.data_pipeline import add_stint_features, load_race
    from src.models.tire_degradation import TireDegradationModel, get_degradation_model
    from src.strategy.optimizer import optimize_pit_window, recommended_pit_lap
    from src.utils.config import FIGURES_DIR
    from src.visualization.degradation_plots import (
        plot_predicted_vs_actual,
        plot_predicted_vs_actual_plotly,
    )
    from src.visualization.export_utils import export_figure_png, export_plotly_html
    from src.visualization.strategy_plots import (
        plot_strategy_timeline_from_laps,
        plot_strategy_timeline_plotly,
    )

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    exported = 0

    for year, race_name in CASE_STUDY_RACES:
        slug = _race_slug(year, race_name)
        out_dir = FIGURES_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            data = load_race(year, race_name)
        except ValueError as e:
            if "Wet" in str(e) or "dry" in str(e).lower():
                print(f"Skipping {year} {race_name}: wet race.", file=sys.stderr)
            else:
                print(f"Skipping {year} {race_name}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Skipping {year} {race_name}: {e}", file=sys.stderr)
            continue

        laps = add_stint_features(data.laps, data.pit_stops)
        if laps.empty or "LapTime" not in laps.columns or "lap_in_stint" not in laps.columns:
            print(f"Skipping {year} {race_name}: insufficient lap data.", file=sys.stderr)
            continue

        track_id = race_name
        model = get_degradation_model()
        # Ensure model fitted for this track (fit from this race if missing)
        for comp in ("SOFT", "MEDIUM", "HARD"):
            subset = laps[laps["Compound"].str.upper().str.strip() == comp]
            if len(subset) < 2:
                continue
            try:
                model.predict_lap_time(track_id, comp, 1, 100.0)
            except ValueError:
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
            pass

        driver = _driver_for_plots(laps)
        if not driver:
            continue

        driver_laps = laps[laps["DriverNumber"].astype(str) == str(driver)].sort_values("LapNumber")
        if len(driver_laps) < 5:
            continue

        # Predicted lap times for this driver
        pred_sec = []
        for _, row in driver_laps.iterrows():
            comp = str(row.get("Compound", "SOFT")).strip().upper()
            lap_in_stint = int(row.get("lap_in_stint", 1))
            fuel = float(row.get("estimated_fuel_kg", 100.0))
            t = model.predict_lap_time(track_id, comp, lap_in_stint, fuel)
            pred_sec.append(t)
        lap_numbers = driver_laps["LapNumber"].values
        if pd.api.types.is_timedelta64_dtype(driver_laps["LapTime"]):
            actual_sec = driver_laps["LapTime"].dt.total_seconds().values
        else:
            actual_sec = pd.to_numeric(driver_laps["LapTime"], errors="coerce").values

        title_pva = f"{year} {race_name} — Driver {driver} (predicted vs actual)"
        # Matplotlib: predicted vs actual → PNG
        ax = plot_predicted_vs_actual(
            lap_numbers,
            actual_sec,
            pred_sec,
            title=title_pva,
            xlabel="Lap number",
            ylabel="Lap time (s)",
        )
        png_path = out_dir / f"predicted_vs_actual_{driver}.png"
        import matplotlib.pyplot as plt
        export_figure_png(ax.get_figure(), png_path)
        plt.close(ax.get_figure())
        exported += 1
        print(f"Exported {png_path}")

        # Plotly: predicted vs actual → HTML
        fig_plotly = plot_predicted_vs_actual_plotly(
            lap_numbers,
            actual_sec,
            pred_sec,
            title=title_pva,
            xlabel="Lap number",
            ylabel="Lap time (s)",
        )
        html_path = out_dir / f"predicted_vs_actual_{driver}.html"
        export_plotly_html(fig_plotly, html_path)
        exported += 1
        print(f"Exported {html_path}")

        # Pit window: recommend at lap 15 for display
        current_lap = min(15, driver_laps["LapNumber"].max() - 5)
        row_at = driver_laps[driver_laps["LapNumber"] == current_lap]
        if row_at.empty:
            row_at = driver_laps.iloc[:1]
        current_compound = str(row_at["Compound"].iloc[0]).strip().upper()
        lap_in_stint = int(row_at["lap_in_stint"].iloc[0])
        total_race_laps = int(laps["LapNumber"].max())
        results = optimize_pit_window(
            current_lap=current_lap,
            current_compound=current_compound,
            lap_in_stint=lap_in_stint,
            total_race_laps=total_race_laps,
            track_id=track_id,
            new_compound="MEDIUM",
            degradation_model=model,
        )
        rec = recommended_pit_lap(results)
        pit_window = (rec - 2, rec + 2) if rec is not None else None

        # Stints for this driver (for plotly we need stints list)
        driver_laps_sorted = driver_laps.sort_values("LapNumber")
        stints_list = []
        if "stint_id" in driver_laps_sorted.columns:
            for sid, grp in driver_laps_sorted.groupby("stint_id"):
                start = int(grp["LapNumber"].min())
                end = int(grp["LapNumber"].max())
                comp = grp["Compound"].mode().iloc[0] if not grp.empty else "UNKNOWN"
                stints_list.append((start, end, str(comp).strip().upper()))
        else:
            cur_start = cur_end = None
            cur_compound = None
            for _, row in driver_laps_sorted.iterrows():
                lap = int(row["LapNumber"])
                comp = str(row["Compound"]).strip().upper()
                if cur_compound is None or comp != cur_compound:
                    if cur_compound is not None:
                        stints_list.append((cur_start, cur_end, cur_compound))
                    cur_start = cur_end = lap
                    cur_compound = comp
                else:
                    cur_end = lap
            if cur_compound is not None:
                stints_list.append((cur_start, cur_end, cur_compound))

        title_tl = f"{year} {race_name} — Driver {driver} (strategy timeline)"
        # Matplotlib: strategy timeline → PNG
        ax_tl = plot_strategy_timeline_from_laps(
            laps,
            data.pit_stops,
            driver_filter=driver,
            pit_window=pit_window,
            title=title_tl,
        )
        png_tl = out_dir / f"strategy_timeline_{driver}.png"
        export_figure_png(ax_tl.get_figure(), png_tl)
        plt.close(ax_tl.get_figure())
        exported += 1
        print(f"Exported {png_tl}")

        # Plotly: strategy timeline → HTML
        fig_tl = plot_strategy_timeline_plotly(
            stints_list,
            pit_laps=data.pit_stops[data.pit_stops["DriverNumber"].astype(str) == str(driver)]["LapNumber"].dropna().astype(int).tolist() if not data.pit_stops.empty else None,
            pit_window=pit_window,
            title=title_tl,
            xlabel="Lap number",
        )
        html_tl = out_dir / f"strategy_timeline_{driver}.html"
        export_plotly_html(fig_tl, html_tl)
        exported += 1
        print(f"Exported {html_tl}")

    print(f"Done. Exported {exported} files to {FIGURES_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
