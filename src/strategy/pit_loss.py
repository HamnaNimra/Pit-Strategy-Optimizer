"""Track-specific pit stop time loss.

Configuration mapping tracks to pit loss (seconds). Strategy logic should use
get_pit_loss(track_name) instead of hard-coded constants. Overrides supported
for testing.
"""

from __future__ import annotations

# Default pit loss when track is not in config (typical F1 ~20–25 s)
DEFAULT_PIT_LOSS_SECONDS = 22.0

# Track-specific pit loss (seconds). Keys normalized to lowercase for lookup.
# Add or override entries as needed; strategy code uses get_pit_loss(), not this dict.
TRACK_PIT_LOSS_SECONDS: dict[str, float] = {
    "bahrain": 21.5,
    "monaco": 19.0,
    "monza": 22.5,
    "singapore": 24.0,
    "spa": 22.0,
    "silverstone": 22.0,
    "barcelona": 21.5,
    "hungaroring": 21.0,
    "suzuka": 22.5,
    "americas": 22.0,
    "red bull ring": 21.0,
    "zandvoort": 21.5,
    "marina bay": 24.0,
    "losail": 22.0,
    "jeddah": 22.5,
    "abu dhabi": 22.0,
    "miami": 22.0,
    "las vegas": 22.5,
    "imola": 21.5,
    "portimão": 21.5,
    "istanbul": 22.0,
    "sochi": 22.0,
    "shanghai": 22.0,
    "melbourne": 22.0,
    "montreal": 22.0,
    "baku": 21.5,
    "france": 22.0,
    "austria": 21.0,
    "great britain": 22.0,
    "germany": 22.0,
    "italy": 22.5,
    "russia": 22.0,
    "turkey": 22.0,
    "japan": 22.5,
    "mexico": 22.0,
    "brazil": 22.0,
    "qatar": 22.0,
    "saudi arabia": 22.5,
    "netherlands": 21.5,
    "emilia romagna": 21.5,
    "portugal": 21.5,
    "china": 22.0,
    "united states": 22.0,
}


def _normalize_track(track_name: str) -> str:
    """Normalize track name for config lookup (strip, lowercase)."""
    return (track_name or "").strip().lower()


def get_pit_loss(
    track_name: str,
    *,
    default: float | None = None,
    overrides: dict[str, float] | None = None,
) -> float:
    """
    Return track-specific pit loss in seconds.

    Lookup order: overrides (for testing) → TRACK_PIT_LOSS_SECONDS →
    default argument → DEFAULT_PIT_LOSS_SECONDS. Track name is normalized
    (strip, lowercase) before lookup.

    Parameters
    ----------
    track_name : str
        Track identifier (e.g. "Bahrain", "Monaco"). Case-insensitive.
    default : float, optional
        Fallback when track is not in config. If None, use DEFAULT_PIT_LOSS_SECONDS.
    overrides : dict[str, float], optional
        Optional mapping (track_name_normalized -> seconds). Takes precedence over
        built-in config. Use for testing or one-off overrides.

    Returns
    -------
    float
        Pit loss in seconds (time lost relative to staying on track).
    """
    key = _normalize_track(track_name)
    if overrides and key in overrides:
        return float(overrides[key])
    if key in TRACK_PIT_LOSS_SECONDS:
        return TRACK_PIT_LOSS_SECONDS[key]
    if default is not None:
        return float(default)
    return DEFAULT_PIT_LOSS_SECONDS


def set_pit_loss_for_testing(
    track_name: str,
    seconds: float,
    *,
    _overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    """
    Return a dict suitable for get_pit_loss(..., overrides=...) for testing.

    Does not mutate global config. Usage:
        overrides = set_pit_loss_for_testing("TestTrack", 18.0)
        loss = get_pit_loss("TestTrack", overrides=overrides)

    Parameters
    ----------
    track_name : str
        Track to override.
    seconds : float
        Pit loss in seconds.
    _overrides : dict, optional
        If provided, this dict is updated and returned (for chaining).

    Returns
    -------
    dict[str, float]
        Overrides dict to pass to get_pit_loss(..., overrides=...).
    """
    out = dict(_overrides) if _overrides is not None else {}
    out[_normalize_track(track_name)] = float(seconds)
    return out
