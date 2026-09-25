"""
Wonyo-AI Behavioral Cloning Neural Network Trainer for Google Colab
Target Hardware: Google Colab Remote GPU (T4 / L4 / A100) via Colab CLI
Run via:
    colab run --gpu T4 src/train_colab_nn.py
Or interactive session:
    colab new -s wonyo --gpu T4
    colab install -s wonyo duckdb polars torch
    colab exec -s wonyo -f src/train_colab_nn.py
    colab download -s wonyo wonyo_nn_model.pt
    colab stop -s wonyo
"""

import os
import sys
import glob
import time
import math
import numpy as np

# Ensure necessary libraries are installed when running remotely on Colab VM
try:
    import duckdb
    import polars as pl
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
except ImportError:
    print("[Colab Setup] Installing duckdb, polars...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "duckdb", "polars"])
    import duckdb
    import polars as pl
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader

# Detect Compute Device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"=== [Wonyo-AI NN Training on Colab] ===")
print(f"Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")


# -------------------------------------------------------------
# 1. Data Loader & Feature Engineering
# -------------------------------------------------------------
def load_and_preprocess_wonyo_trades(data_dir: str = "aoa_public_2021-12-31_with_letter"):
    print(f"\n[1/4] Scanning trade files in: {data_dir}...")
    files = sorted(glob.glob(f"{data_dir}/aoa-execution-*.csv"))
    if not files:
        # Fallback to current directory or uploaded files
        files = sorted(glob.glob("aoa-execution-*.csv"))
    
    if not files:
        print(f"[Warning] No execution CSVs found in {data_dir}. Generating synthetic demonstration data for verification...")
        return generate_synthetic_wonyo_dataset()

    print(f"Found {len(files)} execution CSV files:")
    for f in files:
        print(f"  - {f}")

    con = duckdb.connect()
    print("Aggregating XBTUSD executions ordered chronologically...")
    trades_df = con.sql(f"""
        SELECT 
            CAST(transacttime AS TIMESTAMP) as ts,
            side,
            lastqty,
            lastpx,
            ordtype,
            lastliquidityind,
            CASE WHEN side = 'Buy' THEN lastqty ELSE -lastqty END as signed_qty
        FROM '{data_dir}/aoa-execution-*.csv'
        WHERE symbol = 'XBTUSD' AND exectype = 'Trade' AND transacttime IS NOT NULL
        ORDER BY ts ASC
    """).pl()
    
    print(f"Total Trade Rows: {len(trades_df):,}")
    
    # Calculate cumulative position and cycle states
    trades_df = trades_df.with_columns([
        pl.col("signed_qty").cum_sum().alias("cum_position"),
        pl.col("lastpx").pct_change().fill_null(0.0).alias("price_return")
    ])
    
    return trades_df


def generate_synthetic_wonyo_dataset(n_samples: int = 5000, seq_len: int = 32, n_features: int = 12):
    """Fallback generator when running test without full 600MB data uploaded."""
    print(f"Generating synthetic behavioral dataset ({n_samples} samples)...")
    np.random.seed(42)
    X = np.random.randn(n_samples, seq_len, n_features).astype(np.float32)
    # Action labels: 0=HOLD, 1=BUY_LONG, 2=SELL_SHORT, 3=CLOSE
    y_action = np.random.choice([0, 1, 2, 3], size=n_samples, p=[0.70, 0.12, 0.12, 0.06]).astype(np.int64)
    y_size = np.random.uniform(0.1, 3.0, size=n_samples).astype(np.float32)
    return X, y_action, y_size


# -------------------------------------------------------------
# 2. PyTorch Dataset Definition
# -------------------------------------------------------------
class WonyoBehaviorDataset(Dataset):
    def __init__(self, X: np.ndarray, y_action: np.ndarray, y_size: np.ndarray):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y_action = torch.tensor(y_action, dtype=torch.long)
        self.y_size = torch.tensor(y_size, dtype=torch.float32).unsqueeze(1)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y_action[idx], self.y_size[idx]


# -------------------------------------------------------------
# 3. Neural Network Architecture: WonyoImitationNet
#    - Multi-Head 1D-CNN + Bidirectional GRU + Self-Attention
#    - Head 1: Action Classification (HOLD, LONG, SHORT, CLOSE)
#    - Head 2: Dynamic Position Size Regression (Kelly scale)
# -------------------------------------------------------------
class TemporalAttention(nn.Module):
    def __init__(self, hidden_dim):
        super().__init__()
        self.attn = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.Tanh(),
            nn.Linear(hidden_dim // 2, 1)
        )

    def forward(self, x):
        # x shape: [batch, seq_len, hidden_dim]
        weights = torch.softmax(self.attn(x), dim=1) # [batch, seq_len, 1]
        context = torch.sum(weights * x, dim=1)      # [batch, hidden_dim]
        return context, weights


class WonyoImitationNet(nn.Module):
    def __init__(self, input_dim: int = 12, hidden_dim: int = 128, num_classes: int = 4, dropout: float = 0.25):
        super().__init__()
        # 1. Local Pattern Feature Extraction (1D Convolutions for candle absorption & spikes)
        self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=64, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(in_channels=64, out_channels=hidden_dim, kernel_size=3, padding=1)
        self.relu = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        
        # 2. Sequence Dynamics (Bi-GRU)
        self.gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim // 2,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=dropout
        )
        
        # 3. Attention Layer (focus on key liquidity absorption moments)
        self.attention = TemporalAttention(hidden_dim)
        
        # 4. Multi-Task Output Heads
        # Head A: Action Classifier (HOLD=0, LONG=1, SHORT=2, CLOSE=3)
        self.action_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )
        
        # Head B: Sizing Regressor (Normalized Leverage / Bet size)
        self.size_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Softplus() # Guarantee positive sizing
        )

    def forward(self, x):
        # Input shape: [batch, seq_len, input_dim]
        # Transpose for Conv1d: [batch, input_dim, seq_len]
        x_conv = x.transpose(1, 2)
        x_conv = self.relu(self.conv1(x_conv))
        x_conv = self.relu(self.conv2(x_conv))
        x_conv = self.dropout(x_conv)
        
        # Transpose back: [batch, seq_len, hidden_dim]
        x_seq = x_conv.transpose(1, 2)
        gru_out, _ = self.gru(x_seq)
        
        # Temporal Attention Pooling
        context, _ = self.attention(gru_out)
        
        # Multi-Head Outputs
        action_logits = self.action_head(context)
        size_pred = self.size_head(context)
        
        return action_logits, size_pred


# -------------------------------------------------------------
# 4. Training & Validation Loop
# -------------------------------------------------------------
def train_model(epochs: int = 15, batch_size: int = 64, lr: float = 1e-3):
    X, y_action, y_size = generate_synthetic_wonyo_dataset(n_samples=10000, seq_len=32, n_features=12)
    
    # Train / Validation Split (80 / 20)
    split_idx = int(len(X) * 0.8)
    train_dataset = WonyoBehaviorDataset(X[:split_idx], y_action[:split_idx], y_size[:split_idx])
    val_dataset = WonyoBehaviorDataset(X[split_idx:], y_action[split_idx:], y_size[split_idx:])
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    model = WonyoImitationNet(input_dim=12, hidden_dim=128).to(device)
    
    # Loss functions: CrossEntropy with class weighting for imbalanced HOLD vs ENTRY
    class_weights = torch.tensor([1.0, 3.5, 3.5, 2.0], device=device)
    criterion_action = nn.CrossEntropyLoss(weight=class_weights)
    criterion_size = nn.SmoothL1Loss()
    
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    print(f"\n[3/4] Starting Training ({epochs} epochs, Batch Size: {batch_size})...")
    start_time = time.time()
    
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct_action = 0
        total_samples = 0
        
        for batch_x, batch_action, batch_size_true in train_loader:
            batch_x = batch_x.to(device)
            batch_action = batch_action.to(device)
            batch_size_true = batch_size_true.to(device)
            
            optimizer.zero_grad()
            pred_action, pred_size = model(batch_x)
            
            loss_act = criterion_action(pred_action, batch_action)
            loss_sz = criterion_size(pred_size, batch_size_true)
            loss = loss_act + 0.3 * loss_sz
            
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
            optimizer.step()
            
            total_loss += loss.item() * len(batch_x)
            preds = torch.argmax(pred_action, dim=1)
            correct_action += (preds == batch_action).sum().item()
            total_samples += len(batch_x)
            
        scheduler.step()
        train_acc = correct_action / total_samples * 100.0
        avg_loss = total_loss / total_samples
        
        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for vx, v_act, v_sz in val_loader:
                vx = vx.to(device)
                v_act = v_act.to(device)
                v_pred_act, _ = model(vx)
                val_correct += (torch.argmax(v_pred_act, dim=1) == v_act).sum().item()
                val_total += len(vx)
        val_acc = val_correct / val_total * 100.0
        
        if epoch % 3 == 0 or epoch == epochs:
            print(f"Epoch [{epoch:02d}/{epochs:02d}] | Train Loss: {avg_loss:.4f} | Train Acc: {train_acc:.2f}% | Val Acc: {val_acc:.2f}%")
            
    elapsed = time.time() - start_time
    print(f"\n[4/4] Training Complete in {elapsed:.2f}s!")
    
    # Save checkpoint
    out_path = "wonyo_nn_model.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "input_dim": 12,
        "hidden_dim": 128,
        "classes": ["HOLD", "BUY_LONG", "SELL_SHORT", "CLOSE"]
    }, out_path)
    print(f"Model saved successfully to: {os.path.abspath(out_path)}")
    print(f"File size: {os.path.getsize(out_path) / 1024:.1f} KB")


if __name__ == "__main__":
    train_model(epochs=12, batch_size=128, lr=0.002)
