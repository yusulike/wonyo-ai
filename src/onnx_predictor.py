"""
Wonyo-AI ONNX Runtime Inference Engine
Ultra-fast, zero-PyTorch dependency production inference for Real-time Web Dashboard.
"""

import os
import time
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

try:
    import onnxruntime as ort
except ImportError:
    ort = None


FEATURE_COLS = [
    'volume_zscore',
    'volume_exhaustion',
    'body_ratio',
    'upper_wick_ratio',
    'lower_wick_ratio',
    'bullish_absorption',
    'bearish_absorption',
    'ret_1',
    'ret_5',
    'trend_bias',
    'microstructure_risk',
    'kaufman_efficiency'
]

ACTION_LABELS = ["HOLD", "BUY_LONG", "SELL_SHORT", "CLOSE"]


class WonyoONNXPredictor:
    def __init__(self, model_path: Optional[str] = None):
        self.session = None
        self.is_loaded = False
        self.model_path = model_path or os.path.join(os.path.dirname(__file__), "wonyo_nn_model.onnx")
        self._init_session()

    def _init_session(self):
        if ort is None:
            print("[ONNX Predictor] onnxruntime not installed.")
            return

        if not os.path.exists(self.model_path):
            alt_path = "src/wonyo_nn_model.onnx"
            if os.path.exists(alt_path):
                self.model_path = alt_path
            else:
                print(f"[ONNX Predictor] Model file not found at: {self.model_path}")
                return

        try:
            # CPUExecutionProvider is ultra-fast and lightweight for single 32x12 tensor (~0.3ms)
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 2
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=opts,
                providers=["CPUExecutionProvider"]
            )
            self.input_name = self.session.get_inputs()[0].name
            self.is_loaded = True
            print(f"[ONNX Predictor] Loaded successfully: {self.model_path}")
        except Exception as e:
            print(f"[ONNX Predictor] Failed to load ONNX model: {e}")
            self.session = None
            self.is_loaded = False

    def predict(self, df_features: pd.DataFrame) -> Dict[str, Any]:
        """
        Runs real-time inference on the latest 32 candle features.
        """
        if not self.is_loaded or self.session is None:
            return {
                "status": "OFFLINE",
                "action": "HOLD",
                "confidence_pct": 50.0,
                "probabilities": {"hold_pct": 50.0, "long_pct": 25.0, "short_pct": 25.0, "close_pct": 0.0},
                "size_multiplier": 1.0,
                "latency_ms": 0.0,
                "engine": "OFFLINE",
                "message": "ONNX model not loaded"
            }

        try:
            t0 = time.perf_counter()
            # Ensure we have at least 32 rows
            if len(df_features) < 32:
                # Pad with first row if buffer is smaller than 32
                pad_rows = 32 - len(df_features)
                pad_df = pd.concat([df_features.iloc[[0]] * 0] * pad_rows + [df_features], ignore_index=True)
                subset = pad_df.iloc[-32:][FEATURE_COLS]
            else:
                subset = df_features.iloc[-32:][FEATURE_COLS]

            # Clean NaNs and Infinities
            clean_matrix = subset.fillna(0.0).replace([np.inf, -np.inf], 0.0).to_numpy(dtype=np.float32)
            market_tensor = np.expand_dims(clean_matrix, axis=0) # [1, 32, 12]

            logits, size_pred = self.session.run(None, {self.input_name: market_tensor})
            latency_ms = (time.perf_counter() - t0) * 1000.0

            # Softmax
            raw_logits = logits[0]
            exp_logits = np.exp(raw_logits - np.max(raw_logits))
            probs = exp_logits / np.sum(exp_logits)

            action_idx = int(np.argmax(probs))
            predicted_action = ACTION_LABELS[action_idx]
            size_multiplier = float(np.clip(size_pred[0][0], 0.1, 5.0))

            return {
                "status": "READY",
                "action": predicted_action,
                "confidence_pct": round(float(probs[action_idx]) * 100.0, 1),
                "probabilities": {
                    "hold_pct": round(float(probs[0]) * 100.0, 1),
                    "long_pct": round(float(probs[1]) * 100.0, 1),
                    "short_pct": round(float(probs[2]) * 100.0, 1),
                    "close_pct": round(float(probs[3]) * 100.0, 1)
                },
                "size_multiplier": round(size_multiplier, 2),
                "latency_ms": round(latency_ms, 2),
                "engine": "ONNX Runtime C++ (Optimized)",
                "model_version": "WonyoImitationNet-v1.0"
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "action": "HOLD",
                "confidence_pct": 50.0,
                "probabilities": {"hold_pct": 50.0, "long_pct": 25.0, "short_pct": 25.0, "close_pct": 0.0},
                "size_multiplier": 1.0,
                "latency_ms": 0.0,
                "engine": "ERROR",
                "message": str(e)
            }
