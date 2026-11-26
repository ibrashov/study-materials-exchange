"""Train static MiniLM students and freeze selection before final evaluation."""
import hashlib
import json
from collections import Counter
from time import perf_counter

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression, Ridge

from ml_moderation.semantic_encoder import Encoder
from ml_moderation.scripts.fetch_phase2 import SOURCES, digest
from ml_moderation.scripts.semantic_phase2 import (
    DATA, LANGS, POSITIVE, REPORT, assess, lexical, policy, rows_for, select_threshold, train_rows, write_csv,
)
from ml_moderation.static_student import CODES, WIDTH, bag, embed, interactions, unit
from ml_moderation.validator_v2 import ROOT, models, normalize, score

OUTPUT = REPORT.parent / "phase3"
FINAL_HASH = "7922a02dc0bc7c5b551ffaeFdf9f36081c00320f2f57c36845ac5c75c17bf050".lower()


def authored(split):
    raw = (DATA / f"phase3_{split}.txt").read_bytes().replace(b"\r\n", b"\n")
    if split == "holdout" and hashlib.sha256(raw).hexdigest() != FINAL_HASH:
        raise ValueError("Phase 3 holdout does not match the frozen checksum")
    rows = []
    for line_num, line in enumerate(raw.decode("utf8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        origin, category, rationale, *titles = line.split("|")
        for lang, title in zip(LANGS, titles, strict=True):
            for course in CODES:
                paired = category in POSITIVE and course != origin
                rows.append(dict(course=course, title=title, language=lang,
                                 category="hard_negative" if paired else category,
                                 label="ambiguous" if category == "ambiguous" else int(category in POSITIVE and not paired),
                                 base_id=f"{split}-{line_num}", source="assistant_authored_unreviewed",
                                 rationale=f"{rationale}; intended course {origin}"))
    return rows


def sparse_bags(texts):
    indices, values, ends = [], [], [0]
    for text in texts:
        counts = bag(text)
        indices.extend(counts)
        values.extend(counts.values())
        ends.append(len(indices))
    return csr_matrix((np.array(values, dtype=np.float32), indices, ends), shape=(len(texts), WIDTH))


def teacher_for(name):
    path = DATA / f"generated/phase2/{name}"
    if (digest(path / "model.onnx"), digest(path / "tokenizer.json")) != SOURCES[name][-2:]:
        raise ValueError("Teacher weights do not match Phase 2")
    return Encoder(name, path)


def teacher_vectors(teacher, titles):
    return np.concatenate([teacher.embed(titles[i:i + 16], query=True)
                           for i in range(0, len(titles), 16)])


def fit_student(teacher, training):
    titles = list(dict.fromkeys(row["title"] for row in training))
    teacher_matrix = teacher_vectors(teacher, titles)
    projection = PCA(n_components=64, random_state=13).fit(teacher_matrix)
    target = projection.transform(teacher_matrix)
    ridge = Ridge(alpha=.3, fit_intercept=False, solver="lsqr", tol=1e-4).fit(sparse_bags(titles), target)
    dense = ridge.coef_.T.astype(np.float32)
    scales = np.maximum(np.abs(dense).max(axis=0) / 127, 1e-10)
    quantized = np.rint(dense / scales).clip(-127, 127).astype(np.int8)
    contexts = unit(projection.transform(np.concatenate([teacher.course(c) for c in CODES])))
    contexts = contexts.reshape(len(CODES), -1, 64).astype(np.float32)
    originals = dict(zip(titles, teacher_matrix, strict=True))
    return quantized, scales, contexts, originals


def features(rows, lookup, contexts):
    return np.array([interactions(lookup[row["title"]], contexts, row["course"]) for row in rows])


def fit_lr(values, y, teacher_scores=None):
    model = LogisticRegression(random_state=13, class_weight="balanced", max_iter=1000)
    if teacher_scores is None:
        return model.fit(values, y)
    # A quarter of each example's loss uses a soft target. The teacher cosine
    # is converted to a train-only percentile, not treated as probability.
    quantiles = np.quantile(teacher_scores, [.1, .9])
    soft = np.clip((teacher_scores - quantiles[0]) / max(np.diff(quantiles)[0], 1e-5), 0, 1)
    return model.fit(np.concatenate([values, values, values]),
                     np.r_[y, np.ones(len(y)), np.zeros(len(y))],
                     sample_weight=np.r_[np.full(len(y), .75), .25 * soft, .25 * (1 - soft)])


def tuning(rows, values):
    upper, lower, _ = select_threshold(rows, values)
    best = None
    for candidate in np.unique(np.r_[lower, upper, np.quantile(values[values < upper], [.25, .5, .75])
                                    if np.any(values < upper) else lower]):
        result = assess(rows, policy(values, upper, candidate))
        cost = result["relevant_explicit_rejection_rate"] + .30 * result["binary_clarification"]
        if best is None or cost < best[0]:
            best = cost, float(candidate)
    return float(upper), best[1]


def additional_metrics(rows, values):
    result = assess(rows, values)
    valid = np.array([row["label"] != "ambiguous" for row in rows])
    decided = valid & (values != -1)
    labels = np.array([row["label"] if ok else -1 for row, ok in zip(rows, valid)])
    result["binary_decided_fraction"] = float(decided.sum() / valid.sum())
    result["selective_accuracy"] = float(np.mean(values[decided] == labels[decided])) if decided.any() else None
    return result


def main():
    started = perf_counter()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    training, development = train_rows() + authored("training"), rows_for("dev")
    historical = rows_for("challenge")
    sets = [training, development, historical]
    used = [{normalize(r["title"]) for r in rows} for rows in sets]
    if any(used[a] & used[b] for a, b in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("Cross-split title leakage")
    write_csv(OUTPUT / "additional_training.csv", authored("training"))
    teacher = teacher_for("minilm")
    quantized, scales, contexts, originals = fit_student(teacher, training)
    student = quantized.astype(np.float32) * scales
    teacher_contexts = np.stack([teacher.course(c) for c in CODES])
    labels = np.array([r["label"] for r in training])

    def vectors(rows, encoder, original=None):
        titles = list(dict.fromkeys(row["title"] for row in rows))
        lookup = original or dict(zip(titles, teacher_vectors(encoder, titles), strict=True))
        return features(rows, lookup, np.stack([encoder.course(c) for c in CODES]))

    def static(rows):
        lookup = {r["title"]: embed(r["title"], student) for r in rows}
        return features(rows, lookup, contexts)

    train_static, dev_static = map(static, (training, development))
    teach_train = features(training, originals, teacher_contexts)
    teach_dev = vectors(development, teacher)
    dev_lexical = lexical(development)
    train_lexical = lexical(training)
    hybrid_train = np.column_stack((train_static, train_lexical))
    lr = fit_lr(train_static, labels)
    hybrid = fit_lr(hybrid_train, labels)
    soft = fit_lr(hybrid_train, labels, teach_train[:, 0])
    teacher_combo = fit_lr(teach_train[:, :3], labels)
    teacher_relative = fit_lr(teach_train, labels)
    teacher_hybrid = fit_lr(np.column_stack((teach_train, train_lexical)), labels)

    def methods(sta, tea, lex):
        hybrid_features = np.column_stack((sta, lex))
        return {
            "student_cosine": sta[:, 0], "student_lr": lr.decision_function(sta),
            "student_hybrid": hybrid.decision_function(hybrid_features),
            "student_soft": soft.decision_function(hybrid_features),
            "minilm_full": tea[:, 0], "minilm_max_topic": tea[:, 1], "minilm_top3": tea[:, 2],
            "minilm_combined": teacher_combo.decision_function(tea[:, :3]),
            "minilm_relative": teacher_relative.decision_function(tea),
            "minilm_hybrid": teacher_hybrid.decision_function(np.column_stack((tea, lex))),
        }

    dev_scores = methods(dev_static, teach_dev, dev_lexical)
    thresholds = {name: tuning(development, values) for name, values in dev_scores.items()}
    dev_metrics = {name: additional_metrics(development, policy(values, *thresholds[name]))
                   for name, values in dev_scores.items()}
    # Selection excludes both benchmark datasets. Trade off quality against irrelevant acceptance.
    selected = max((name for name in dev_scores if name.startswith("student_")),
                   key=lambda n: dev_metrics[n]["macro_f1"] - .25 * dev_metrics[n]["irrelevant_acceptance_rate"])
    selected_models = {
        "student_cosine": (np.r_[1., np.zeros(11)], 0.),
        "student_lr": (np.r_[lr.coef_[0], np.zeros(7)], float(lr.intercept_[0])),
        "student_hybrid": (hybrid.coef_[0], float(hybrid.intercept_[0])),
        "student_soft": (soft.coef_[0], float(soft.intercept_[0])),
    }
    for name, (coef, bias) in selected_models.items():
        path = ROOT / "models/title_validator_v2_2.npz" if name == selected else OUTPUT / f"{name}.npz"
        np.savez_compressed(path, quantized=quantized, scale=scales, contexts=contexts,
                            coef=coef, bias=bias, upper=thresholds[name][0], lower=thresholds[name][1])
    artifact = ROOT / "models/title_validator_v2_2.npz"
    freeze = dict(selection=selected, thresholds=thresholds, artifact_sha256=digest(artifact),
                  holdout_sha256=FINAL_HASH, shape=list(quantized.shape), seed=13,
                  teacher_sha256=SOURCES["minilm"][-2], development=dev_metrics)
    (OUTPUT / "frozen_configuration.json").write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf8")
    final = authored("holdout")
    if {normalize(r["title"]) for r in final} & set.union(*used):
        raise ValueError("Final title leakage")
    write_csv(OUTPUT / "final_holdout.csv", final)
    write_csv(OUTPUT / "human_label_review.csv", [
        {**row, "reviewed_label": "", "reviewer": "", "review_notes": ""} for row in final
    ])
    previous = json.loads((REPORT / "independent_metrics.json").read_text(encoding="utf8"))
    e5 = teacher_for("e5")
    e5_curve = previous["threshold_curves"]["e5_course_cosine"]
    e5_cut = max(e5_curve, key=lambda r: r["macro_f1"])["threshold"]
    e5_dev = vectors(development, e5)[:, 0]
    e5_below = [v for v, row in zip(e5_dev, development) if isinstance(row["label"], int)
                and row["label"] == 0 and v < e5_cut]
    e5_low = float(np.quantile(e5_below, .9)) if e5_below else e5_cut
    old_policy = json.loads((REPORT / "preview_policy.json").read_text(encoding="utf8"))
    baseline = models()["relevance"]
    output = {**freeze, "train_count": len(training), "dev_count": len(development),
              "holdout_count": len(final), "model_bytes": artifact.stat().st_size}
    for split, rows in (("historical", historical), ("holdout", final)):
        lex = lexical(rows)
        tea = vectors(rows, teacher)
        scores = methods(static(rows), tea, lex)
        decisions = {n: policy(values, *thresholds[n]) for n, values in scores.items()}
        base = np.array([score(x, baseline) for x in lex])
        decisions["v2_0"] = policy(base, float(baseline[2]), float(baseline[2]) - .10)
        decisions["v2_1_minilm"] = policy(tea[:, 0], old_policy["accept"], old_policy["clarify"])
        decisions["v2_1_e5"] = policy(vectors(rows, e5)[:, 0], e5_cut, e5_low)
        output[split] = {name: additional_metrics(rows, pred) for name, pred in decisions.items()}
        write_csv(OUTPUT / f"{split}_predictions.csv", [
            {**row, **{n: int(values[i]) for n, values in decisions.items()}} for i, row in enumerate(rows)
        ])
        if split == "historical":
            errors = []
            for index, row in enumerate(rows):
                decision = int(decisions["v2_1_minilm"][index])
                expected = -1 if row["label"] == "ambiguous" else row["label"]
                if expected == decision:
                    continue
                category = row["category"]
                suspects = {
                    "ambiguous": "generic or overlapping; threshold/context ambiguity",
                    "misleading": "keyword dominates semantic intent",
                    "hard_negative": "possible syllabus overlap; check paired label",
                    "paraphrase": "course representation or sentence embedding mismatch",
                    "relevant": "topic coverage or cutoff",
                }
                errors.append({**row, "decision": decision, "cosine": float(tea[index, 0]),
                               "relative_margin": float(tea[index, 3]),
                               "hypothesis": suspects.get(category, "off-topic similarity or calibration"),
                               "human_review_priority": "high" if category in {"ambiguous", "hard_negative"} else "normal"})
            write_csv(OUTPUT / "minilm_historical_errors.csv", errors)
            output["historical_error_categories"] = dict(Counter(row["category"] for row in errors))
    output["elapsed_seconds"] = perf_counter() - started
    (OUTPUT / "metrics.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf8")
    print(selected, {name: round(output["holdout"][name]["macro_f1"], 3) for name in output["holdout"]})


if __name__ == "__main__":
    main()
