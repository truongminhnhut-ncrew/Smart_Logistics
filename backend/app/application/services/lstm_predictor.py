"""
lstm_predictor.py — LSTM-based ETA & delay prediction.

Theo TONGQUAN.md mục 17: Module AI dự báo delay/ETA dùng LSTM.

KIẾN TRÚC:
  Input features (t-5 đến t) — sequence of 5 ticks, each with 6 features:
    - speed_kmh[t]            : tốc độ tại tick t
    - distance_remaining_km   : khoảng cách còn lại đến đích
    - incident_flag           : 1 nếu có sự cố, 0 nếu không
    - sin(hour_of_day)        : sin encoding giờ
    - cos(hour_of_day)        : cos encoding giờ
    - traffic_factor          : hệ số giao thông khu vực

  Output:
    - predicted_eta_minutes   : ETA dự báo (phút)
    - predicted_delay_minutes : Delay so với SLA (phút)
    - confidence              : độ tin cậy [0.0 - 1.0]
    - can_continue            : có thể tiếp tục giao hay không (bool)
    - recommended_action      : hành động đề xuất (str)
    - method                  : "lstm" hoặc "heuristic"

Tài liệu tham khảo:
  - Sutskever et al., "Sequence to Sequence Learning with Neural Networks" (2014)
  - Hochreiter & Schmidhuber, "Long Short-Term Memory" (1997)
"""

import json
import math
import random
import logging
from collections import deque
from pathlib import Path
from typing import Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────
SEQUENCE_LENGTH = 5        # 5 ticks history input
NUM_FEATURES = 6           # speed, distance, incident, sin_h, cos_h, traffic
AVERAGE_CITY_SPEED = 25.0  # km/h trong nội thành HCMC
BASE_DELAY_FACTOR = 0.15   # 15% base delay buffer
MODEL_DIR = Path(__file__).parent / "models"


class ShipperHistory:
    """Sliding window of speed history per shipper."""

    def __init__(self, max_len: int = SEQUENCE_LENGTH):
        self._speeds: Deque[float] = deque(maxlen=max_len)

    def push(self, speed_kmh: float) -> None:
        self._speeds.append(speed_kmh)

    def get_sequence(self) -> List[float]:
        return list(self._speeds)

    def avg_speed(self) -> float:
        if not self._speeds:
            return AVERAGE_CITY_SPEED
        return sum(self._speeds) / len(self._speeds)

    def is_ready(self) -> bool:
        return len(self._speeds) >= SEQUENCE_LENGTH


def _get_recommended_action(can_continue: bool, delay_minutes: float,
                            incident_flag: bool, avg_speed: float) -> str:
    """Determine recommended action based on prediction outputs."""
    if not can_continue:
        if avg_speed < 2.0:
            return "REASSIGN_ORDER"
        return "WAIT_AND_RETRY"

    if delay_minutes > 30:
        return "REROUTE_IMMEDIATELY"
    elif delay_minutes > 15:
        return "NOTIFY_CUSTOMER_AND_REROUTE"
    elif delay_minutes > 5:
        return "NOTIFY_CUSTOMER"
    elif incident_flag:
        return "MONITOR_CLOSELY"
    else:
        return "CONTINUE_NORMAL"


class LSTMPredictor:
    """
    LSTM ETA predictor with real PyTorch model support.

    Loads TorchScript model from models/lstm_eta.pt if available,
    otherwise falls back to heuristic prediction.
    """

    def __init__(self):
        self._histories: Dict[str, ShipperHistory] = {}
        self._model = None
        self._scaler = None
        self._model_available = False
        self._load_model()

    def _load_model(self) -> None:
        """Load pre-trained LSTM TorchScript model + scaler."""
        model_path = MODEL_DIR / "lstm_eta.pt"
        scaler_path = MODEL_DIR / "scaler.json"

        if model_path.exists() and scaler_path.exists():
            try:
                import torch
                self._model = torch.jit.load(str(model_path), map_location="cpu")
                self._model.eval()

                with open(scaler_path, "r") as f:
                    self._scaler = json.load(f)

                self._model_available = True
                logger.info("✅ LSTM model loaded successfully from %s", model_path)
            except Exception as e:
                logger.warning("⚠️ Failed to load LSTM model: %s. Using heuristic.", e)
                self._model_available = False
        else:
            logger.info("ℹ️ LSTM model not found at %s. Using heuristic fallback.", model_path)
            self._model_available = False

    def update_history(self, shipper_id: str, speed_kmh: float) -> None:
        """Push a new speed observation to shipper's history window."""
        if shipper_id not in self._histories:
            self._histories[shipper_id] = ShipperHistory()
        self._histories[shipper_id].push(speed_kmh)

    def predict_eta(
        self,
        shipper_id: str,
        distance_remaining_km: float,
        incident_flag: bool = False,
        hour_of_day: int = 12,
        traffic_factor: float = 1.0,
    ) -> dict:
        """
        Predict ETA and delay for a shipper.

        Returns:
            {
                "predicted_eta_minutes": 15.0,
                "predicted_delay_minutes": 2.0,
                "confidence": 0.82,
                "can_continue": True,
                "recommended_action": "CONTINUE_NORMAL",
                "method": "lstm" | "heuristic"
            }
        """
        history = self._histories.get(shipper_id)
        avg_speed = history.avg_speed() if history else AVERAGE_CITY_SPEED

        if self._model_available and self._model is not None and self._scaler is not None:
            try:
                return self._model_predict(
                    shipper_id, distance_remaining_km,
                    incident_flag, hour_of_day, traffic_factor
                )
            except Exception as e:
                logger.warning("LSTM predict failed: %s. Falling back to heuristic.", e)

        return self._heuristic_predict(
            avg_speed, distance_remaining_km, incident_flag,
            hour_of_day, traffic_factor
        )

    def _heuristic_predict(
        self,
        avg_speed_kmh: float,
        distance_km: float,
        incident_flag: bool,
        hour_of_day: int,
        traffic_factor: float,
    ) -> dict:
        """
        Heuristic ETA prediction (fallback when LSTM model not available).

        Logic:
          - Giờ cao điểm (7-9h, 17-19h): traffic_factor × 1.5
          - Sự cố: + delay theo incident type
          - Noise nhỏ ±5% để simulate model uncertainty
        """
        # Peak hour multiplier
        peak_hours = set(range(7, 10)) | set(range(17, 20))
        peak_factor = 1.5 if hour_of_day in peak_hours else 1.0

        effective_speed = avg_speed_kmh / (traffic_factor * peak_factor)
        effective_speed = max(5.0, effective_speed)  # min 5 km/h

        raw_eta = (distance_km / effective_speed) * 60  # minutes

        # SLA delay simulation
        sla_eta = (distance_km / AVERAGE_CITY_SPEED) * 60
        delay = max(0.0, raw_eta - sla_eta)

        if incident_flag:
            delay += random.uniform(5, 20)
            raw_eta += delay

        # Noise ±5% (simulating model uncertainty)
        noise = raw_eta * random.uniform(-0.05, 0.05)
        predicted_eta = round(max(0, raw_eta + noise), 1)
        predicted_delay = round(max(0, delay), 1)

        # Confidence: lower if incident or high traffic
        confidence = 0.90
        if incident_flag:
            confidence -= 0.25
        if traffic_factor > 1.5:
            confidence -= 0.10
        confidence = round(max(0.40, confidence + random.uniform(-0.05, 0.05)), 2)

        # Can continue assessment
        can_continue = True
        if incident_flag and avg_speed_kmh < 5.0:
            can_continue = False
        elif incident_flag and avg_speed_kmh < 10.0 and predicted_delay > 20:
            can_continue = False

        recommended_action = _get_recommended_action(
            can_continue, predicted_delay, incident_flag, avg_speed_kmh
        )

        return {
            "predicted_eta_minutes": predicted_eta,
            "predicted_delay_minutes": predicted_delay,
            "confidence": confidence,
            "can_continue": can_continue,
            "recommended_action": recommended_action,
            "method": "heuristic",
        }

    def _model_predict(
        self,
        shipper_id: str,
        distance_km: float,
        incident_flag: bool,
        hour_of_day: int,
        traffic_factor: float,
    ) -> dict:
        """
        LSTM model inference using TorchScript model.

        Input tensor shape: (1, SEQUENCE_LENGTH, NUM_FEATURES)
        Features per tick: [speed, distance, incident, sin(hour), cos(hour), traffic]
        """
        import torch
        import numpy as np

        history = self._histories.get(shipper_id)
        speeds = history.get_sequence() if history and history.is_ready() else [AVERAGE_CITY_SPEED] * SEQUENCE_LENGTH
        avg_speed = sum(speeds) / len(speeds)

        # Pad if not enough history
        while len(speeds) < SEQUENCE_LENGTH:
            speeds.insert(0, speeds[0] if speeds else AVERAGE_CITY_SPEED)

        # Build feature sequence
        sin_h = math.sin(2 * math.pi * hour_of_day / 24)
        cos_h = math.cos(2 * math.pi * hour_of_day / 24)
        inc_flag = 1.0 if incident_flag else 0.0

        sequence = []
        for t, spd in enumerate(speeds[-SEQUENCE_LENGTH:]):
            d = distance_km - (t * spd / 3600)
            d = max(0.1, d)
            sequence.append([spd, d, inc_flag, sin_h, cos_h, traffic_factor])

        # Normalize input
        X = np.array([sequence], dtype=np.float32)  # (1, 5, 6)
        X_mean = np.array(self._scaler["X_mean"], dtype=np.float32)
        X_std = np.array(self._scaler["X_std"], dtype=np.float32)
        X_norm = (X - X_mean) / X_std

        # Inference
        with torch.no_grad():
            input_tensor = torch.from_numpy(X_norm)
            output = self._model(input_tensor).numpy()[0]  # (4,)

        # Denormalize output
        y_mean = np.array(self._scaler["y_mean"], dtype=np.float32)
        y_std = np.array(self._scaler["y_std"], dtype=np.float32)
        output_real = output * y_std + y_mean

        predicted_eta = round(max(0.1, float(output_real[0])), 1)
        predicted_delay = round(max(0.0, float(output_real[1])), 1)
        confidence = round(min(0.99, max(0.30, float(output_real[2]))), 2)
        can_continue_score = float(output_real[3])
        can_continue = can_continue_score > 0.5

        recommended_action = _get_recommended_action(
            can_continue, predicted_delay, incident_flag, avg_speed
        )

        return {
            "predicted_eta_minutes": predicted_eta,
            "predicted_delay_minutes": predicted_delay,
            "confidence": confidence,
            "can_continue": can_continue,
            "recommended_action": recommended_action,
            "method": "lstm",
        }

    def batch_predict(self, shippers: List[dict]) -> Dict[str, dict]:
        """
        Batch predict ETA for all active shippers.

        Args:
            shippers: List of shipper dicts with keys:
                - shipper_id, speed_kmh, distance_remaining_km,
                  has_incident, eta_minutes (current)
        Returns:
            Dict of shipper_id -> prediction result
        """
        from datetime import datetime
        hour = datetime.utcnow().hour

        results = {}
        for s in shippers:
            if s.get("distance_remaining_km", 0) <= 0:
                continue
            self.update_history(s["shipper_id"], s.get("speed_kmh", AVERAGE_CITY_SPEED))
            results[s["shipper_id"]] = self.predict_eta(
                shipper_id=s["shipper_id"],
                distance_remaining_km=s.get("distance_remaining_km", 0),
                incident_flag=s.get("has_incident", False),
                hour_of_day=hour,
                traffic_factor=1.0,
            )
        return results


# Singleton instance
lstm_predictor = LSTMPredictor()