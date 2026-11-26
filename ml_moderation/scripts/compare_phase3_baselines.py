"""Replay all frozen Phase 2 policies on the new holdout without retraining."""
import json

import numpy as np

from ml_moderation.scripts.distill_phase3 import OUTPUT, additional_metrics, authored, teacher_for
from ml_moderation.scripts.semantic_phase2 import (
    REPORT, lexical, policy, representations, rows_for, select_threshold,
)
from ml_moderation.validator_v2 import models, score


def main():
    rows, dev = authored("holdout"), rows_for("dev")
    lex = lexical(rows)
    base = models()["relevance"]
    legacy = policy(np.array([score(row, base) for row in lex]), float(base[2]), float(base[2]) - .1)
    results = {"keyword": additional_metrics(rows, lex[:, 0].astype(int)),
               "v2_0": additional_metrics(rows, legacy)}
    for name in ("e5", "minilm"):
        encoder = teacher_for(name)
        encoded = representations(rows, encoder)
        dev_encoded = representations(dev, encoder)
        for method, column in (("course_cosine", 0), ("topic_cosine", 1)):
            cutoff, lower, _ = select_threshold(dev, dev_encoded[:, column])
            results[f"{name}_{method}"] = additional_metrics(rows, policy(encoded[:, column], cutoff, lower))
        for kind, values in (("semantic_lr", encoded), ("hybrid_lr", np.column_stack((encoded, lex)))):
            with np.load(REPORT / f"{name}_{kind}.npz", allow_pickle=False) as weights:
                coef, bias = weights["coef"], weights["bias"]
                probabilities = 1.0 / (1.0 + np.exp(-(values @ coef + bias)))
                decisions = policy(probabilities, float(weights["threshold"]), float(weights["lower"]))
            results[f"{name}_{kind}"] = additional_metrics(rows, decisions)
            if kind == "semantic_lr":
                results[f"{name}_cascade"] = additional_metrics(rows, np.where(lex[:, 3] > 0, legacy, decisions))
        encoder.course.cache_clear()
        del encoder
    historical = json.loads((REPORT / "independent_metrics.json").read_text(encoding="utf8"))["models"]
    (OUTPUT / "phase2_baseline_replay.json").write_text(
        json.dumps({"historical": historical, "holdout": results}, indent=2) + "\n", encoding="utf8"
    )


if __name__ == "__main__":
    main()
