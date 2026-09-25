"""
Wonyo-AI: Real-Trade Neural Network Trainer & ONNX Exporter for Google Colab
Trains Multi-Task WonyoImitationNet on Authentic 2018-2021 BitMEX Trades
and Exports to Production-Ready ONNX Format for Real-time Web Dashboard Serving.
"""

import os
import sys
import time
import math
import numpy as np

# Ensure necessary libraries are installed
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    import onnx
except ImportError:
    print("[Colab Setup] Installing onnx, torch...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "onnx", "torch"])
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    import onnx

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"=== [Wonyo-AI Full Real-Trade Training on Colab] ===")
print(f"Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")


# -------------------------------------------------------------
# 1. Dataset Loader
# -------------------------------------------------------------
class WonyoRealDataset(Dataset):
    def __init__(self, npz_path: str = "wonyo_dataset_real.npz"):
        if not os.path.exists(npz_path):
            # Check src/ or parent dir
            if os.path.exists(os.path.join("src", npz_path)):
                npz_path = os.path.join("src", npz_path)
            elif os.path.exists(os.path.join("/content", npz_path)):
                npz_path = os.path.join("/content", npz_path)

        if os.path.exists(npz_path):
            print(f"Loading authentic Wonyotti trade dataset: {npz_path}")
            data = np.load(npz_path)
            self.X = torch.tensor(data['X'], dtype=torch.float32)
            self.y_action = torch.tensor(data['y_action'], dtype=torch.long)
            self.y_size = torch.tensor(data['y_size'], dtype=torch.float32).unsqueeze(1)
        else:
            print(f"[Warning] {npz_path} not found. Using fallback demo dataset...")
            n_samples = 5000
            self.X = torch.randn(n_samples, 32, 12, dtype=torch.float32)
            self.y_action = torch.randint(0, 4, (n_samples,), dtype=torch.long)
            self.y_size = torch.rand(n_samples, 1, dtype=torch.float32) * 2.0

        print(f"Dataset Size: {len(self.X):,} samples | Sequence Shape: {self.X.shape[1:]}")

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y_action[idx], self.y_size[idx]


# -------------------------------------------------------------
# 2. Neural Network Architecture: WonyoImitationNet
# -------------------------------------------------------------
class TemporalAttention(nn.Module):
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.Tanh(),
            nn.Linear(hidden_dim // 2, 1)
        )

    def forward(self, x):
        # x shape: [batch, seq_len, hidden_dim]
        scores = self.attn(x)                       # [batch, seq_len, 1]
        weights = torch.softmax(scores, dim=1)      # [batch, seq_len, 1]
        context = torch.sum(weights * x, dim=1)     # [batch, hidden_dim]
        return context, weights


class WonyoImitationNet(nn.Module):
    def __init__(self, input_dim: int = 12, hidden_dim: int = 128, num_classes: int = 4, dropout: float = 0.20):
        super().__init__()
        # 1. 1D Convolutional Blocks for Candle Micro-Geometry & Liquidity Absorption
        self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=64, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(64)
        self.conv2 = nn.Conv1d(in_channels=64, out_channels=hidden_dim, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        self.relu = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        
        # 2. Bi-Directional GRU for Orderflow Sequence & Momentum
        self.gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim // 2,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=dropout
        )
        
        # 3. Temporal Self-Attention
        self.attention = TemporalAttention(hidden_dim)
        
        # 4. Multi-Task Heads
        # Head 1: Action Classification (0=HOLD, 1=BUY_LONG, 2=SELL_SHORT, 3=CLOSE)
        self.action_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )
        
        # Head 2: Dynamic Position Sizing (0.1x ~ 5.0x leverage/scale)
        self.size_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Softplus()
        )

    def forward(self, x):
        # x: [batch, seq_len, input_dim] -> conv expects [batch, input_dim, seq_len]
        x_in = x.transpose(1, 2)
        c1 = self.relu(self.bn1(self.conv1(x_in)))
        c2 = self.relu(self.bn2(self.conv2(c1)))
        c2 = self.dropout(c2)
        
        # Transpose to [batch, seq_len, hidden_dim]
        c_seq = c2.transpose(1, 2)
        gru_out, _ = self.gru(c_seq)
        
        # Attention Pooling
        context, _ = self.attention(gru_out)
        
        # Heads
        action_logits = self.action_head(context)
        size_pred = self.size_head(context)
        
        return action_logits, size_pred


# -------------------------------------------------------------
# 3. Training & ONNX Export Pipeline
# -------------------------------------------------------------
def train_and_export_onnx(
    npz_path: str = "wonyo_dataset_real.npz",
    epochs: int = 25,
    batch_size: int = 64,
    lr: float = 1e-3,
    onnx_out: str = "wonyo_nn_model.onnx",
    pt_out: str = "wonyo_nn_model.pt"
):
    dataset = WonyoRealDataset(npz_path)
    total_len = len(dataset)
    split_idx = int(total_len * 0.85)
    
    # Train/Val Split (Sequential Time-Series preserving)
    train_indices = list(range(0, split_idx))
    val_indices = list(range(split_idx, total_len))
    
    train_subset = torch.utils.data.Subset(dataset, train_indices)
    val_subset = torch.utils.data.Subset(dataset, val_indices)
    
    train_loader = DataLoader(train_subset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_subset, batch_size=batch_size, shuffle=False)
    
    model = WonyoImitationNet(input_dim=12, hidden_dim=128, num_classes=4).to(device)
    
    # Calculate Class Weights to prevent HOLD bias
    actions = [dataset.y_action[i].item() for i in train_indices]
    counts = np.bincount(actions, minlength=4)
    total_samples = len(actions)
    weights = total_samples / (4.0 * np.maximum(counts, 1.0))
    class_weights = torch.tensor(weights, dtype=torch.float32, device=device)
    print("Computed Adaptive Class Weights:")
    labels = ["HOLD", "BUY_LONG", "SELL_SHORT", "CLOSE"]
    for i, (lbl, w) in enumerate(zip(labels, weights)):
        print(f"  {lbl} ({i}): count={counts[i]}, weight={w:.3f}")
        
    criterion_action = nn.CrossEntropyLoss(weight=class_weights)
    criterion_size = nn.SmoothL1Loss()
    
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    print(f"\n[Training] Commencing {epochs} epochs on {device}...")
    start_time = time.time()
    
    best_val_acc = 0.0
    
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct_act = 0
        samples = 0
        
        for bx, b_act, b_sz in train_loader:
            bx = bx.to(device)
            b_act = b_act.to(device)
            b_sz = b_sz.to(device)
            
            optimizer.zero_grad()
            p_act, p_sz = model(bx)
            
            loss_a = criterion_action(p_act, b_act)
            loss_s = criterion_size(p_sz, b_sz)
            loss = loss_a + 0.25 * loss_s
            
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            optimizer.step()
            
            total_loss += loss.item() * len(bx)
            correct_act += (torch.argmax(p_act, dim=1) == b_act).sum().item()
            samples += len(bx)
            
        scheduler.step()
        train_acc = correct_act / samples * 100.0
        avg_loss = total_loss / samples
        
        # Validation
        model.eval()
        val_correct = 0
        val_samples = 0
        with torch.no_grad():
            for vx, v_act, v_sz in val_loader:
                vx = vx.to(device)
                v_act = v_act.to(device)
                vp_act, _ = model(vx)
                val_correct += (torch.argmax(vp_act, dim=1) == v_act).sum().item()
                val_samples += len(vx)
                
        val_acc = val_correct / val_samples * 100.0 if val_samples > 0 else 0.0
        
        if epoch % 2 == 0 or epoch == epochs or val_acc > best_val_acc:
            print(f"Epoch [{epoch:02d}/{epochs:02d}] | Loss: {avg_loss:.4f} | Train Acc: {train_acc:.2f}% | Val Acc: {val_acc:.2f}%")
            if val_acc > best_val_acc:
                best_val_acc = val_acc
            sys.stdout.flush()
                
    elapsed = time.time() - start_time
    print(f"\nTraining Completed in {elapsed:.2f}s! Best Validation Accuracy: {best_val_acc:.2f}%")
    sys.stdout.flush()
    
    # -------------------------------------------------------------
    # 4. Save PyTorch State Dict
    # -------------------------------------------------------------
    torch.save({
        "model_state_dict": model.state_dict(),
        "input_dim": 12,
        "hidden_dim": 128,
        "classes": labels
    }, pt_out)
    print(f"Saved PyTorch model: {pt_out} ({os.path.getsize(pt_out) / 1024:.1f} KB)")
    
    # -------------------------------------------------------------
    # 5. Export to Production ONNX Format
    # -------------------------------------------------------------
    print(f"\n[ONNX Export] Converting PyTorch model to ONNX...")
    model.eval()
    dummy_input = torch.randn(1, 32, 12, device=device)
    
    torch.onnx.export(
        model,
        dummy_input,
        onnx_out,
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["market_tensor"],
        output_names=["action_logits", "size_pred"],
        dynamic_axes={
            "market_tensor": {0: "batch_size"},
            "action_logits": {0: "batch_size"},
            "size_pred": {0: "batch_size"}
        }
    )
    
    print(f"Successfully exported ONNX model to: {onnx_out}")
    print(f"ONNX Model File Size: {os.path.getsize(onnx_out) / 1024:.1f} KB")
    
    # Validate with onnx checker
    onnx_model = onnx.load(onnx_out)
    onnx.checker.check_model(onnx_model)
    print("ONNX Model Graph Validation Passed!")

if __name__ == "__main__":
    train_and_export_onnx(
        npz_path="wonyo_dataset_real.npz",
        epochs=30,
        batch_size=64,
        lr=0.0015,
        onnx_out="wonyo_nn_model.onnx",
        pt_out="wonyo_nn_model.pt"
    )
