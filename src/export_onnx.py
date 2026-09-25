"""
Wonyo-AI: Fast ONNX Exporter
Loads trained PyTorch checkpoint and exports to ONNX.
"""

import os
import sys
import torch
import torch.nn as nn
import onnx

# Ensure onnxscript is available
try:
    import onnxscript
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "onnxscript"])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Model Architecture Definition
class TemporalAttention(nn.Module):
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.Tanh(),
            nn.Linear(hidden_dim // 2, 1)
        )

    def forward(self, x):
        scores = self.attn(x)
        weights = torch.softmax(scores, dim=1)
        context = torch.sum(weights * x, dim=1)
        return context, weights


class WonyoImitationNet(nn.Module):
    def __init__(self, input_dim: int = 12, hidden_dim: int = 128, num_classes: int = 4, dropout: float = 0.20):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=64, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(64)
        self.conv2 = nn.Conv1d(in_channels=64, out_channels=hidden_dim, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        self.relu = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        
        self.gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim // 2,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=dropout
        )
        
        self.attention = TemporalAttention(hidden_dim)
        
        self.action_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )
        
        self.size_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Softplus()
        )

    def forward(self, x):
        x_in = x.transpose(1, 2)
        c1 = self.relu(self.bn1(self.conv1(x_in)))
        c2 = self.relu(self.bn2(self.conv2(c1)))
        c2 = self.dropout(c2)
        
        c_seq = c2.transpose(1, 2)
        gru_out, _ = self.gru(c_seq)
        context, _ = self.attention(gru_out)
        
        action_logits = self.action_head(context)
        size_pred = self.size_head(context)
        return action_logits, size_pred


def export():
    pt_path = "wonyo_nn_model.pt"
    if not os.path.exists(pt_path) and os.path.exists(f"/content/{pt_path}"):
        pt_path = f"/content/{pt_path}"

    print(f"Loading checkpoint: {pt_path}...")
    ckpt = torch.load(pt_path, map_location=device)
    
    model = WonyoImitationNet(input_dim=12, hidden_dim=128, num_classes=4).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    
    dummy_input = torch.randn(1, 32, 12, device=device)
    onnx_out = "/content/wonyo_nn_model.onnx"
    
    print("Exporting model to ONNX...")
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
    
    print(f"Successfully generated ONNX file: {onnx_out}")
    print(f"File size: {os.path.getsize(onnx_out) / 1024:.1f} KB")
    
    # Check ONNX
    onnx_model = onnx.load(onnx_out)
    onnx.checker.check_model(onnx_model)
    print("ONNX Model Graph Validation Passed 100%!")


if __name__ == "__main__":
    export()
