# Case Studies

Reproducible race case studies for the pit strategy optimizer. Each study uses the same pipeline: load dry-race data, run the optimizer at each real pit decision point, compare recommended vs actual pit lap, and report lap delta and alignment. No speculation or hype; results are from intermediate calculations only.

---

## Selected Races

The following races are used for case studies. All are run as dry sessions (wet races are excluded by `load_race`).

| Year | Race        | Notes                    |
|------|-------------|--------------------------|
| 2023 | Bahrain     | Season opener, dry       |
| 2023 | Spain       | Dry                      |
| 2023 | Monaco      | Dry                      |
| 2023 | Silverstone | Dry                      |
| 2023 | Monza       | Dry                      |

Races are specified as `(year, race_name)` for `load_race` and `run_validation`. Race names match FastF1 event names (e.g. "Bahrain", "Spanish Grand Prix" or "Spain").

---

## Inputs

For each race the pipeline uses:

1. **Race data**  
   - From `load_race(year, race_name)`: `laps`, `pit_stops`, `weather`.  
   - Dry races only; wet sessions raise and are skipped.

2. **Stint features**  
   - From `add_stint_features(laps, pit_stops)`: `lap_in_stint`, `stint_id`, `estimated_fuel_kg` added to laps.

3. **Per decision point (each pit stop)**  
   - `current_lap`: lap number at which the driver pitted (decision point = start of that lap).  
   - `current_compound`: compound on that lap (from laps).  
   - `lap_in_stint`: laps on that tyre set (from laps with stint features).  
   - `total_race_laps`: max lap number in laps for that race.  
   - `track_id`: race name (e.g. "Bahrain").  
   - `new_compound`: compound fitted at the stop (from pit_stops).

4. **Model**  
   - Fitted `TireDegradationModel` for the relevant track and compounds (SOFT, MEDIUM, HARD).  
   - Pit loss from `get_pit_loss(track_id)`.

---

## Model Recommendation

For each decision point the optimizer:

1. Runs `optimize_pit_window(current_lap, current_compound, lap_in_stint, total_race_laps, track_id, new_compound, ...)`.  
2. Takes the best strategy from the result DataFrame (rank 1).  
3. Reads `recommended_pit_lap(results)`: either a lap number (pit on that lap) or `None` (stay out).

Recommendation is stored per row in the validation details as `recommended_pit_lap`.

---

## Actual Team Decision

Actual pit lap is taken from the pit_stops DataFrame: for each pit stop, `LapNumber` is the lap on which the driver entered the pit (in-lap). That value is recorded as `actual_pit_lap` in the validation details.

No interpretation of team intent; the recorded decision is the lap number of the pit stop.

---

## Outcome Differences

For each decision:

- **Lap delta** = `recommended_pit_lap - actual_pit_lap` when the model recommends a lap (integer). If the model recommends stay-out, `lap_delta` is not defined (stored as missing).
- **Alignment within ±3 laps** = `True` when `recommended_pit_lap` is not missing and `|lap_delta| ≤ 3`. If the model recommended stay-out and the team pitted, alignment is `False`.

Aggregate metrics (from `run_validation` summary):

- **total_decisions**: number of pit decisions evaluated.  
- **count_within_3**: number of decisions with alignment within ±3 laps.  
- **pct_within_3**: 100 × count_within_3 / valid_decisions.  
- **mean_abs_lap_delta**: mean of |lap_delta| over decisions with a numeric delta.  
- **count_errors**: number of decision points where the optimizer raised (e.g. missing model).

---

## Per-Race Summary Table (Template)

After running validation, fill or replace with actual outputs. One row per race; metrics can be aggregated from validation details filtered by `track_id` and `year`.

| Year | Track     | Decisions | Within ±3 | Mean |Δ| (laps) |
|------|-----------|-----------|-----------|------------------|
| 2023 | Bahrain   | —         | —         | —                |
| 2023 | Spain     | —         | —         | —                |
| 2023 | Monaco    | —         | —         | —                |
| 2023 | Silverstone | —       | —         | —                |
| 2023 | Monza     | —         | —         | —                |

---

## Example Decision-Level Table (Template)

After running validation, the details DataFrame has one row per pit decision. Example columns (actual numbers from a run):

| year | track_id | driver_number | actual_pit_lap | recommended_pit_lap | lap_delta | alignment_within_3 | current_compound | new_compound |
|------|----------|---------------|----------------|--------------------|-----------|--------------------|------------------|--------------|
| 2023 | Bahrain  | 1             | 28             | 27                 | -1        | True               | SOFT             | MEDIUM       |
| …    | …        | …             | …              | …                  | …         | …                  | …                | …            |

---

## How to Reproduce

1. **Environment**  
   Install dependencies from `requirements.txt` (FastF1, pandas, numpy, scikit-learn, joblib, matplotlib, plotly).

2. **Fit degradation models**  
   For each track and compound used in the selected races, fit the tire degradation model on lap data (e.g. from the same year or a prior year). Save models so validation can load them.

   ```python
   from src.data_pipeline import load_race, add_stint_features
   from src.models import TireDegradationModel

   model = TireDegradationModel()
   for year, name in [(2023, "Bahrain"), (2023, "Spain"), ...]:
       data = load_race(year, name)
       laps = add_stint_features(data.laps, data.pit_stops)
       for comp in ["SOFT", "MEDIUM", "HARD"]:
           model.fit(laps, track_id=name, compound=comp)
   model.save()
   ```

3. **Run validation**  
   Call `run_validation` with the selected races and the fitted model. Save results.

   ```python
   from src.validation import run_validation, save_validation_results
   from src.models import TireDegradationModel

   model = TireDegradationModel()
   model.load()
   races = [(2023, "Bahrain"), (2023, "Spain"), (2023, "Monaco"), (2023, "Silverstone"), (2023, "Monza")]
   details, summary = run_validation(races, degradation_model=model)
   save_validation_results(details, summary)
   ```

4. **Inspect results**  
   - `details`: one row per pit decision (columns above).  
   - `summary`: `total_decisions`, `count_within_3`, `pct_within_3`, `mean_abs_lap_delta`, `count_errors`.  
   - Filter `details` by `year` and `track_id` to build per-race summaries for the case study tables.

5. **Optional: load saved results**  
   ```python
   from src.validation import load_validation_results
   details, summary = load_validation_results()
   ```

---

## Validation Results (Summary)

After a full run, paste or summarize the contents of `validation_summary.txt` here, for example:

```
total_decisions: ...
count_within_3: ...
pct_within_3: ...
mean_abs_lap_delta: ...
count_errors: ...
```

---

## Strategy Comparisons

To compare strategies across drivers or races:

- Use the same `details` DataFrame; group by `track_id` and `year` (and optionally `driver_number`) to compute per-race or per-driver alignment and mean |lap_delta|.  
- Use visualization: `plot_strategy_timeline_from_laps(laps, pit_stops, driver_filter=...)` and `plot_predicted_vs_actual_from_laps(...)` for chosen drivers.  
- No extra logic is required; comparisons are based on the same validation outputs and optional filtering.
