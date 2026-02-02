# Motorsports Pit Strategy Optimizer

Decision-support for pit stop windows in Formula 1. The system models tire degradation and pit loss, recommends a pit lap (or stay out), explains the recommendation, and compares recommendations to historical team decisions. Single-car only; dry races only.

---

## Overview

- **Data:** Race data from the [FastF1](https://github.com/theOehrly/Fast-F1) library. Lap times, compounds, pit stops, and weather are loaded and cached; only dry sessions are used.
- **Model:** Linear tire degradation per track and compound (SOFT, MEDIUM, HARD). Lap time is predicted from lap-in-stint, fuel load, and optional track temperature. Models are fitted with scikit-learn and persisted to disk.
- **Strategy:** The optimizer simulates pitting on the current lap and N future laps, applies track-specific pit loss and degradation, and ranks strategies by total projected time. A rule-based explanation layer describes why the pit window opens, when degradation overtakes pit loss, and the cost of delaying or advancing the stop.
- **Validation:** Historical validation runs the optimizer at each real pit decision point and reports lap delta (recommended − actual) and alignment within ±3 laps. Results are stored as CSV and summary text.

Full requirements and scope are in the [Product Requirements Document](docs/PRD.md). [Assumptions and limitations](docs/ASSUMPTIONS.md) and [case studies](docs/CASE_STUDIES.md) are documented separately.

---

## Installation

```bash
git clone <repo-url>
cd Pit-Strategy-Optimizer
pip install -r requirements.txt
```

**Requirements:** FastF1, pandas, numpy, scikit-learn, joblib, matplotlib, plotly (see `requirements.txt`).

---

## Testing

From the project root (with dependencies installed):

```bash
pip install -r requirements.txt
pytest tests/ -v
```

- **Unit tests:** `test_pit_loss.py`, `test_preprocess.py`, `test_stint_features.py`, `test_data_pipeline.py`, `test_degradation_model.py`, `test_optimizer.py`, `test_explanation.py` — no network or FastF1 API.
- **Integration tests:** `test_integration.py` — end-to-end flow from synthetic laps and pit stops through stint features, degradation model fit, optimizer, recommendation, and explanation; and validation flow using `_validate_race` with synthetic data. No live FastF1 calls.

To run only unit or only integration tests: `pytest tests/ -v -k "not integration"` or `pytest tests/test_integration.py -v`.

---

## Project Structure

```
Pit-Strategy-Optimizer/
├── README.md
├── requirements.txt
├── run_strategy.py          # CLI entry point
├── data/
│   ├── raw/
│   ├── processed/            # validation results
│   └── cache/                # FastF1 + processed race cache
├── src/
│   ├── data_pipeline/        # load_race, preprocess, stint_features
│   ├── models/               # tire_degradation, diagnostics
│   ├── strategy/             # pit_loss, optimizer, explanation
│   ├── validation/           # historical_validation
│   ├── visualization/        # degradation_plots, strategy_plots
│   └── utils/                # config
├── docs/
│   ├── PRD.md
│   ├── ASSUMPTIONS.md
│   └── CASE_STUDIES.md
├── notebooks/
│   └── exploratory_analysis.ipynb
└── tests/
    ├── conftest.py           # shared fixtures (synthetic_laps, fitted_degradation_model, etc.)
    ├── test_data_pipeline.py
    ├── test_degradation_model.py
    ├── test_explanation.py
    ├── test_integration.py   # end-to-end (synthetic data only)
    ├── test_optimizer.py
    ├── test_pit_loss.py
    ├── test_preprocess.py
    ├── test_stint_features.py
```

---

## Data

- **Source:** FastF1. Race sessions are loaded by year and race name (`load_race(year, race_name)`). Lap times, sector times, compounds, stint info, pit stops, and weather are extracted into pandas DataFrames.
- **Dry only:** Sessions with rainfall in weather data are rejected; only slick compounds (SOFT, MEDIUM, HARD) are used.
- **Cache:** Processed race data (laps, pit_stops, weather) is cached under `data/cache/processed_races/` by year and race name. FastF1 API responses are cached under `data/cache/fastf1/`.

---

## Usage

### CLI

**Required:** `--year`, `--race`, `--driver`. **Optional:** `--lap` (default 10), `--new-compound` (default MEDIUM).

The CLI loads race data, ensures the degradation model is fitted for the track and compounds (fitting from race data if missing), runs the optimizer at the given lap, and prints the recommendation and explanation.

**Sample commands:**

```bash
# Help and options
python run_strategy.py --help

# Default lap (10), default new compound (MEDIUM)
python run_strategy.py --year 2024 --race Monaco --driver VER

# Evaluate at lap 20, pit onto MEDIUM
python run_strategy.py --year 2024 --race Monaco --driver VER --lap 20 --new-compound MEDIUM

# Different race and driver (driver number)
python run_strategy.py --year 2024 --race Bahrain --driver 1 --lap 15

# Pit onto HARD
python run_strategy.py --year 2023 --race Silverstone --driver HAM --lap 25 --new-compound HARD
```

First run for a given race may take longer while FastF1 data is fetched and the degradation model is fitted; later runs use cached data and saved models.

### Python API

- **Load race:** `from src.data_pipeline import load_race, add_stint_features` → `data = load_race(year, race_name)`, `laps = add_stint_features(data.laps, data.pit_stops)`.
- **Optimize:** `from src.strategy import optimize_pit_window, recommended_pit_lap` → `results = optimize_pit_window(...)`, `rec = recommended_pit_lap(results)`.
- **Explain:** `from src.strategy import explain_strategy` → `ex = explain_strategy(results, track_id, current_compound, ...)`.
- **Validate:** `from src.validation import run_validation, save_validation_results` → `details, summary = run_validation(races, degradation_model=model)`, `save_validation_results(details, summary)`.

---

## Validation

Historical validation (`run_validation(races, degradation_model=...)`) runs the optimizer at each real pit decision point for the given races, compares recommended vs actual pit lap, and returns:

- **Details:** One row per pit decision (year, track_id, driver_number, actual_pit_lap, recommended_pit_lap, lap_delta, alignment_within_3, compounds, error flag).
- **Summary:** total_decisions, count_within_3, pct_within_3, mean_abs_lap_delta, count_errors.

Results can be saved with `save_validation_results(details, summary)` and loaded with `load_validation_results()`. Selected races, inputs, and how to reproduce are in [Case studies](docs/CASE_STUDIES.md).

---

## Visualization

- **Predicted vs actual lap times:** `plot_predicted_vs_actual(lap_numbers, actual_seconds, predicted_seconds, ...)` or `plot_predicted_vs_actual_from_laps(laps, predicted_seconds, driver_filter=...)`.
- **Tire degradation curves:** `plot_degradation_curve(curve_df, compound_label=...)` or `plot_degradation_curves_by_compound({compound: df, ...})`.
- **Strategy timeline:** `plot_strategy_timeline(stints, pit_laps=..., pit_window=...)` or `plot_strategy_timeline_from_laps(laps, pit_stops, driver_filter=..., pit_window=...)`.

All plotting functions take data as arguments; no hardcoded race or driver. See `src/visualization/` and docstrings for parameters.

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/PRD.md](docs/PRD.md) | Product requirements, scope, and methodology. |
| [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) | Fuel model, clean-air assumption, dry-race scope, excluded features. |
| [docs/CASE_STUDIES.md](docs/CASE_STUDIES.md) | Selected races, inputs, model vs actual, outcome metrics, how to reproduce. |

---

## Contributing

Contributions are welcome. Keep behavior aligned with the PRD and document assumptions in `docs/ASSUMPTIONS.md`.

---

## License

Copyright © 2026 Hamna Nimra. All rights reserved.

This software and associated documentation files are proprietary. 
Unauthorized copying, modification, distribution, or use of this software via any medium is strictly prohibited.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
