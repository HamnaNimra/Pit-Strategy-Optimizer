"""Configuration and constants for the pit strategy optimizer."""

from pathlib import Path

# Project root: directory containing run_strategy.py (two levels up from src/utils/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Data directories
DATA_DIR = _PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CACHE_DIR = DATA_DIR / "cache"

# FastF1 API cache (raw API responses)
FASTF1_CACHE_DIR = CACHE_DIR / "fastf1"

# Processed race data cache (extracted DataFrames)
PROCESSED_RACES_DIR = CACHE_DIR / "processed_races"

# Dry races only: wet sessions are rejected
SLICK_COMPOUNDS = frozenset({"SOFT", "MEDIUM", "HARD"})

# Persisted models (e.g. tire degradation per track/compound)
MODELS_DIR = CACHE_DIR / "models"
DEGRADATION_MODELS_DIR = MODELS_DIR / "degradation"

# Validation outputs (historical comparison results)
VALIDATION_RESULTS_DIR = DATA_DIR / "processed" / "validation"

# Exported visualizations (case study plots: PNG, HTML)
FIGURES_DIR = DATA_DIR / "processed" / "figures"

# Uncertainty-aware recommendation (pit window, sensitivity, VSC)
PIT_WINDOW_WITHIN_SEC = 2.0
DEGRADATION_SENSITIVITY_DELTA_SEC_PER_LAP = 0.02
VSC_PIT_LOSS_FACTOR = 0.5
