"""
Generate synthetic motor temperature data for LSTM training.

Uses regime-based sampling (inspired by ml/base.py) with STICKY regimes —
the motor stays in one state for 30-100 readings before potentially switching.
This creates realistic sustained normal/anomaly episodes.

Usage (run locally):
    python generate_training_data.py --steps 100000 --out ../data/motor_training.csv
"""

import argparse
import csv
import os

import numpy as np


T_WARNING = 85.0
T_CRITICAL = 90.0

# Temperature regimes — adapted from ml/base.py
REGIMES = [
    (77.0, 3.0, "NORMAL",   0.65),
    (87.0, 2.0, "WARNING",  0.20),
    (93.0, 1.5, "CRITICAL", 0.15),
]


def simulate(n_steps: int, seed: int = 42) -> list[dict]:
    """
    Generate sequential temperature readings with sticky regime episodes.

    Each regime persists for 30-100 readings before switching, creating
    realistic sustained normal/anomaly periods with clear transitions.
    """
    rng = np.random.default_rng(seed)
    probs = [r[3] for r in REGIMES]

    readings = []
    current_temp = 77.0
    smoothing = 0.3

    # Sticky regime state
    regime_idx = 0
    regime_remaining = 0

    for step in range(n_steps):
        # Switch regime when current episode ends
        if regime_remaining <= 0:
            regime_idx = rng.choice(len(REGIMES), p=probs)
            regime_remaining = int(rng.integers(30, 100))

        regime_remaining -= 1
        target_temp, sigma, _, _ = REGIMES[regime_idx]

        # Smooth transition toward the target regime
        target_sample = float(rng.normal(target_temp, sigma))
        current_temp = (1 - smoothing) * target_sample + smoothing * current_temp

        # Label based on actual temperature
        if current_temp >= T_CRITICAL:
            anomaly_type = "CRITICAL"
        elif current_temp >= T_WARNING:
            anomaly_type = "WARNING"
        else:
            anomaly_type = "NORMAL"

        readings.append({
            "step": step,
            "temperature": round(current_temp, 4),
            "fan_state": "ON" if current_temp > T_WARNING else "OFF",
            "anomaly_type": anomaly_type,
        })

    return readings


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic motor data")
    parser.add_argument("--steps", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="../data/motor_training.csv")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    print(f"Simulating {args.steps} steps (seed={args.seed})...")
    readings = simulate(args.steps, args.seed)

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["step", "temperature", "fan_state", "anomaly_type"])
        writer.writeheader()
        writer.writerows(readings)

    temps = [r["temperature"] for r in readings]
    n_warn = sum(1 for r in readings if r["temperature"] > T_WARNING)
    n_crit = sum(1 for r in readings if r["temperature"] > T_CRITICAL)

    print(f"Saved {len(readings)} readings -> {args.out}")
    print(f"Range: {min(temps):.1f} - {max(temps):.1f} C")
    print(f"Above WARNING (85 C): {n_warn} ({100*n_warn/len(readings):.1f}%)")
    print(f"Above CRITICAL (90 C): {n_crit} ({100*n_crit/len(readings):.1f}%)")


if __name__ == "__main__":
    main()
