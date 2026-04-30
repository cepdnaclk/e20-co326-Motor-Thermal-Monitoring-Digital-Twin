"""Unit tests for predictive.features"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from predictive.features import extract_slope, extract_rolling_stats


# ── extract_slope tests ─────────────────────────────────────────────

def test_slope_rising():
    # Perfectly linear: 0, 1, 2, 3, 4 → slope = 1.0
    readings = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    slope = extract_slope(readings)
    assert abs(slope - 1.0) < 1e-9


def test_slope_falling():
    # 4, 3, 2, 1, 0 → slope = -1.0
    readings = np.array([4.0, 3.0, 2.0, 1.0, 0.0])
    slope = extract_slope(readings)
    assert abs(slope - (-1.0)) < 1e-9


def test_slope_flat():
    readings = np.array([5.0, 5.0, 5.0, 5.0])
    slope = extract_slope(readings)
    assert abs(slope) < 1e-9


def test_slope_single_reading():
    readings = np.array([42.0])
    slope = extract_slope(readings)
    assert slope == 0.0


def test_slope_empty():
    readings = np.array([])
    slope = extract_slope(readings)
    assert slope == 0.0


def test_slope_two_readings():
    readings = np.array([10.0, 15.0])
    slope = extract_slope(readings)
    assert abs(slope - 5.0) < 1e-9


def test_slope_noisy_but_rising():
    # General upward trend with noise
    readings = np.array([10.0, 12.0, 11.5, 14.0, 13.5, 16.0])
    slope = extract_slope(readings)
    assert slope > 0


# ── extract_rolling_stats tests ──────────────────────────────────────

def test_stats_basic():
    readings = np.array([10.0, 20.0, 30.0])
    stats = extract_rolling_stats(readings)
    assert abs(stats["mean"] - 20.0) < 1e-9
    assert abs(stats["min"] - 10.0) < 1e-9
    assert abs(stats["max"] - 30.0) < 1e-9
    assert abs(stats["delta"] - 20.0) < 1e-9
    assert stats["std"] > 0


def test_stats_empty():
    readings = np.array([])
    stats = extract_rolling_stats(readings)
    assert stats["mean"] == 0.0
    assert stats["std"] == 0.0


def test_stats_single():
    readings = np.array([42.0])
    stats = extract_rolling_stats(readings)
    assert stats["mean"] == 42.0
    assert stats["std"] == 0.0
    assert stats["delta"] == 0.0
