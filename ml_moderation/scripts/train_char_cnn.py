"""Phase 6 (Model C): Compact Character-level 1D CNN trained with PyTorch.

Training-only script: PyTorch is intentionally excluded from backend/requirements.txt
so production deployment on Render Free stays lightweight unless Char-CNN demonstrates
a decisive advantage justifying its memory/dependency footprint.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import random
import sys
import time

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
venv_site = ROOT / ".venv" / "Lib" / "site-packages"
if venv_site.is_dir() and str(venv_site) not in sys.path:
    sys.path.append(str(venv_site))

from ml_moderation.config import GENERATED_DIR, RANDOM_SEED, REPORTS_DIR
from ml_moderation.normalization import normalize_text
from ml_moderation.scripts.train_models import compute_detailed_metrics, measure_latency_ms, tune_threshold

MAX_LEN = 96


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_split(name: str) -> list[dict[str, str]]:
    with (GENERATED_DIR / f"{name}.csv").open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_char_vocab(texts: list[str], min_freq: int = 2) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in texts:
        for ch in t:
            counts[ch] = counts.get(ch, 0) + 1
    vocab = {"<PAD>": 0, "<UNK>": 1}
    for ch, cnt in sorted(counts.items()):
        if cnt >= min_freq:
            vocab[ch] = len(vocab)
    return vocab


def encode_text(text: str, vocab: dict[str, int], max_len: int = MAX_LEN) -> list[int]:
    norm = normalize_text(text).combined_model_text[:max_len]
    unk = vocab["<UNK>"]
    ids = [vocab.get(ch, unk) for ch in norm]
    if len(ids) < max_len:
        ids.extend([0] * (max_len - len(ids)))
    return ids


class CharCNN(nn.Module):
    """Lightweight multi-scale 1D Character CNN for binary filename moderation."""

    def __init__(self, vocab_size: int, emb_dim: int = 32, num_filters: int = 48) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, emb_dim, padding_idx=0)
        self.conv3 = nn.Conv1d(emb_dim, num_filters, kernel_size=3, padding=1)
        self.conv4 = nn.Conv1d(emb_dim, num_filters, kernel_size=4, padding=2)
        self.conv5 = nn.Conv1d(emb_dim, num_filters, kernel_size=5, padding=2)
        self.dropout = nn.Dropout(0.25)
        self.fc1 = nn.Linear(num_filters * 3, 64)
        self.fc2 = nn.Linear(64, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        emb = self.embedding(x).transpose(1, 2)  # (B, E, L)
        c3 = torch.relu(self.conv3(emb)).amax(dim=2)
        c4 = torch.relu(self.conv4(emb)).amax(dim=2)
        c5 = torch.relu(self.conv5(emb)).amax(dim=2)
        feat = torch.cat([c3, c4, c5], dim=1)
        h = torch.relu(self.fc1(self.dropout(feat)))
        return self.fc2(h).squeeze(1)


def train_and_evaluate() -> dict:
    set_seed(RANDOM_SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_rows = load_split("train")
    val_rows = load_split("val")
    test_rows = load_split("test")
    challenge_rows = load_split("challenge_test")

    train_norm_texts = [normalize_text(r["filename"]).combined_model_text for r in train_rows]
    vocab = build_char_vocab(train_norm_texts, min_freq=2)

    X_train = torch.tensor([encode_text(r["filename"], vocab) for r in train_rows], dtype=torch.long)
    y_train = torch.tensor([int(r["label"]) for r in train_rows], dtype=torch.float32)
    X_val = torch.tensor([encode_text(r["filename"], vocab) for r in val_rows], dtype=torch.long)
    y_val_np = np.array([int(r["label"]) for r in val_rows], dtype=int)
    X_test = torch.tensor([encode_text(r["filename"], vocab) for r in test_rows], dtype=torch.long)
    X_chal = torch.tensor([encode_text(r["filename"], vocab) for r in challenge_rows], dtype=torch.long)

    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=128, shuffle=True)

    model = CharCNN(vocab_size=len(vocab), emb_dim=32, num_filters=48).to(device)
    pos_weight = torch.tensor([(y_train == 0).sum() / max((y_train == 1).sum(), 1)], dtype=torch.float32, device=device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2.5e-3, weight_decay=1e-4)

    epochs = 10
    best_val_f1 = -1.0
    best_state = None
    best_tuned = None

    train_start = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            logits = model(bx)
            loss = criterion(logits, by)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * len(bx)

        model.eval()
        with torch.no_grad():
            val_probs = torch.sigmoid(model(X_val.to(device))).cpu().numpy()
        tuned = tune_threshold(y_val_np, val_probs, max_fpr=0.008)
        print(f"Epoch {epoch:02d}/{epochs} | loss={total_loss / len(train_rows):.4f} | val_f1={tuned['f1']:.4f} | val_fpr={tuned['fpr']:.4f}")
        score = tuned["f1"] - max(0.0, tuned["fpr"] - 0.01) * 5.0
        if score > best_val_f1:
            best_val_f1 = score
            best_tuned = tuned
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    train_seconds = time.perf_counter() - train_start
    assert best_state is not None and best_tuned is not None

    # Move best model to CPU for fair Render-equivalent inference evaluation
    cpu_model = CharCNN(vocab_size=len(vocab), emb_dim=32, num_filters=48)
    cpu_model.load_state_dict(best_state)
    cpu_model.eval()

    exp_dir = REPORTS_DIR / "experimental_models"
    exp_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = exp_dir / "model_c_char_cnn.pt"
    torch.save({"state_dict": best_state, "vocab": vocab, "max_len": MAX_LEN, "threshold": best_tuned["threshold"]}, ckpt_path)

    th = best_tuned["threshold"]
    with torch.no_grad():
        test_probs = torch.sigmoid(cpu_model(X_test)).numpy()
        chal_probs = torch.sigmoid(cpu_model(X_chal)).numpy()

    test_preds = (test_probs >= th).astype(int).tolist()
    chal_preds = (chal_probs >= th).astype(int).tolist()

    def predict_single_cpu(text: str) -> float:
        with torch.no_grad():
            x = torch.tensor([encode_text(text, vocab)], dtype=torch.long)
            return float(torch.sigmoid(cpu_model(x)).item())

    lat = measure_latency_ms(predict_single_cpu, [r["filename"] for r in test_rows[:200]], warmup=20)
    num_params = sum(p.numel() for p in cpu_model.parameters())

    out = {
        "description": "Compact PyTorch 1D Character-level CNN (Embedding 32 + Conv1d k=3,4,5)",
        "device_trained": str(device),
        "epochs": epochs,
        "train_seconds": round(train_seconds, 2),
        "num_parameters": int(num_params),
        "vocab_size": len(vocab),
        "threshold": round(th, 4),
        "val_f1": round(best_tuned["f1"], 6),
        "val_fpr": round(best_tuned["fpr"], 6),
        "artifact_size_kb": round(ckpt_path.stat().st_size / 1024.0, 2),
        "latency_ms": lat,
        "test": compute_detailed_metrics(test_rows, test_preds),
        "challenge": compute_detailed_metrics(challenge_rows, chal_preds),
    }
    out_path = REPORTS_DIR / "char_cnn_results.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"model_c_char_cnn                 | TEST F1={out['test']['f1']:.4f} ObfRec={out['test'].get('obfuscated_recall', 0):.4f} FPR={out['test']['fpr']:.4f} "
        f"| CHAL F1={out['challenge']['f1']:.4f} ObfRec={out['challenge'].get('obfuscated_recall', 0):.4f} FPR={out['challenge']['fpr']:.4f} "
        f"| avg={lat['avg_ms']:.3f}ms | params={num_params}"
    )
    return out


if __name__ == "__main__":
    train_and_evaluate()
