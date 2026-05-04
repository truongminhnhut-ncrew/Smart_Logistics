"""
train_lstm.py — Generate synthetic delivery data & train LSTM model.

Usage:
    cd Smart_Logistics
    python -m backend.app.application.services.train_lstm

Output:
    backend/app/application/services/models/lstm_eta.pt   (TorchScript model)
    backend/app/application/services/models/scaler.json   (normalization params)
"""

import json
import math
import os
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# ── Constants ─────────────────────────────────────────────
SEQUENCE_LENGTH = 5          # 5-tick sliding window
NUM_FEATURES = 6             # speed, distance, incident, sin_hour, cos_hour, traffic
NUM_OUTPUTS = 4              # eta_min, delay_min, confidence, can_continue (0/1)
NUM_SAMPLES = 20000          # synthetic training samples
HIDDEN_SIZE = 64
NUM_LAYERS = 2
EPOCHS = 50
BATCH_SIZE = 128
LEARNING_RATE = 0.001
MODEL_DIR = Path(__file__).parent / "models"


# ── LSTM Model Definition ────────────────────────────────
class DeliveryLSTM(nn.Module):
    """
    LSTM model for ETA & delay prediction.

    Input:  (batch, seq_len=5, features=6)
    Output: (batch, 4) → [eta_min, delay_min, confidence, can_continue]
    """

    def __init__(self, input_size=NUM_FEATURES, hidden_size=HIDDEN_SIZE,
                 num_layers=NUM_LAYERS, output_size=NUM_OUTPUTS):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0.0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, output_size),
        )

    def forward(self, x):
        # x: (batch, seq_len, features)
        lstm_out, _ = self.lstm(x)
        last_hidden = lstm_out[:, -1, :]  # take last time step
        out = self.fc(last_hidden)
        # Ensure positive outputs for eta/delay, sigmoid for confidence & can_continue
        eta = torch.relu(out[:, 0:1]) + 0.1        # min 0.1 min
        delay = torch.relu(out[:, 1:2])              # >= 0
        confidence = torch.sigmoid(out[:, 2:3])      # [0,1]
        can_continue = torch.sigmoid(out[:, 3:4])    # [0,1]
        return torch.cat([eta, delay, confidence, can_continue], dim=1)


# ── Synthetic Data Generation ─────────────────────────────
def generate_synthetic_data(num_samples: int = NUM_SAMPLES):
    """
    Generate synthetic delivery tracking data simulating HCMC conditions.

    Each sample = 5-tick sequence of (speed, distance, incident, sin_h, cos_h, traffic)
    Labels = (eta_minutes, delay_minutes, confidence, can_continue)
    """
    X_all = []
    y_all = []

    for _ in range(num_samples):
        # Random scenario parameters
        hour = random.randint(0, 23)
        sin_h = math.sin(2 * math.pi * hour / 24)
        cos_h = math.cos(2 * math.pi * hour / 24)

        # Peak hour factor
        is_peak = hour in range(7, 10) or hour in range(17, 20)
        peak_factor = random.uniform(1.3, 1.8) if is_peak else 1.0

        # Base speed (HCMC city)
        base_speed = random.uniform(15, 40)  # km/h
        traffic_factor = random.uniform(0.8, 2.5)

        # Incident
        has_incident = random.random() < 0.25  # 25% chance
        incident_flag = 1.0 if has_incident else 0.0

        # Distance remaining
        distance_km = random.uniform(0.5, 15.0)

        # Generate 5-tick speed sequence with some variation
        speeds = []
        current_speed = base_speed / (traffic_factor * peak_factor)
        if has_incident:
            # Incidents cause speed drops
            incident_severity = random.choice([0.3, 0.5, 0.7])
            current_speed *= incident_severity

        for t in range(SEQUENCE_LENGTH):
            noise = random.uniform(-3, 3)
            s = max(1.0, current_speed + noise)
            speeds.append(s)

        # Build sequence features
        sequence = []
        for t in range(SEQUENCE_LENGTH):
            # Distance decreases slightly over ticks
            d = distance_km - (t * speeds[t] / 3600)  # speed in km/h, tick = 1 second
            d = max(0.1, d)
            sequence.append([
                speeds[t],
                d,
                incident_flag,
                sin_h,
                cos_h,
                traffic_factor,
            ])

        # Calculate ground truth ETA
        avg_speed = max(3.0, np.mean(speeds))
        effective_speed = avg_speed  # already adjusted for traffic + incident
        raw_eta = (distance_km / effective_speed) * 60  # minutes

        # SLA baseline
        sla_speed = 25.0  # average expected
        sla_eta = (distance_km / sla_speed) * 60
        delay = max(0.0, raw_eta - sla_eta)

        # Additional delay from incidents
        if has_incident:
            incident_delay = random.uniform(5, 25)
            delay += incident_delay
            raw_eta += incident_delay

        # Add noise to simulate real-world variance
        raw_eta += random.gauss(0, raw_eta * 0.05)
        raw_eta = max(0.5, raw_eta)
        delay = max(0.0, delay + random.gauss(0, 1.0))

        # Confidence
        confidence = 0.92
        if has_incident:
            confidence -= random.uniform(0.15, 0.30)
        if traffic_factor > 1.5:
            confidence -= random.uniform(0.05, 0.15)
        confidence = max(0.35, min(0.98, confidence + random.gauss(0, 0.03)))

        # Can continue: 0 if severe incident + very slow
        can_continue = 1.0
        if has_incident and avg_speed < 5.0:
            can_continue = 0.0
        elif has_incident and avg_speed < 10.0:
            can_continue = random.choice([0.0, 1.0])

        X_all.append(sequence)
        y_all.append([raw_eta, delay, confidence, can_continue])

    return np.array(X_all, dtype=np.float32), np.array(y_all, dtype=np.float32)


def compute_normalization(X, y):
    """Compute mean/std for normalization."""
    # Reshape X to (samples * seq_len, features) for stats
    X_flat = X.reshape(-1, X.shape[-1])
    scaler = {
        "X_mean": X_flat.mean(axis=0).tolist(),
        "X_std": X_flat.std(axis=0).tolist(),
        "y_mean": y.mean(axis=0).tolist(),
        "y_std": y.std(axis=0).tolist(),
    }
    # Replace 0 std with 1 to avoid division by zero
    scaler["X_std"] = [s if s > 1e-6 else 1.0 for s in scaler["X_std"]]
    scaler["y_std"] = [s if s > 1e-6 else 1.0 for s in scaler["y_std"]]
    return scaler


def normalize_X(X, scaler):
    mean = np.array(scaler["X_mean"], dtype=np.float32)
    std = np.array(scaler["X_std"], dtype=np.float32)
    return (X - mean) / std


def normalize_y(y, scaler):
    mean = np.array(scaler["y_mean"], dtype=np.float32)
    std = np.array(scaler["y_std"], dtype=np.float32)
    return (y - mean) / std


def denormalize_y(y_norm, scaler):
    mean = np.array(scaler["y_mean"], dtype=np.float32)
    std = np.array(scaler["y_std"], dtype=np.float32)
    return y_norm * std + mean


# ── Training ─────────────────────────────────────────────
def train():
    print("=" * 60)
    print("  LSTM ETA Predictor — Training")
    print("=" * 60)

    # 1. Generate data
    print(f"\n[1/5] Generating {NUM_SAMPLES} synthetic samples...")
    X, y = generate_synthetic_data(NUM_SAMPLES)
    print(f"  X shape: {X.shape}  (samples, seq_len={SEQUENCE_LENGTH}, features={NUM_FEATURES})")
    print(f"  y shape: {y.shape}  (samples, outputs={NUM_OUTPUTS})")
    print(f"  ETA range: {y[:,0].min():.1f} — {y[:,0].max():.1f} minutes")
    print(f"  Delay range: {y[:,1].min():.1f} — {y[:,1].max():.1f} minutes")

    # 2. Normalize
    print("\n[2/5] Computing normalization parameters...")
    scaler = compute_normalization(X, y)
    X_norm = normalize_X(X, scaler)
    y_norm = normalize_y(y, scaler)

    # Train/val split (80/20)
    split = int(0.8 * len(X_norm))
    X_train, X_val = X_norm[:split], X_norm[split:]
    y_train, y_val = y_norm[:split], y_norm[split:]

    train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    val_ds = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
    train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_dl = DataLoader(val_ds, batch_size=BATCH_SIZE)

    print(f"  Train: {len(X_train)}, Val: {len(X_val)}")

    # 3. Build model
    print(f"\n[3/5] Building LSTM model (hidden={HIDDEN_SIZE}, layers={NUM_LAYERS})...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")

    model = DeliveryLSTM().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loss_fn = nn.MSELoss()

    total_params = sum(p.numel() for p in model.parameters())
    print(f"  Total parameters: {total_params:,}")

    # 4. Train
    print(f"\n[4/5] Training for {EPOCHS} epochs...")
    best_val_loss = float("inf")
    best_state = None

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_dl:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            pred = model(X_batch)
            loss = loss_fn(pred, y_batch)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(X_batch)
        train_loss /= len(X_train)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in val_dl:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                pred = model(X_batch)
                val_loss += loss_fn(pred, y_batch).item() * len(X_batch)
        val_loss /= len(X_val)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = model.state_dict().copy()

        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:3d}/{EPOCHS}  train_loss={train_loss:.4f}  val_loss={val_loss:.4f}")

    # Load best model
    model.load_state_dict(best_state)
    print(f"\n  Best validation loss: {best_val_loss:.4f}")

    # 5. Save model
    print(f"\n[5/5] Saving model...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Save as TorchScript for production inference
    model.eval()
    model_cpu = model.to("cpu")
    example_input = torch.randn(1, SEQUENCE_LENGTH, NUM_FEATURES)
    scripted = torch.jit.trace(model_cpu, example_input)
    model_path = MODEL_DIR / "lstm_eta.pt"
    scripted.save(str(model_path))
    print(f"  Model saved: {model_path} ({model_path.stat().st_size / 1024:.1f} KB)")

    # Save scaler
    scaler_path = MODEL_DIR / "scaler.json"
    with open(scaler_path, "w") as f:
        json.dump(scaler, f, indent=2)
    print(f"  Scaler saved: {scaler_path}")

    # Quick test
    print("\n── Quick Test ──────────────────────")
    model_cpu.eval()
    test_X = torch.from_numpy(X_val[:5])
    with torch.no_grad():
        test_pred = model_cpu(test_X).numpy()
    test_pred_real = denormalize_y(test_pred, scaler)
    test_actual_real = denormalize_y(y_val[:5], scaler)

    for i in range(5):
        eta_p, delay_p, conf_p, cont_p = test_pred_real[i]
        eta_a, delay_a, conf_a, cont_a = test_actual_real[i]
        print(f"  Sample {i+1}: ETA pred={eta_p:.1f}min actual={eta_a:.1f}min | "
              f"Delay pred={delay_p:.1f} actual={delay_a:.1f} | "
              f"Conf={conf_p:.2f} | CanContinue={cont_p:.2f}")

    print("\n✅ Training complete!")
    return model_path, scaler_path


if __name__ == "__main__":
    train()