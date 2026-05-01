"""Unit tests for predictive.baseline_model"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from predictive.buffer import SlidingBuffer
from predictive.baseline_model import predict


def _fill_buffer(values):
    """Helper: create a buffer and fill it with values."""
    buf = SlidingBuffer(maxlen=30)
    for v in values:
        buf.append(v)
    return buf


def test_too_few_readings():
    buf = _fill_buffer([70.0, 71.0])
    result = predict(buf)
    assert result["risk_score"] == 0.0
    assert result["eta_minutes"] is None
    assert result["model"] == "baseline"


def test_flat_temperature():
    """Constant temperature → no risk, no ETA."""
    buf = _fill_buffer([70.0] * 15)
    result = predict(buf)
    assert result["risk_score"] == 0.0
    assert result["eta_minutes"] is None


def test_falling_temperature():
    """Falling temperature → risk_score = 0, no ETA."""
    values = [80.0 - i * 0.5 for i in range(15)]
    buf = _fill_buffer(values)
    result = predict(buf)
    assert result["risk_score"] == 0.0
    assert result["eta_minutes"] is None


def test_rising_temperature():
    """Steadily rising temperature → positive risk_score and finite ETA."""
    values = [65.0 + i * 1.0 for i in range(15)]  # 65, 66, ..., 79
    buf = _fill_buffer(values)
    result = predict(buf)
    assert result["risk_score"] > 0.0
    assert result["eta_minutes"] is not None
    assert result["eta_minutes"] > 0


def test_risk_score_bounded():
    """risk_score should always be in [0, 1]."""
    # Extreme rising: 0, 10, 20, ... (slope = 10, way above MAX_SLOPE)
    values = [i * 10.0 for i in range(10)]
    buf = _fill_buffer(values)
    result = predict(buf)
    assert 0.0 <= result["risk_score"] <= 1.0


def test_already_above_warning():
    """If current temp is above T_WARNING, eta should be None."""
    values = [90.0 + i * 0.5 for i in range(10)]  # already above 85°C
    buf = _fill_buffer(values)
    result = predict(buf)
    # Rising but already above threshold — no eta
    assert result["eta_minutes"] is None


def test_output_keys():
    """Every prediction must contain the three expected keys."""
    buf = _fill_buffer([70.0] * 10)
    result = predict(buf)
    assert "risk_score" in result
    assert "eta_minutes" in result
    assert "model" in result
