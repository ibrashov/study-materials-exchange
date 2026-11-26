"""Render the Phase 2 measurements as PNGs."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ml_moderation.scripts.semantic_phase2 import REPORT

FIGURES = REPORT.parent / "figures"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGURES / f"{name}.png", dpi=145)
    plt.close(fig)


def bars(names, values, title, ylabel, file):
    fig, ax = plt.subplots(figsize=(9, max(3, len(names) * .37)))
    ax.barh(names, values, color="#177e89")
    ax.invert_yaxis()
    ax.set(title=title, xlabel=ylabel)
    save(fig, file)


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    data = read(REPORT / "independent_metrics.json")
    models = data["models"]
    focus = ["keyword", "v2_0", "e5_semantic_lr", "minilm_course_cosine", "minilm_semantic_lr"]
    for metric, title in (
        ("macro_f1", "Independent binary relevance"),
        ("paraphrase_acceptance", "Acceptance of unfamiliar paraphrases"),
        ("hard_negative_detection", "Explicit rejection of paired hard negatives"),
    ):
        bars(list(models), [models[m][metric] for m in models], title, "Fraction", metric)
    fig, axes = plt.subplots(1, len(focus), figsize=(14, 3.5), sharey=True)
    for ax, key in zip(axes, focus):
        matrix = np.array(models[key]["confusion_matrix"])
        ax.imshow(matrix, vmin=0, vmax=168, cmap="Blues")
        for (row, col), value in np.ndenumerate(matrix):
            ax.text(col, row, str(value), ha="center", va="center", color="white" if value > 90 else "black")
        ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Other", "Accept"],
               yticklabels=["Irrelevant", "Relevant"], title=key.replace("_", "\n", 1))
    save(fig, "confusion_matrices")
    historical = read(REPORT.parent / "metrics.json")["relevance"]["hybrid_logistic"]["f1"]
    bars(["V2.0 synthetic", "V2.0 independent"], [historical, models["v2_0"]["positive_f1"]],
         "V2.0 positive-class F1 by evaluation set", "F1", "synthetic_vs_independent")
    fig, ax = plt.subplots(figsize=(9, 4))
    langs = ("en", "ru", "kk", "mixed")
    for key in focus:
        ax.plot(langs, [models[key]["by_language"][lang]["macro_f1"] for lang in langs], "o-", label=key)
    ax.set(title="Independent performance by title language", ylabel="Macro F1", ylim=(0, 1))
    ax.legend(fontsize=8)
    save(fig, "language")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, name in zip(axes, ("e5", "minilm")):
        for kind in ("course_cosine", "topic_cosine"):
            curve = data["threshold_curves"][f"{name}_{kind}"]
            ax.plot([row["threshold"] for row in curve], [row["macro_f1"] for row in curve], label=kind)
        ax.set(title=name, xlabel="Cosine cutoff (development only)", ylabel="Macro F1")
        ax.legend(fontsize=8)
    save(fig, "thresholds")
    names = ["v2_0", "e5", "minilm"]
    sizes = [32_150, *[data["artifacts"][m]["weights_bytes"] for m in names[1:]]]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.barh(names, np.array(sizes) / 2**20, color="#177e89")
    ax.set(xscale="log", xlabel="Artifact size (MiB, log scale)", title="Inference weights")
    save(fig, "model_size")
    bench = [read(REPORT / f"benchmark_{m}.json") for m in names]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(names, [m["rss_bytes"]["loaded"] / 2**20 for m in bench], color="#177e89")
    axes[0].axhline(512, color="#9c3022", linestyle="--", label="512 MiB reference")
    axes[0].set(ylabel="Working set in MiB", title="Local backend process")
    axes[0].legend(fontsize=8)
    axes[1].bar(names, [m["p95_ms"] for m in bench], color="#177e89")
    axes[1].set(ylabel="Milliseconds", title="Warm combined p95")
    save(fig, "resources")


if __name__ == "__main__":
    main()
