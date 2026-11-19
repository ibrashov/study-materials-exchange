"""Phase 7: Aggregate all model results, generate comparison tables, error analysis, and plots."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_moderation.config import FIGURES_DIR, REPORTS_DIR


def _load_results() -> dict:
    sk_path = REPORTS_DIR / "sklearn_results.json"
    cnn_path = REPORTS_DIR / "char_cnn_results.json"
    if not sk_path.is_file():
        raise FileNotFoundError(f"Missing {sk_path}; run train_models.py first.")
    data = json.loads(sk_path.read_text(encoding="utf-8"))
    if cnn_path.is_file():
        data["models"]["model_c_char_cnn"] = json.loads(cnn_path.read_text(encoding="utf-8"))
    return data


def _write_comparison_csv(data: dict) -> Path:
    out_csv = REPORTS_DIR / "model_comparison.csv"
    order = [
        "baseline_a_blacklist_substring",
        "baseline_a_blacklist_exact",
        "baseline_b_fuzzy_matching",
        "model_a_logreg",
        "model_b_linear_svm",
        "model_c_char_cnn",
        "model_d_hybrid",
    ]
    fields = [
        "model",
        "test_accuracy",
        "test_precision",
        "test_recall",
        "test_f1",
        "test_fpr",
        "test_fnr",
        "test_obfuscated_recall",
        "test_hard_neg_fpr",
        "test_en_f1",
        "test_ru_f1",
        "test_kk_f1",
        "challenge_f1",
        "challenge_obf_recall",
        "challenge_fpr",
        "challenge_hard_neg_fpr",
        "latency_avg_ms",
        "latency_p95_ms",
        "artifact_size_kb",
    ]
    rows = []
    for name in order:
        if name not in data["models"]:
            continue
        m = data["models"][name]
        t = m["test"]
        c = m["challenge"]
        langs = t.get("by_language", {})
        rows.append({
            "model": name,
            "test_accuracy": t["accuracy"],
            "test_precision": t["precision"],
            "test_recall": t["recall"],
            "test_f1": t["f1"],
            "test_fpr": t["fpr"],
            "test_fnr": t["fnr"],
            "test_obfuscated_recall": t.get("obfuscated_recall", 0.0),
            "test_hard_neg_fpr": t.get("hard_negative_fpr", 0.0),
            "test_en_f1": langs.get("en", {}).get("f1", 0.0),
            "test_ru_f1": langs.get("ru", {}).get("f1", 0.0),
            "test_kk_f1": langs.get("kk", {}).get("f1", 0.0),
            "challenge_f1": c["f1"],
            "challenge_obf_recall": c.get("obfuscated_recall", 0.0),
            "challenge_fpr": c["fpr"],
            "challenge_hard_neg_fpr": c.get("hard_negative_fpr", 0.0),
            "latency_avg_ms": m["latency_ms"]["avg_ms"],
            "latency_p95_ms": m["latency_ms"]["p95_ms"],
            "artifact_size_kb": m["artifact_size_kb"],
        })
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return out_csv


def _write_error_analysis(data: dict) -> Path:
    out_md = REPORTS_DIR / "error_analysis.md"
    prod = data["selected_production_model"]
    errs = data["error_analysis"]
    lines = [
        "# Error Analysis — Selected Production Model",
        "",
        f"- **Selected model:** `{prod['name']}` (`{prod['model_type']}`, v{prod['model_version']})",
        f"- **Validation-tuned threshold:** `{prod['threshold']:.4f}` (uncertain band lower bound: `{prod['uncertain_low']:.4f}`)",
        "",
        "## 1. Held-out Test Split Errors (`test.csv`)",
        f"- False Positives: **{len(errs['test']['false_positives'])}**",
        f"- False Negatives: **{len(errs['test']['false_negatives'])}**",
        "",
    ]
    if errs["test"]["false_positives"]:
        lines.append("### Sample False Positives (Test)")
        lines.append("| Filename | Language | Category | Normalized | Confidence |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in errs["test"]["false_positives"][:15]:
            lines.append(
                f"| `{item['filename']}` | {item['language']} | {item['category']} | `{item['normalized']}` | {item['confidence']:.4f} |"
            )
        lines.append("")
    if errs["test"]["false_negatives"]:
        lines.append("### Sample False Negatives (Test)")
        lines.append("| Filename | Language | Augmentation | Normalized | Confidence |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in errs["test"]["false_negatives"][:15]:
            lines.append(
                f"| `{item['filename']}` | {item['language']} | {item['augmentation_type']} | `{item['normalized']}` | {item['confidence']:.4f} |"
            )
        lines.append("")

    lines.extend([
        "## 2. Independent Challenge Test Set Errors (`challenge_test.csv`)",
        f"- False Positives: **{len(errs['challenge']['false_positives'])}**",
        f"- False Negatives: **{len(errs['challenge']['false_negatives'])}**",
        "",
    ])
    if errs["challenge"]["false_positives"]:
        lines.append("### False Positives (Challenge)")
        for item in errs["challenge"]["false_positives"]:
            lines.append(f"- `{item['filename']}` ({item['language']}, {item['category']}) -> norm `{item['normalized']}`, conf={item['confidence']:.4f}")
        lines.append("")
    if errs["challenge"]["false_negatives"]:
        lines.append("### False Negatives (Challenge)")
        for item in errs["challenge"]["false_negatives"]:
            lines.append(f"- `{item['filename']}` ({item['language']}, {item['augmentation_type']}) -> norm `{item['normalized']}`, conf={item['confidence']:.4f}")
        lines.append("")

    lines.extend([
        "## 3. Ambiguous Evaluation Cases (`ambiguous_eval.csv`)",
        "| Filename | Expected | Predicted | Confidence | Policy Zone | Normalized |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for item in data.get("ambiguous_eval", []):
        exp = "ALLOWED" if item["expected_label"] == 0 else "BLOCKED"
        pred = "ALLOWED" if item["predicted_allowed"] else "BLOCKED"
        lines.append(
            f"| `{item['filename']}` | {exp} | {pred} | {item['confidence']:.4f} | {item['policy_zone']} | `{item['normalized']}` |"
        )
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_md


def _generate_figures(data: dict) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib not available in this interpreter; skipping figure generation.")
        return []

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    short_labels = {
        "baseline_a_blacklist_substring": "Blacklist\n(Substring)",
        "baseline_a_blacklist_exact": "Blacklist\n(Exact)",
        "baseline_b_fuzzy_matching": "Fuzzy\nMatching",
        "model_a_logreg": "Model A\nLogReg",
        "model_b_linear_svm": "Model B\nLinear SVM",
        "model_c_char_cnn": "Model C\nChar-CNN",
        "model_d_hybrid": "Model D\nHybrid",
    }
    keys = [k for k in short_labels if k in data["models"]]

    # Figure 1: Model comparison on Challenge + Test (F1, Obfuscated Recall, Hard Negative FPR)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    x = np.arange(len(keys))
    w = 0.26

    for ax, split_key, title in [
        (axes[0], "test", "Held-out Test Split (Unseen Base Words)"),
        (axes[1], "challenge", "Challenge Test Set (Unseen Obfuscations + Hard Negs)"),
    ]:
        f1s = [data["models"][k][split_key]["f1"] * 100 for k in keys]
        obfs = [data["models"][k][split_key].get("obfuscated_recall", 0.0) * 100 for k in keys]
        fprs = [data["models"][k][split_key].get("hard_negative_fpr", 0.0) * 100 for k in keys]

        ax.bar(x - w, f1s, w, label="F1-score (%)", color="#2563eb")
        ax.bar(x, obfs, w, label="Obfuscated Recall (%)", color="#16a34a")
        ax.bar(x + w, fprs, w, label="Hard-Neg FPR (%)", color="#dc2626")
        ax.set_xticks(x)
        ax.set_xticklabels([short_labels[k] for k in keys], fontsize=8)
        ax.set_ylim(0, 108)
        ax.set_ylabel("Percentage (%)")
        ax.set_title(title)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.legend(fontsize=8)

    fig.tight_layout()
    p1 = FIGURES_DIR / "model_comparison.png"
    fig.savefig(p1, dpi=150)
    plt.close(fig)
    saved.append(str(p1))

    # Figure 2: Confusion Matrices for selected production model (Test & Challenge)
    sel = data["selected_production_model"]["name"]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2))
    for ax, split_key, title in [
        (axes[0], "test", f"{sel} — Test Split"),
        (axes[1], "challenge", f"{sel} — Challenge Set"),
    ]:
        cm = data["models"][sel][split_key]["confusion_matrix"]
        mat = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
        ax.imshow(mat, cmap="Blues")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred Allowed", "Pred Blocked"])
        ax.set_yticklabels(["True Allowed", "True Blocked"])
        ax.set_title(title)
        for i in range(2):
            for j in range(2):
                ax.text(j, i, str(mat[i, j]), ha="center", va="center", color="black", fontsize=12, fontweight="bold")
    fig.tight_layout()
    p2 = FIGURES_DIR / "confusion_matrix_production.png"
    fig.savefig(p2, dpi=150)
    plt.close(fig)
    saved.append(str(p2))

    # Figure 3: Multilingual performance (EN, RU, KK, Mixed) for selected production model
    langs = ["en", "ru", "kk", "mixed"]
    lang_labels = ["English", "Russian", "Kazakh", "Mixed"]
    test_lang = data["models"][sel]["test"]["by_language"]
    chal_lang = data["models"][sel]["challenge"]["by_language"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    lx = np.arange(len(langs))
    t_f1 = [test_lang.get(lang, {}).get("f1", 0.0) * 100 for lang in langs]
    c_f1 = [chal_lang.get(lang, {}).get("f1", 0.0) * 100 for lang in langs]
    t_fpr = [test_lang.get(lang, {}).get("fpr", 0.0) * 100 for lang in langs]
    ax.bar(lx - 0.25, t_f1, 0.25, label="Test F1 (%)", color="#2563eb")
    ax.bar(lx, c_f1, 0.25, label="Challenge F1 (%)", color="#0d9488")
    ax.bar(lx + 0.25, t_fpr, 0.25, label="Test FPR (%)", color="#dc2626")
    ax.set_xticks(lx)
    ax.set_xticklabels(lang_labels)
    ax.set_ylim(0, 108)
    ax.set_ylabel("Percentage (%)")
    ax.set_title(f"Multilingual Performance — {sel}")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend()
    fig.tight_layout()
    p3 = FIGURES_DIR / "language_performance.png"
    fig.savefig(p3, dpi=150)
    plt.close(fig)
    saved.append(str(p3))

    # Figure 4: Feature Ablation (Raw vs Normalized vs Combined)
    ab = data.get("feature_ablation", {})
    if ab:
        modes = ["raw", "normalized", "combined"]
        fig, ax = plt.subplots(figsize=(7.5, 4.2))
        mx = np.arange(len(modes))
        ax.bar(mx - 0.2, [ab[m]["test"]["f1"] * 100 for m in modes], 0.2, label="Test F1 (%)", color="#2563eb")
        ax.bar(mx, [ab[m]["challenge"]["f1"] * 100 for m in modes], 0.2, label="Challenge F1 (%)", color="#16a34a")
        ax.bar(mx + 0.2, [ab[m]["challenge"].get("obfuscated_recall", 0) * 100 for m in modes], 0.2, label="Challenge Obf Recall (%)", color="#f59e0b")
        ax.set_xticks(mx)
        ax.set_xticklabels(["Raw Only", "Normalized Only", "Combined (Raw+Norm+Signals)"])
        ax.set_ylim(0, 108)
        ax.set_ylabel("Percentage (%)")
        ax.set_title("Phase 4 Feature Ablation (Logistic Regression)")
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.legend()
        fig.tight_layout()
        p4 = FIGURES_DIR / "ablation_features.png"
        fig.savefig(p4, dpi=150)
        plt.close(fig)
        saved.append(str(p4))

    return saved


def main() -> None:
    data = _load_results()
    metrics_path = REPORTS_DIR / "metrics.json"
    metrics_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = _write_comparison_csv(data)
    err_path = _write_error_analysis(data)
    figs = _generate_figures(data)
    print("Wrote:", metrics_path, csv_path, err_path)
    print("Figures:", figs)


if __name__ == "__main__":
    main()
