"""
Train LSTM model for predictive maintenance.

Reads CSV from generate_training_data.py, creates sliding window sequences,
trains an LSTM, evaluates on a held-out test split, and saves the model.

Usage (run locally — requires tensorflow):
    pip install tensorflow numpy pandas scikit-learn
    python train_lstm.py --data ../data/motor_training.csv --epochs 30 --eval
"""

import argparse
import os

import numpy as np
import pandas as pd

SEQUENCE_LEN = 30   # 30 readings = 60 seconds of history
HORIZON = 10        # look ahead 10 readings (20 seconds)
T_WARNING = 85.0
N_FEATURES = 3      # temperature_norm, z_score, delta_norm


def create_sequences(temperatures: np.ndarray):
    """
    Convert flat temperature array into (X, y) for LSTM training.

    X shape: (n_samples, SEQUENCE_LEN, N_FEATURES)
    y shape: (n_samples,)

    Label = 1 (AT_RISK) when:
      - Current temperature is BELOW T_WARNING, AND
      - At least one of the next HORIZON readings crosses T_WARNING
    This predicts the *transition* from safe to danger — the core value
    of predictive maintenance.
    """
    n = len(temperatures)
    X, y = [], []

    for i in range(SEQUENCE_LEN, n - HORIZON):
        window = temperatures[i - SEQUENCE_LEN : i]
        future = temperatures[i : i + HORIZON]

        mean = window.mean()
        std = max(window.std(), 1e-6)

        features = []
        for j, temp in enumerate(window):
            t_norm = temp / 100.0
            z = (temp - mean) / std
            delta = (temp - window[j - 1]) / 10.0 if j > 0 else 0.0
            features.append([t_norm, z, delta])

        X.append(features)

        # Predict transition: safe now, danger ahead
        current_temp = window[-1]
        future_max = max(future)
        label = 1.0 if (current_temp < T_WARNING and future_max > T_WARNING) else 0.0
        y.append(label)

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def build_model():
    """Build the LSTM model as defined in the plan."""
    import tensorflow as tf

    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(64, input_shape=(SEQUENCE_LEN, N_FEATURES)),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy", tf.keras.metrics.AUC(name="auc")],
    )
    return model


def main():
    parser = argparse.ArgumentParser(description="Train LSTM predictive model")
    parser.add_argument("--data", required=True, help="Path to motor_training.csv")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--out", default="../models/lstm_motor.keras")
    parser.add_argument("--eval", action="store_true", help="Evaluate on test set")
    args = parser.parse_args()

    import tensorflow as tf

    # ── Load data ────────────────────────────────────────────────────
    print("Loading data...")
    df = pd.read_csv(args.data)
    temperatures = df["temperature"].values.astype(np.float32)

    print(f"Creating sequences (seq_len={SEQUENCE_LEN}, horizon={HORIZON})...")
    X, y = create_sequences(temperatures)

    pos_pct = 100 * y.mean()
    print(f"Dataset: {X.shape[0]} sequences")
    print(f"  Positive (at risk): {y.sum():.0f} ({pos_pct:.1f}%)")
    print(f"  Negative (safe):    {(1 - y).sum():.0f} ({100 - pos_pct:.1f}%)")

    # ── Train/test split ─────────────────────────────────────────────
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    print(f"\nTrain: {len(X_train)} | Test: {len(X_test)}")

    # ── Build and train ──────────────────────────────────────────────
    model = build_model()
    model.summary()

    # ── Class weights (moderate boost for minority class) ────────────
    # Cap at 3x to avoid over-predicting the minority class
    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    ratio = n_neg / max(n_pos, 1)
    capped_weight = min(ratio, 3.0)  # never more than 3x
    class_weight = {0: 1.0, 1: capped_weight}
    print(f"\nClass weights: SAFE=1.00, AT_RISK={capped_weight:.2f} (raw ratio: {ratio:.1f}x)")

    print("\nTraining...")
    model.fit(
        X_train, y_train,
        validation_split=0.15,
        epochs=args.epochs,
        batch_size=args.batch_size,
        class_weight=class_weight,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor="val_auc", patience=5, mode="max",
                restore_best_weights=True,
            ),
        ],
        verbose=1,
    )

    # ── Save model ───────────────────────────────────────────────────
    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    model.save(out_path)
    print(f"\nModel saved → {out_path}")

    # ── Evaluate ─────────────────────────────────────────────────────
    if args.eval:
        from sklearn.metrics import classification_report, roc_auc_score

        print("\n" + "=" * 60)
        print("EVALUATION ON TEST SET")
        print("=" * 60)

        results = model.evaluate(X_test, y_test, verbose=0)
        for name, value in zip(model.metrics_names, results):
            print(f"  {name}: {value:.4f}")

        y_proba = model.predict(X_test, verbose=0).flatten()

        auc = roc_auc_score(y_test, y_proba)
        print(f"\n  AUC-ROC: {auc:.4f}")

        # Evaluate at multiple thresholds to find best tradeoff
        print(f"\n  {'Thresh':>6}  {'Prec':>6}  {'Recall':>6}  {'F1':>6}  {'Acc':>6}")
        print(f"  {'------':>6}  {'------':>6}  {'------':>6}  {'------':>6}  {'------':>6}")

        best_f1, best_thresh = 0, 0.5
        for thresh in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
            y_pred = (y_proba > thresh).astype(int)
            tp = ((y_pred == 1) & (y_test == 1)).sum()
            fp = ((y_pred == 1) & (y_test == 0)).sum()
            fn = ((y_pred == 0) & (y_test == 1)).sum()
            prec = tp / max(tp + fp, 1)
            rec = tp / max(tp + fn, 1)
            f1 = 2 * prec * rec / max(prec + rec, 1e-9)
            acc = (y_pred == y_test).mean()
            marker = " <-- best" if f1 > best_f1 else ""
            if f1 > best_f1:
                best_f1, best_thresh = f1, thresh
            print(f"  {thresh:>6.1f}  {prec:>6.3f}  {rec:>6.3f}  {f1:>6.3f}  {acc:>6.3f}{marker}")

        print(f"\nBest threshold: {best_thresh} (F1={best_f1:.3f})")
        y_pred = (y_proba > best_thresh).astype(int)
        print(f"\n{classification_report(y_test, y_pred, target_names=['SAFE', 'AT_RISK'], zero_division=0)}")


if __name__ == "__main__":
    main()
