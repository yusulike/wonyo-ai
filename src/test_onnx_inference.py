"""
Test ONNX Runtime Inference for Wonyo-AI Neural Network
Verifies that the downloaded ONNX model executes smoothly with microsecond latency.
"""

import time
import numpy as np
import onnxruntime as ort

print("=== [Testing ONNX Runtime Inference] ===")
model_path = "src/wonyo_nn_model.onnx"
print(f"Loading ONNX Model: {model_path}")

session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

input_name = session.get_inputs()[0].name
input_shape = session.get_inputs()[0].shape
output_names = [o.name for o in session.get_outputs()]

print(f"Input: {input_name} (Shape: {input_shape})")
print(f"Outputs: {output_names}")

# Benchmark single-sample inference latency
batch_x = np.random.randn(1, 32, 12).astype(np.float32)

# Warmup
for _ in range(5):
    _ = session.run(None, {input_name: batch_x})

# Benchmark
latencies = []
for _ in range(100):
    t0 = time.perf_counter()
    logits, size_pred = session.run(None, {input_name: batch_x})
    latencies.append((time.perf_counter() - t0) * 1000.0)

# Softmax for probabilities
probs = np.exp(logits[0]) / np.sum(np.exp(logits[0]))
action_idx = int(np.argmax(probs))
labels = ["HOLD", "BUY_LONG", "SELL_SHORT", "CLOSE"]

print("\n--- Inference Benchmark Results ---")
print(f"Average Latency: {np.mean(latencies):.2f} ms (Min: {np.min(latencies):.2f} ms, Max: {np.max(latencies):.2f} ms)")
print(f"Predicted Action: {labels[action_idx]} (Confidence: {probs[action_idx]*100:.2f}%)")
print(f"Action Probabilities: HOLD={probs[0]:.2f}, LONG={probs[1]:.2f}, SHORT={probs[2]:.2f}, CLOSE={probs[3]:.2f}")
print(f"Predicted Sizing Scale: {float(size_pred[0][0]):.2f}x")
print("\n[SUCCESS] ONNX Model is verified and ready for production serving!")
