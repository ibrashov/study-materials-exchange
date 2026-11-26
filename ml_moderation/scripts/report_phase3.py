"""Benchmark the integrated static student and render Phase 3 comparisons."""
import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter, process_time
from types import SimpleNamespace

import numpy as np

from ml_moderation.validator_v2 import ROOT

OUT = ROOT / "reports/week13/phase3"


def benchmark():
    import psutil
    from backend.app.main import app
    from backend.app.services.moderation import enforce_material_moderation
    from backend.app.services.title_validation import enforce_title_validation

    os.environ.update(MATERIAL_VALIDATOR_V2_ENABLED="true", MATERIAL_VALIDATOR_V2_MODEL="v2_2",
                      MATERIAL_VALIDATOR_V2_2_MODE="shadow")
    process = psutil.Process()
    course = SimpleNamespace(course_name="Database Systems", course_code="DB101", description=None)
    title = "SQL Joins and Queries"
    def validate():
        start = perf_counter()
        enforce_material_moderation(title=title, filename="document_123.pdf")
        enforce_title_validation(title, course)
        return (perf_counter() - start) * 1000

    startup = process.memory_info()
    first = validate()
    loaded = process.memory_info()
    cpu_start, start = process_time(), perf_counter()
    samples = [validate() for _ in range(120)]
    cpu = (process_time() - cpu_start) / (perf_counter() - start)
    start = perf_counter()
    with ThreadPoolExecutor(max_workers=4) as executor:
        concurrent = list(executor.map(lambda _: validate(), range(120)))
    elapsed = perf_counter() - start
    end = process.memory_info()
    result = {"routes": len(app.routes), "app_imported_rss_bytes": startup.rss,
              "app_imported_peak_bytes": getattr(startup, "peak_wset", None), "startup_peak_bytes": getattr(loaded, "peak_wset", None),
              "all_models_loaded_rss_bytes": loaded.rss, "final_rss_bytes": end.rss,
              "peak_working_set_bytes": getattr(end, "peak_wset", None),
              "cold_first_ms": first, "p50_ms": float(np.median(samples)), "p95_ms": float(np.percentile(samples, 95)),
              "concurrent_p95_ms": float(np.percentile(concurrent, 95)), "concurrent_per_second": len(concurrent) / elapsed,
              "mean_cpu_core_equivalents": cpu}
    (OUT / "benchmark.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")


def plots():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    metrics = json.loads((OUT / "metrics.json").read_text(encoding="utf8"))
    profile = json.loads((OUT / "benchmark.json").read_text(encoding="utf8"))
    selected = metrics["selection"]
    figures = OUT / "figures"
    figures.mkdir(exist_ok=True)
    names = ["v2_0", "v2_1_e5", "v2_1_minilm", "student_cosine", "student_lr", "student_hybrid", "student_soft"]
    positions = np.arange(len(names))
    for key, label in (("macro_f1", "Macro F1"), ("paraphrase_acceptance", "Paraphrases accepted"),
                       ("irrelevant_acceptance_rate", "Irrelevant titles accepted")):
        fig, ax = plt.subplots(figsize=(9, 4.5))
        for offset, split in ((-.17, "historical"), (.17, "holdout")):
            ax.barh(positions + offset, [metrics[split][n][key] for n in names], height=.32, label=split)
        ax.set(yticks=positions, yticklabels=names, xlim=(0, 1), xlabel=label)
        ax.invert_yaxis()
        ax.legend()
        fig.tight_layout()
        fig.savefig(figures / f"{key}.png", dpi=140)
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for name in ("v2_0", "v2_1_minilm", selected):
        langs = metrics["holdout"][name]["by_language"]
        axes[0].plot(list(langs), [v["macro_f1"] for v in langs.values()], "o-", label=name)
    axes[0].set(ylabel="Holdout Macro F1", ylim=(0, 1))
    axes[0].legend()
    previous_benchmarks = [
        json.loads((OUT.parent / "phase2" / f"benchmark_{name}.json").read_text(encoding="utf8"))
        for name in ("v2_0", "e5", "minilm")
    ]
    peak = [profile["rss_bytes"]["peak"] / 2**20 for profile in previous_benchmarks]
    peak.append(profile["peak_working_set_bytes"] / 2**20)
    axes[1].bar(["V2.0", "E5", "MiniLM", "Student"], peak)
    axes[1].axhline(400, linestyle="--", color="black", label="Conservative target")
    axes[1].set(ylabel="Peak Windows working set, MiB")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(figures / "language_and_memory.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plots-only", action="store_true")
    args = parser.parse_args()
    if not args.plots_only:
        benchmark()
    plots()
