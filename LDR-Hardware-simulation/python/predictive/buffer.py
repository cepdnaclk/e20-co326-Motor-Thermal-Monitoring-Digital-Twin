"""
Sliding buffer for temperature readings.

A thin wrapper around collections.deque that adds a `latest(n)` method
for extracting the most recent N values as a list — used by feature
extraction and model inference.
"""

from collections import deque


class SlidingBuffer:
    """Fixed-size sliding window of float values."""

    def __init__(self, maxlen: int = 30):
        self._buf: deque = deque(maxlen=maxlen)

    def append(self, value: float) -> None:
        """Add a new reading to the buffer."""
        self._buf.append(float(value))

    def latest(self, n: int | None = None) -> list[float]:
        """
        Return the most recent `n` values as a plain list.
        If n is None or larger than the current buffer size,
        returns all available values.
        """
        if n is None or n >= len(self._buf):
            return list(self._buf)
        return list(self._buf)[-n:]

    def __len__(self) -> int:
        return len(self._buf)

    def __repr__(self) -> str:
        return f"SlidingBuffer(len={len(self._buf)}, maxlen={self._buf.maxlen})"
