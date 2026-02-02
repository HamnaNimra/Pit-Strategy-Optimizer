# Product Requirements Document
## Motorsports Pit Strategy Optimizer

---

## 1. Overview

**Product Name:** Motorsports Pit Strategy Optimizer

**Purpose**
The Motorsports Pit Strategy Optimizer is a decision-support system designed to evaluate and recommend optimal pit stop windows during motorsports races, with an initial focus on Formula 1. The system models tire degradation, pit stop time loss, and race context to assess strategic trade-offs and compare modeled recommendations against historical race outcomes.

The goal is not to perfectly predict race results, but to build a transparent, explainable framework for analyzing pit strategy decisions using publicly available race data.

**Target Users**
- Motorsports enthusiasts and analysts interested in race strategy
- Engineers and analysts exploring performance modeling and optimization
- Portfolio reviewers evaluating applied data modeling and systems thinking

---

## 2. Problem Definition

Pit strategy is one of the most influential factors in race outcomes. Teams must continuously balance:

- Tire performance degradation over a stint
- Time lost in the pit lane (typically ~20–25 seconds)
- Track position and overtaking difficulty
- Relative pace and proximity of competitors
- Changing race conditions such as weather or safety cars

While professional teams rely on proprietary tools and live simulations, publicly available tools often focus on visualization rather than predictive or evaluative strategy modeling. This project aims to bridge that gap by demonstrating how strategic decisions can be modeled, evaluated, and validated using real race data.

---

## 3. Project Goals

### Primary Goals
- Build a functional tire degradation model with reasonable predictive accuracy
- Estimate optimal pit stop windows under different race scenarios
- Validate modeled recommendations against real historical team decisions

### Secondary Goals
- Provide clear explanations for strategy recommendations
- Visualize how degradation and pit timing impact race outcomes
- Create a reproducible framework suitable for extension and analysis

---

## 4. Strategy Modeling Approach

The system evaluates pit strategy as a trade-off between short-term time loss (pit stop) and long-term time gain (fresher tires). Strategy recommendations are produced by simulating alternative pit timing scenarios and comparing total projected race time under each option.

Key principles:
- Deterministic, explainable modeling over black-box prediction
- Explicit assumptions and documented limitations
- Historical validation to measure alignment with real decisions

---

## 5. Data Sources and Pipeline

### Data Sources
All race data is sourced from the FastF1 Python library, which provides access to publicly available Formula 1 timing and telemetry data.

Available inputs include:
- Lap times for all drivers
- Sector times
- Tire compounds and stint information
- Pit stop timing and duration
- Basic telemetry (speed, throttle, braking, gear, DRS)
- Weather data (track and air temperature)

### Data Pipeline
- Race sessions are loaded on demand
- Relevant fields are extracted and normalized into structured datasets
- Derived features are computed and cached locally to avoid repeated processing

---

## 6. Tire Degradation Modeling

### Description
The tire degradation model estimates lap time evolution over a stint as tires age.

### Inputs
- Tire compound (Soft, Medium, Hard)
- Track identifier
- Lap number within the stint
- Track temperature
- Estimated fuel load (derived from lap number)

### Outputs
- Predicted lap time
- Degradation rate (seconds per lap)
- Identification of potential performance "cliff" points

### MVP Modeling Approach
- Linear regression per track and compound
- Optional normalization for temperature and fuel load
- Focus on dry race conditions only

More complex non-linear models may be explored post-MVP.

---

## 7. Pit Window Optimization Engine

### Description
The pit window optimizer evaluates multiple pit timing scenarios and ranks them based on projected total race time.

### Inputs
- Current lap number
- Current tire compound and age
- Remaining race distance
- Track-specific pit stop time loss
- Available tire compounds

### Outputs
- Recommended pit lap or pit window
- Ranked alternative strategies
- Time deltas between strategies

### Core Logic
- Simulate pitting on the current lap and on subsequent laps within a defined window
- Apply pit loss and projected post-pit degradation
- Compare cumulative race time outcomes

---

## 8. Strategy Explanation Layer

For each recommendation, the system provides a short, human-readable explanation describing:
- Why the pit window opens at a given point
- How degradation overtakes pit loss
- The cost of delaying or advancing the stop

This explanation is derived directly from intermediate calculations and is fully deterministic.

---

## 9. Validation Methodology

### Historical Validation
The system is evaluated against historical races by comparing:
- Modeled optimal pit timing
- Actual pit timing chosen by teams

### Metrics
- Lap delta between recommendation and actual decision
- Percentage of decisions falling within an acceptable window (±3 laps)
- Aggregate alignment rate across multiple races

Validation focuses on clean, dry races to reduce confounding variables.

---

## 10. Visualization and Analysis

The project includes visual outputs to support interpretation and storytelling:

- Predicted vs actual lap time curves
- Tire degradation profiles by compound
- Stint-by-stint comparisons across drivers
- Strategy timelines showing pit windows and position changes

Visualizations are designed to be understandable by both technical and non-technical audiences.

---

## 11. MVP Scope

### Included
- Single-car strategy optimization
- Dry race conditions only
- Linear degradation models
- Historical validation on a limited race set

### Excluded
- Safety car or virtual safety car modeling
- Traffic and multi-car interactions
- Driver-specific pace modeling beyond lap time trends
- Real-time live race integration
- Wet and intermediate tires are excluded from the MVP. (This project models dry-weather (slick) tires at the compound level (Soft, Medium, Hard).)

---

## 12. Post-MVP Enhancements

Potential future extensions include:
1. Temperature-adjusted degradation modeling
2. Safety car probability and impact modeling
3. Undercut and overcut interaction modeling
4. Multi-stop and multi-compound optimization
5. Web-based interface for broader accessibility
6. Live race strategy simulation

---

## 13. Assumptions and Limitations

- Fuel load is estimated using a simplified linear model
- Clean-air lap time is assumed in the MVP
- Strategy recommendations are advisory, not predictive
- Results may diverge in races with unusual conditions or disruptions

All assumptions are explicitly documented and revisited as the model evolves.

---

## 14. Success Criteria

The project is considered successful if it:
- Produces strategy recommendations that align with real decisions at a meaningful rate
- Clearly explains why recommendations are made
- Demonstrates disciplined scope control and modeling trade-offs
- Serves as a strong example of applied performance and strategy analysis

---

## 15. Phases and Milestones

- Phase 1: Data acquisition and degradation modeling
- Phase 2: Pit strategy optimization logic
- Phase 3: Validation and visualization
- Phase 4: Documentation, polish, and case studies

**Target Completion:** Early March 2026

---

## 16. How to Run

- **CLI:** `python run_strategy.py --year <YEAR> --race <RACE> --driver <DRIVER>` (optional: `--lap`, `--new-compound`). Loads race data, ensures degradation models are fitted for the track/compounds (fitting from race data if missing), runs the optimizer, and prints recommendation and explanation.
- **Validation:** Use `run_validation(races, degradation_model=model)` and `save_validation_results` / `load_validation_results` (see [CASE_STUDIES.md](CASE_STUDIES.md)).

---

## 17. Final Repo Structure

```
pit-strategy-optimizer/
├── README.md
├── requirements.txt
├── run_strategy.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── cache/
│
├── src/
│   ├── data_pipeline/
│   │   ├── __init__.py
│   │   ├── load_race.py
│   │   ├── preprocess.py
│   │   └── stint_features.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tire_degradation.py
│   │   └── diagnostics.py
│   │
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── pit_loss.py
│   │   ├── optimizer.py
│   │   └── explanation.py
│   │
│   ├── validation/
│   │   ├── __init__.py
│   │   └── historical_validation.py
│   │
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── degradation_plots.py
│   │   └── strategy_plots.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── config.py
│
├── notebooks/
│   └── exploratory_analysis.ipynb
│
├── docs/
│   ├── PRD.md
│   ├── ASSUMPTIONS.md
│   └── CASE_STUDIES.md
│
└── tests/
    ├── conftest.py
    ├── test_data_pipeline.py
    ├── test_degradation_model.py
    ├── test_explanation.py
    ├── test_integration.py
    ├── test_optimizer.py
    ├── test_pit_loss.py
    ├── test_preprocess.py
    └── test_stint_features.py
```
