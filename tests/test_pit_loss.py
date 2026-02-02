"""Unit tests for pit loss (get_pit_loss, set_pit_loss_for_testing)."""

import pytest

from src.strategy.pit_loss import (
    DEFAULT_PIT_LOSS_SECONDS,
    get_pit_loss,
    set_pit_loss_for_testing,
)


def test_get_pit_loss_known_track():
    """Known track returns configured value (case-insensitive)."""
    assert get_pit_loss("Bahrain") == 21.5
    assert get_pit_loss("bahrain") == 21.5
    assert get_pit_loss("Monaco") == 19.0


def test_get_pit_loss_unknown_track_uses_default():
    """Unknown track returns DEFAULT_PIT_LOSS_SECONDS."""
    loss = get_pit_loss("UnknownTrackXYZ")
    assert loss == DEFAULT_PIT_LOSS_SECONDS


def test_get_pit_loss_override_default():
    """default= overrides built-in default for unknown track."""
    assert get_pit_loss("UnknownTrack", default=25.0) == 25.0


def test_get_pit_loss_overrides_take_precedence():
    """overrides= takes precedence over built-in config."""
    overrides = set_pit_loss_for_testing("Bahrain", 18.0)
    assert get_pit_loss("Bahrain", overrides=overrides) == 18.0
    assert get_pit_loss("Bahrain") == 21.5  # unchanged without overrides


def test_set_pit_loss_for_testing_returns_dict():
    """set_pit_loss_for_testing returns dict usable as overrides."""
    ov = set_pit_loss_for_testing("TestTrack", 20.0)
    assert isinstance(ov, dict)
    assert "testtrack" in ov or "TestTrack" in ov
    assert get_pit_loss("TestTrack", overrides=ov) == 20.0
