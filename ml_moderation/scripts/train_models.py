"""Phase 6: Train Baselines, Feature Ablation, Model A (LogReg), Model B (Linear SVM), and Model D (Hybrid).

All hyperparameter and threshold selection is performed strictly on `val.csv`.
`test.csv` and `challenge_test.csv` are never used during training or tuning.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import time
import tracemalloc

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_moderation.baseline import BlacklistModerator, FuzzyMatchingModerator
from ml_moderation.config import (
    DEFAULT_MODEL_PATH,
    GENERATED_DIR,
    MODEL_VERSION,
    MODELS_DIR,
    RANDOM_SEED,
    REPORTS_DIR,
)
from ml_moderation.features import FilenameFeatureExtractor
from ml_moderation.normalization import normalize_text
from ml_moderation.predictor import FilenameModerator


def load_split(name: str) -> list[dict[str, str]]:
    path = GENERATED_DIR / f"{name}.csv"
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def extract_train_vocabularies(train_rows: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    """Extract profanity terms and clean single-word hard negatives strictly from train.csv."""
    prof_terms: set[str] = set()
    safe_single_words: set[str] = set()
    for row in train_rows:
        label = int(row["label"])
        cat = row["category"]
        norm = normalize_text(row["filename"])
        if label == 1 and cat == "explicit_profanity" and row["augmentation_type"] == "none":
            tokens = norm.normalized.split()
            if len(tokens) == 1 and len(tokens[0]) >= 3:
                prof_terms.add(tokens[0])
        elif label == 0 and cat == "hard_negative":
            tokens = norm.normalized.split()
            if len(tokens) == 1 and len(tokens[0]) >= 3:
                safe_single_words.add(tokens[0])
    # Ensure safety: never allow a known train hard-negative single word in prof_terms.
    prof_terms -= safe_single_words
    return sorted(prof_terms), sorted(safe_single_words)


def tune_threshold(y_true: np.ndarray, probs: np.ndarray, max_fpr: float = 0.008) -> dict[str, float]:
    """Select decision threshold on validation set maximizing F1 subject to FPR <= max_fpr."""
    best = {"threshold": 0.5, "f1": -1.0, "fpr": 1.0, "recall": 0.0, "precision": 0.0}
    fallback = {"threshold": 0.5, "f1": -1.0, "fpr": 1.0, "recall": 0.0, "precision": 0.0}

    neg_mask = y_true == 0
    for th in np.linspace(0.15, 0.99, 169):
        preds = (probs >= th).astype(int)
        fp = int(np.sum((preds == 1) & neg_mask))
        fpr = fp / max(int(np.sum(neg_mask)), 1)
        f1 = float(f1_score(y_true, preds, zero_division=0))
        rec = float(recall_score(y_true, preds, zero_division=0))
        prec = float(precision_score(y_true, preds, zero_division=0))
        if f1 > fallback["f1"]:
            fallback = {"threshold": float(th), "f1": f1, "fpr": fpr, "recall": rec, "precision": prec}
        if fpr <= max_fpr and f1 > best["f1"]:
            best = {"threshold": float(th), "f1": f1, "fpr": fpr, "recall": rec, "precision": prec}
    return best if best["f1"] >= 0 else fallback


def compute_detailed_metrics(
    rows: list[dict[str, str]],
    preds: list[int],
    probs: list[float] | None = None,
) -> dict:
    """Compute comprehensive metrics across overall, obfuscated, hard negatives, and languages."""
    y_true = np.array([int(r["label"]) for r in rows], dtype=int)
    y_pred = np.array(preds, dtype=int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = fp / max(fp + tn, 1)
    fnr = fn / max(fn + tp, 1)

    metrics: dict = {
        "count": int(len(rows)),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 6),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 6),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 6),
        "fpr": round(float(fpr), 6),
        "fnr": round(float(fnr), 6),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }

    # Category-specific metrics
    obf_idx = [i for i, r in enumerate(rows) if r["category"] == "obfuscated_profanity"]
    if obf_idx:
        obf_rec = float(np.mean(y_pred[obf_idx] == 1))
        metrics["obfuscated_recall"] = round(obf_rec, 6)
        metrics["obfuscated_count"] = len(obf_idx)

    exp_idx = [i for i, r in enumerate(rows) if r["category"] == "explicit_profanity"]
    if exp_idx:
        metrics["explicit_recall"] = round(float(np.mean(y_pred[exp_idx] == 1)), 6)

    hn_idx = [i for i, r in enumerate(rows) if r["category"] == "hard_negative"]
    if hn_idx:
        metrics["hard_negative_fpr"] = round(float(np.mean(y_pred[hn_idx] == 1)), 6)
        metrics["hard_negative_count"] = len(hn_idx)

    clean_idx = [i for i, r in enumerate(rows) if r["category"] == "clean_academic"]
    if clean_idx:
        metrics["clean_academic_fpr"] = round(float(np.mean(y_pred[clean_idx] == 1)), 6)

    # Language breakdown
    by_lang: dict[str, dict] = {}
    for lang in ("en", "ru", "kk", "mixed"):
        l_idx = [i for i, r in enumerate(rows) if r["language"] == lang]
        if not l_idx:
            continue
        yt = y_true[l_idx]
        yp = y_pred[l_idx]
        l_tn, l_fp, l_fn, l_tp = confusion_matrix(yt, yp, labels=[0, 1]).ravel()
        by_lang[lang] = {
            "count": len(l_idx),
            "accuracy": round(float(accuracy_score(yt, yp)), 6),
            "precision": round(float(precision_score(yt, yp, zero_division=0)), 6),
            "recall": round(float(recall_score(yt, yp, zero_division=0)), 6),
            "f1": round(float(f1_score(yt, yp, zero_division=0)), 6),
            "fpr": round(float(l_fp / max(l_fp + l_tn, 1)), 6),
        }
    metrics["by_language"] = by_lang
    return metrics


def measure_latency_ms(predict_fn, sample_texts: list[str], warmup: int = 30) -> dict[str, float]:
    """Measure warm per-item single-request inference latency (average and p95 in ms)."""
    for txt in sample_texts[:warmup]:
        predict_fn(txt)
    timings: list[float] = []
    for txt in sample_texts:
        t0 = time.perf_counter()
        predict_fn(txt)
        timings.append((time.perf_counter() - t0) * 1000.0)
    arr = np.asarray(timings, dtype=np.float64)
    return {
        "avg_ms": round(float(np.mean(arr)), 4),
        "p50_ms": round(float(np.percentile(arr, 50)), 4),
        "p95_ms": round(float(np.percentile(arr, 95)), 4),
        "max_ms": round(float(np.max(arr)), 4),
    }


def _fit_platt_scaling(val_scores: np.ndarray, y_val: np.ndarray) -> tuple[float, float]:
    """Fit 1D Platt sigmoid calibration on validation decision scores."""
    cal = LogisticRegression(C=10.0, solver="lbfgs", random_state=RANDOM_SEED)
    cal.fit(val_scores.reshape(-1, 1), y_val)
    return float(cal.coef_[0, 0]), float(cal.intercept_[0])


def build_portable_artifact(
    model_type: str,
    extractor: FilenameFeatureExtractor,
    coef: np.ndarray,
    intercept: float,
    threshold: float,
    platt_a: float = 1.0,
    platt_b: float = 0.0,
    hybrid_exact_terms: list[str] | None = None,
    safe_exact_words: list[str] | None = None,
    metadata: dict | None = None,
) -> dict:
    """Create a Python/sklearn-version-agnostic portable dictionary artifact."""
    artifact = extractor.export_portable()
    artifact.update({
        "artifact_format": "portable_linear_v1",
        "model_type": model_type,
        "model_version": MODEL_VERSION,
        "coef": np.asarray(coef, dtype=np.float32).ravel(),
        "intercept": float(intercept),
        "platt_a": float(platt_a),
        "platt_b": float(platt_b),
        "threshold": float(threshold),
        "uncertain_low": float(max(0.25, threshold - 0.12)),
        "uncertain_high": float(min(0.95, threshold + 0.10)),
        "hybrid_exact_terms": sorted(set(hybrid_exact_terms or ())),
        "safe_exact_words": sorted(set(safe_exact_words or ())),
        "metadata": metadata or {},
    })
    return artifact


def run_training_pipeline() -> dict:
    train_rows = load_split("train")
    val_rows = load_split("val")
    test_rows = load_split("test")
    challenge_rows = load_split("challenge_test")
    ambiguous_rows = load_split("ambiguous_eval")

    train_texts = [r["filename"] for r in train_rows]
    y_train = np.array([int(r["label"]) for r in train_rows], dtype=int)
    val_texts = [r["filename"] for r in val_rows]
    y_val = np.array([int(r["label"]) for r in val_rows], dtype=int)
    test_texts = [r["filename"] for r in test_rows]
    challenge_texts = [r["filename"] for r in challenge_rows]

    train_prof_terms, train_safe_words = extract_train_vocabularies(train_rows)
    latency_probe = test_texts[:300]

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    exp_models_dir = REPORTS_DIR / "experimental_models"
    exp_models_dir.mkdir(parents=True, exist_ok=True)

    results: dict = {
        "model_version": MODEL_VERSION,
        "seed": RANDOM_SEED,
        "train_prof_vocab_size": len(train_prof_terms),
        "feature_ablation": {},
        "models": {},
    }

    # ------------------------------------------------------------------
    # Phase 4: Raw vs Normalized vs Combined Feature Ablation (on Model A)
    # ------------------------------------------------------------------
    print("Running Phase 4 feature ablation (raw vs normalized vs combined)...")
    for mode in ("raw", "normalized", "combined"):
        ext = FilenameFeatureExtractor(mode=mode)
        X_tr = ext.fit_transform(train_texts)
        X_va = ext.transform(val_texts)
        X_te = ext.transform(test_texts)
        X_ch = ext.transform(challenge_texts)

        clf = LogisticRegression(C=4.0, class_weight="balanced", max_iter=1000, random_state=RANDOM_SEED)
        clf.fit(X_tr, y_train)
        val_probs = clf.predict_proba(X_va)[:, 1]
        tuned = tune_threshold(y_val, val_probs, max_fpr=0.008)
        th = tuned["threshold"]

        test_preds = (clf.predict_proba(X_te)[:, 1] >= th).astype(int).tolist()
        chal_preds = (clf.predict_proba(X_ch)[:, 1] >= th).astype(int).tolist()
        results["feature_ablation"][mode] = {
            "num_features": int(X_tr.shape[1]),
            "val_threshold": round(th, 4),
            "val_f1": round(tuned["f1"], 6),
            "val_fpr": round(tuned["fpr"], 6),
            "test": compute_detailed_metrics(test_rows, test_preds),
            "challenge": compute_detailed_metrics(challenge_rows, chal_preds),
        }

    # ------------------------------------------------------------------
    # Phase 5: Baselines (strictly using train-only profanity terms)
    # ------------------------------------------------------------------
    print("Evaluating Phase 5 baselines...")
    for b_name, b_mod in [
        ("baseline_a_blacklist_substring", BlacklistModerator(train_prof_terms, match_mode="substring")),
        ("baseline_a_blacklist_exact", BlacklistModerator(train_prof_terms, match_mode="exact")),
        ("baseline_b_fuzzy_matching", FuzzyMatchingModerator(train_prof_terms, similarity_threshold=0.84)),
    ]:
        test_preds = b_mod.predict(test_texts)
        chal_preds = b_mod.predict(challenge_texts)
        lat = measure_latency_ms(b_mod.predict_one, latency_probe[:120] if "fuzzy" in b_name else latency_probe)
        results["models"][b_name] = {
            "description": b_name,
            "threshold": 0.84 if "fuzzy" in b_name else 1.0,
            "artifact_size_kb": round(len("\n".join(train_prof_terms).encode("utf-8")) / 1024.0, 2),
            "latency_ms": lat,
            "test": compute_detailed_metrics(test_rows, test_preds),
            "challenge": compute_detailed_metrics(challenge_rows, chal_preds),
        }

    # ------------------------------------------------------------------
    # Shared combined feature extraction for Model A, Model B, Model D
    # ------------------------------------------------------------------
    print("Extracting combined character n-gram TF-IDF + signal features...")
    extractor = FilenameFeatureExtractor(mode="combined", ngram_range=(2, 5), max_features_raw=12000, max_features_norm=18000)
    X_train = extractor.fit_transform(train_texts)
    X_val = extractor.transform(val_texts)
    X_test = extractor.transform(test_texts)

    # ------------------------------------------------------------------
    # Model A: Character TF-IDF + Logistic Regression
    # ------------------------------------------------------------------
    print("Training Model A (Char TF-IDF + Logistic Regression)...")
    best_lr = None
    best_lr_cfg = None
    for c_val in (0.5, 1.0, 2.0, 4.0, 8.0):
        clf = LogisticRegression(C=c_val, class_weight="balanced", max_iter=1000, random_state=RANDOM_SEED)
        clf.fit(X_train, y_train)
        v_probs = clf.predict_proba(X_val)[:, 1]
        tuned = tune_threshold(y_val, v_probs, max_fpr=0.008)
        if best_lr_cfg is None or tuned["f1"] > best_lr_cfg["f1"]:
            best_lr = clf
            best_lr_cfg = {"C": c_val, **tuned}

    assert best_lr is not None and best_lr_cfg is not None
    lr_artifact = build_portable_artifact(
        model_type="char_tfidf_logreg",
        extractor=extractor,
        coef=best_lr.coef_[0],
        intercept=float(best_lr.intercept_[0]),
        threshold=best_lr_cfg["threshold"],
        metadata={"C": best_lr_cfg["C"], "val_f1": best_lr_cfg["f1"], "val_fpr": best_lr_cfg["fpr"]},
    )
    lr_path = exp_models_dir / "model_a_logreg.joblib"
    joblib.dump(lr_artifact, lr_path, compress=3, protocol=4)

    # Verify portable dot-product parity against scikit-learn predict_proba
    sklearn_sample_probs = best_lr.predict_proba(X_test[:50])[:, 1]
    lr_mod = FilenameModerator(lr_path)
    portable_sample_probs = np.array([lr_mod.predict_proba_one(t) for t in test_texts[:50]])
    max_parity_diff = float(np.max(np.abs(sklearn_sample_probs - portable_sample_probs)))
    assert max_parity_diff < 1e-4, f"Portable parity drift too high: {max_parity_diff}"

    lr_test_dec = [lr_mod.moderate(t) for t in test_texts]
    lr_chal_dec = [lr_mod.moderate(t) for t in challenge_texts]
    lr_lat = measure_latency_ms(lr_mod.moderate, latency_probe)
    results["models"]["model_a_logreg"] = {
        "description": "Character TF-IDF (2-5, raw+norm+signals) + Logistic Regression",
        "best_params": {"C": best_lr_cfg["C"]},
        "threshold": round(best_lr_cfg["threshold"], 4),
        "val_f1": round(best_lr_cfg["f1"], 6),
        "val_fpr": round(best_lr_cfg["fpr"], 6),
        "portable_parity_max_diff": round(max_parity_diff, 8),
        "artifact_size_kb": round(lr_path.stat().st_size / 1024.0, 2),
        "latency_ms": lr_lat,
        "test": compute_detailed_metrics(test_rows, [0 if d.allowed else 1 for d in lr_test_dec]),
        "challenge": compute_detailed_metrics(challenge_rows, [0 if d.allowed else 1 for d in lr_chal_dec]),
    }

    # ------------------------------------------------------------------
    # Model B: Character TF-IDF + Calibrated Linear SVM
    # ------------------------------------------------------------------
    print("Training Model B (Char TF-IDF + Calibrated Linear SVM)...")
    best_svm = None
    best_svm_cfg = None
    for c_val in (0.25, 0.5, 1.0, 2.0):
        svm = LinearSVC(C=c_val, class_weight="balanced", max_iter=3000, random_state=RANDOM_SEED)
        svm.fit(X_train, y_train)
        v_scores = svm.decision_function(X_val)
        pa, pb = _fit_platt_scaling(v_scores, y_val)
        v_probs = 1.0 / (1.0 + np.exp(-(pa * v_scores + pb)))
        tuned = tune_threshold(y_val, v_probs, max_fpr=0.008)
        if best_svm_cfg is None or tuned["f1"] > best_svm_cfg["f1"]:
            best_svm = svm
            best_svm_cfg = {"C": c_val, "platt_a": pa, "platt_b": pb, **tuned}

    assert best_svm is not None and best_svm_cfg is not None
    svm_artifact = build_portable_artifact(
        model_type="char_tfidf_linear_svm",
        extractor=extractor,
        coef=best_svm.coef_[0],
        intercept=float(best_svm.intercept_[0]),
        threshold=best_svm_cfg["threshold"],
        platt_a=best_svm_cfg["platt_a"],
        platt_b=best_svm_cfg["platt_b"],
        metadata={"C": best_svm_cfg["C"], "val_f1": best_svm_cfg["f1"], "val_fpr": best_svm_cfg["fpr"]},
    )
    svm_path = exp_models_dir / "model_b_linear_svm.joblib"
    joblib.dump(svm_artifact, svm_path, compress=3, protocol=4)

    svm_mod = FilenameModerator(svm_path)
    svm_test_dec = [svm_mod.moderate(t) for t in test_texts]
    svm_chal_dec = [svm_mod.moderate(t) for t in challenge_texts]
    svm_lat = measure_latency_ms(svm_mod.moderate, latency_probe)
    results["models"]["model_b_linear_svm"] = {
        "description": "Character TF-IDF (2-5, raw+norm+signals) + Calibrated Linear SVM",
        "best_params": {"C": best_svm_cfg["C"]},
        "threshold": round(best_svm_cfg["threshold"], 4),
        "val_f1": round(best_svm_cfg["f1"], 6),
        "val_fpr": round(best_svm_cfg["fpr"], 6),
        "artifact_size_kb": round(svm_path.stat().st_size / 1024.0, 2),
        "latency_ms": svm_lat,
        "test": compute_detailed_metrics(test_rows, [0 if d.allowed else 1 for d in svm_test_dec]),
        "challenge": compute_detailed_metrics(challenge_rows, [0 if d.allowed else 1 for d in svm_chal_dec]),
    }

    # ------------------------------------------------------------------
    # Model D: Hybrid (Normalization + Deterministic High-Precision Exact Check + Best Linear ML)
    # ------------------------------------------------------------------
    print("Training Model D (Hybrid: Normalization + Exact Deobfuscated Check + Best Linear ML)...")
    base_is_svm = best_svm_cfg["f1"] > best_lr_cfg["f1"]
    base_artifact = svm_artifact if base_is_svm else lr_artifact
    base_name = "linear_svm" if base_is_svm else "logreg"

    # Build Hybrid using strictly train-split profanity terms + safe hard negatives
    hybrid_artifact = dict(base_artifact)
    hybrid_artifact["model_type"] = f"hybrid_{base_name}"
    hybrid_artifact["hybrid_exact_terms"] = train_prof_terms
    hybrid_artifact["safe_exact_words"] = train_safe_words

    # Re-tune threshold on val.csv with hybrid probabilities
    hybrid_path = exp_models_dir / "model_d_hybrid.joblib"
    joblib.dump(hybrid_artifact, hybrid_path, compress=3, protocol=4)
    hyb_mod = FilenameModerator(hybrid_path)
    hyb_val_probs = np.array([hyb_mod.predict_proba_one(t) for t in val_texts])
    hyb_tuned = tune_threshold(y_val, hyb_val_probs, max_fpr=0.008)
    hybrid_artifact["threshold"] = float(hyb_tuned["threshold"])
    hybrid_artifact["uncertain_low"] = float(max(0.25, hyb_tuned["threshold"] - 0.12))
    hybrid_artifact["uncertain_high"] = float(min(0.95, hyb_tuned["threshold"] + 0.10))
    joblib.dump(hybrid_artifact, hybrid_path, compress=3, protocol=4)

    hyb_mod = FilenameModerator(hybrid_path)
    hyb_test_dec = [hyb_mod.moderate(t) for t in test_texts]
    hyb_chal_dec = [hyb_mod.moderate(t) for t in challenge_texts]
    hyb_lat = measure_latency_ms(hyb_mod.moderate, latency_probe)
    results["models"]["model_d_hybrid"] = {
        "description": f"Hybrid: Normalization + Exact Deobfuscated Check + {base_name}",
        "base_ml_model": base_name,
        "threshold": round(hyb_tuned["threshold"], 4),
        "val_f1": round(hyb_tuned["f1"], 6),
        "val_fpr": round(hyb_tuned["fpr"], 6),
        "artifact_size_kb": round(hybrid_path.stat().st_size / 1024.0, 2),
        "latency_ms": hyb_lat,
        "test": compute_detailed_metrics(test_rows, [0 if d.allowed else 1 for d in hyb_test_dec]),
        "challenge": compute_detailed_metrics(challenge_rows, [0 if d.allowed else 1 for d in hyb_chal_dec]),
    }

    # ------------------------------------------------------------------
    # Select best lightweight production model based on validation & generalization
    # ------------------------------------------------------------------
    candidates = [
        ("model_a_logreg", lr_path),
        ("model_b_linear_svm", svm_path),
        ("model_d_hybrid", hybrid_path),
    ]

    def score_candidate(name: str) -> float:
        m = results["models"][name]
        penalty = max(0.0, m["val_fpr"] - 0.008) * 5.0
        # Slight preference for Hybrid when it matches or improves validation F1
        # because deterministic deobfuscated exact-token verification reduces FN on unseen forms.
        hybrid_bonus = 0.0005 if name == "model_d_hybrid" else 0.0
        return float(m["val_f1"]) - penalty + hybrid_bonus

    selected_name, selected_src_path = max(candidates, key=lambda item: score_candidate(item[0]))

    # Production refit: after honest train/val/test model selection is complete,
    # refit the chosen architecture with its validation-fixed hyperparameters on the full
    # main dataset (train + val + test) so production covers the entire curated multilingual
    # vocabulary while `challenge_test.csv` remains 100% unseen.
    full_rows = train_rows + val_rows + test_rows
    full_texts = [r["filename"] for r in full_rows]
    y_full = np.array([int(r["label"]) for r in full_rows], dtype=int)
    full_prof_terms, full_safe_words = extract_train_vocabularies(full_rows)

    full_extractor = FilenameFeatureExtractor(
        mode="combined", ngram_range=(2, 5), max_features_raw=12000, max_features_norm=18000
    )
    X_full = full_extractor.fit_transform(full_texts)

    if selected_name == "model_b_linear_svm" or (selected_name == "model_d_hybrid" and base_is_svm):
        refit_svm = LinearSVC(
            C=best_svm_cfg["C"], class_weight="balanced", max_iter=3000, random_state=RANDOM_SEED
        )
        refit_svm.fit(X_full, y_full)
        prod_artifact = build_portable_artifact(
            model_type=f"{'hybrid_' if selected_name == 'model_d_hybrid' else ''}char_tfidf_linear_svm",
            extractor=full_extractor,
            coef=refit_svm.coef_[0],
            intercept=float(refit_svm.intercept_[0]),
            threshold=float(hyb_tuned["threshold"] if selected_name == "model_d_hybrid" else best_svm_cfg["threshold"]),
            platt_a=best_svm_cfg["platt_a"],
            platt_b=best_svm_cfg["platt_b"],
            hybrid_exact_terms=full_prof_terms if selected_name == "model_d_hybrid" else None,
            safe_exact_words=full_safe_words if selected_name == "model_d_hybrid" else None,
            metadata={"C": best_svm_cfg["C"], "refit_samples": len(full_rows), "selected_via": "val_f1_fpr"},
        )
    else:
        refit_lr = LogisticRegression(
            C=best_lr_cfg["C"], class_weight="balanced", max_iter=1000, random_state=RANDOM_SEED
        )
        refit_lr.fit(X_full, y_full)
        prod_artifact = build_portable_artifact(
            model_type=f"{'hybrid_' if selected_name == 'model_d_hybrid' else ''}char_tfidf_logreg",
            extractor=full_extractor,
            coef=refit_lr.coef_[0],
            intercept=float(refit_lr.intercept_[0]),
            threshold=float(hyb_tuned["threshold"] if selected_name == "model_d_hybrid" else best_lr_cfg["threshold"]),
            hybrid_exact_terms=full_prof_terms if selected_name == "model_d_hybrid" else None,
            safe_exact_words=full_safe_words if selected_name == "model_d_hybrid" else None,
            metadata={"C": best_lr_cfg["C"], "refit_samples": len(full_rows), "selected_via": "val_f1_fpr"},
        )

    joblib.dump(prod_artifact, DEFAULT_MODEL_PATH, compress=3, protocol=4)

    # Measure Python tracemalloc memory delta of loading the production model
    tracemalloc.start()
    before_cur, _ = tracemalloc.get_traced_memory()
    prod_mod = FilenameModerator(DEFAULT_MODEL_PATH)
    after_cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    prod_chal_dec = [prod_mod.moderate(t) for t in challenge_texts]
    prod_chal_metrics = compute_detailed_metrics(challenge_rows, [0 if d.allowed else 1 for d in prod_chal_dec])
    prod_lat = measure_latency_ms(prod_mod.moderate, latency_probe)

    results["selected_production_model"] = {
        "name": selected_name,
        "model_type": prod_mod.model_type,
        "model_version": prod_mod.model_version,
        "artifact_path": str(DEFAULT_MODEL_PATH.relative_to(ROOT)).replace("\\", "/"),
        "artifact_size_kb": round(DEFAULT_MODEL_PATH.stat().st_size / 1024.0, 2),
        "traced_memory_mb": round((after_cur - before_cur) / (1024 * 1024), 3),
        "traced_peak_mb": round(peak / (1024 * 1024), 3),
        "threshold": prod_mod.threshold,
        "uncertain_low": prod_mod.uncertain_low,
        "refit_samples": len(full_rows),
        "latency_ms": prod_lat,
        "unseen_challenge_metrics": prod_chal_metrics,
    }

    # Evaluate ambiguous set for transparent reporting
    amb_report = []
    for row in ambiguous_rows:
        dec = prod_mod.moderate(row["filename"])
        amb_report.append({
            "filename": row["filename"],
            "expected_label": int(row["label"]),
            "predicted_allowed": dec.allowed,
            "confidence": round(dec.confidence, 4),
            "policy_zone": dec.policy_zone,
            "normalized": dec.normalized_text,
        })
    results["ambiguous_eval"] = amb_report

    # Collect error samples: train-only selected model on held-out test, refit model on unseen challenge.
    eval_test_mod = FilenameModerator(selected_src_path)

    def collect_errors(mod: FilenameModerator, rows: list[dict[str, str]]) -> dict[str, list[dict]]:
        fps, fns = [], []
        for row in rows:
            dec = mod.moderate(row["filename"])
            pred = 0 if dec.allowed else 1
            truth = int(row["label"])
            if pred == 1 and truth == 0:
                fps.append({
                    "filename": row["filename"],
                    "language": row["language"],
                    "category": row["category"],
                    "normalized": dec.normalized_text,
                    "confidence": round(dec.confidence, 4),
                })
            elif pred == 0 and truth == 1:
                fns.append({
                    "filename": row["filename"],
                    "language": row["language"],
                    "category": row["category"],
                    "augmentation_type": row["augmentation_type"],
                    "normalized": dec.normalized_text,
                    "confidence": round(dec.confidence, 4),
                })
        return {"false_positives": fps, "false_negatives": fns}

    results["error_analysis"] = {
        "test": collect_errors(eval_test_mod, test_rows),
        "challenge": collect_errors(prod_mod, challenge_rows),
    }

    out_json = REPORTS_DIR / "sklearn_results.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved results to {out_json}")
    print(f"Selected production model: {selected_name} -> {DEFAULT_MODEL_PATH} ({results['selected_production_model']['artifact_size_kb']} KB)")
    return results


if __name__ == "__main__":
    res = run_training_pipeline()
    for name, info in res["models"].items():
        t = info["test"]
        c = info["challenge"]
        print(
            f"{name:32s} | TEST F1={t['f1']:.4f} ObfRec={t.get('obfuscated_recall', 0):.4f} FPR={t['fpr']:.4f} "
            f"| CHAL F1={c['f1']:.4f} ObfRec={c.get('obfuscated_recall', 0):.4f} FPR={c['fpr']:.4f} "
            f"| avg={info['latency_ms']['avg_ms']:.3f}ms"
        )
