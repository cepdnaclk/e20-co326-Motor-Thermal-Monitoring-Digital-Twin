"""Unit tests for predictive.buffer.SlidingBuffer"""

import sys
import os

# Add python dir to path so we can import predictive
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from predictive.buffer import SlidingBuffer


def test_append_and_len():
    buf = SlidingBuffer(maxlen=5)
    assert len(buf) == 0
    buf.append(10.0)
    buf.append(20.0)
    assert len(buf) == 2


def test_maxlen_enforced():
    buf = SlidingBuffer(maxlen=3)
    for v in [1, 2, 3, 4, 5]:
        buf.append(v)
    assert len(buf) == 3
    # Oldest values should have been dropped
    assert buf.latest() == [3.0, 4.0, 5.0]


def test_latest_all():
    buf = SlidingBuffer(maxlen=10)
    for v in [10, 20, 30]:
        buf.append(v)
    assert buf.latest() == [10.0, 20.0, 30.0]


def test_latest_n():
    buf = SlidingBuffer(maxlen=10)
    for v in [10, 20, 30, 40, 50]:
        buf.append(v)
    assert buf.latest(3) == [30.0, 40.0, 50.0]
    assert buf.latest(1) == [50.0]


def test_latest_n_larger_than_buffer():
    buf = SlidingBuffer(maxlen=10)
    buf.append(42.0)
    # Requesting more than available should return all
    assert buf.latest(100) == [42.0]


def test_latest_none():
    buf = SlidingBuffer(maxlen=10)
    for v in [1, 2, 3]:
        buf.append(v)
    assert buf.latest(None) == [1.0, 2.0, 3.0]


def test_values_are_floats():
    buf = SlidingBuffer(maxlen=5)
    buf.append(10)       # int
    buf.append("20.5")   # string — should be coerced
    values = buf.latest()
    assert all(isinstance(v, float) for v in values)
    assert values == [10.0, 20.5]


def test_repr():
    buf = SlidingBuffer(maxlen=5)
    buf.append(1)
    assert "len=1" in repr(buf)
    assert "maxlen=5" in repr(buf)
