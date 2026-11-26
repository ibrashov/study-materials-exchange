"""Offline comparison of frozen ONNX encoders on the Phase 2 challenge."""
import argparse
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter, process_time

import numpy as np

from ml_moderation.cli_demo_v2 import COURSES
from ml_moderation.semantic_encoder import Encoder, interaction
from ml_moderation.scripts.fetch_phase2 import SOURCES, digest
from ml_moderation.validator_v2 import GENERIC, ROOT, models, normalize, relevance_features, score

REPORT = ROOT / "reports/week13/phase2"
DATA = ROOT / "datasets"
CHALLENGE_SHA = "03974205471e2c169f52d3840056cbeb1a0256c1558de698bf924e74bb31454e"
LANGS = ("en", "ru", "kk", "mixed")
POSITIVE = {"relevant", "paraphrase"}


def rows_for(split):
    path = DATA / f"phase2_{split}.txt"
    content = path.read_bytes().replace(b"\r\n", b"\n")
    if split == "challenge" and hashlib.sha256(content).hexdigest() != CHALLENGE_SHA:
        raise ValueError("Frozen challenge checksum differs")
    rows = []
    for number, line in enumerate(content.decode("utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        code, group, rationale, *titles = line.split("|")
        for lang, title in zip(LANGS, titles, strict=True):
            rows.append(dict(course=code, title=title, language=lang, category=group,
                             label="ambiguous" if group == "ambiguous" else int(group in POSITIVE),
                             base_id=f"{split}-{number}", rationale=rationale,
                             source="assistant_authored_no_human_review"))
            if group in POSITIVE:
                # One paired negative from a different syllabus. Topic groups stay together.
                others = [candidate for candidate in COURSES if candidate != code]
                wrong = others[(number + LANGS.index(lang)) % len(others)]
                rows.append({**rows[-1], "course": wrong, "category": "hard_negative", "label": 0,
                             "rationale": f"{rationale} is assigned to {code}, not {wrong}"})
    return rows


def train_rows():
    from ml_moderation.scripts.train_v2 import generate

    _, generated = generate()
    # Exclude template-heavy examples without losing the three class domains.
    grouped = defaultdict(list)
    for row in generated:
        if row["split"] == "train":
            grouped[row["base_id"]].append(row)
    rng = np.random.default_rng(13)
    rows = []
    for group in grouped.values():
        for index in rng.choice(len(group), min(27, len(group)), replace=False):
            row = group[index]
            rows.append(dict(course=row["course_code"], title=row["title"], label=row["label"]))
    return rows


def representations(rows, encoder):
    unique = list(dict.fromkeys(row["title"] for row in rows))
    embeddings = {}
    for start in range(0, len(unique), 16):
        batch = unique[start:start + 16]
        embeddings.update(zip(batch, encoder.embed(batch, query=True), strict=True))
    return np.array([interaction(embeddings[row["title"]], encoder.course(row["course"]))
                     for row in rows])


def lexical(rows):
    return np.stack([relevance_features(row["title"], row["course"], COURSES[row["course"]])
                     for row in rows])


def assess(rows, predictions):
    from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support

    mask = np.array([isinstance(row["label"], int) for row in rows])
    actual = np.array([row["label"] if isinstance(row["label"], int) else -1 for row in rows])
    predicted = np.asarray(predictions)
    binary = (predicted == 1).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        actual[mask], binary[mask], labels=[0, 1], zero_division=0
    )
    def rate(selection, value):
        return float(np.mean(predicted[selection] == value)) if np.any(selection) else None
    return {
        "n_binary": int(mask.sum()), "accuracy_accept_vs_other": float(np.mean(binary[mask] == actual[mask])),
        "macro_f1": float(f1.mean()), "positive_f1": float(f1[1]),
        "precision": precision.tolist(), "recall": recall.tolist(),
        "confusion_matrix": confusion_matrix(actual[mask], binary[mask], labels=[0, 1]).tolist(),
        "relevant_nonacceptance_rate": float(1 - rate(actual == 1, 1)),
        "relevant_explicit_rejection_rate": rate(actual == 1, 0),
        "irrelevant_acceptance_rate": rate(actual == 0, 1),
        "paraphrase_acceptance": rate(np.array([r["category"] == "paraphrase" for r in rows]), 1),
        "hard_negative_detection": rate(np.array([r["category"] == "hard_negative" for r in rows]), 0),
        "ambiguous_clarification": rate(~mask, -1),
        "binary_clarification": rate(mask, -1),
        "by_language": {
            lang: {"n": int(selection.sum()), "macro_f1": float(f1_score(
                actual[selection], binary[selection], average="macro", labels=[0, 1], zero_division=0))}
            for lang in LANGS
            if np.any(selection := mask & np.array([r["language"] == lang for r in rows]))
        },
    }


def select_threshold(rows, values):
    from sklearn.metrics import f1_score

    labels = np.array([row["label"] if isinstance(row["label"], int) else -1 for row in rows])
    mask = labels >= 0
    candidates = np.unique(np.r_[np.quantile(values[mask], np.linspace(0, 1, 61)),
                                 np.nextafter(values.max(), np.inf)])
    curve = [{"threshold": float(t), "macro_f1": float(
        f1_score(labels[mask], values[mask] >= t, average="macro", zero_division=0))}
             for t in candidates]
    threshold = max(curve, key=lambda item: item["macro_f1"])["threshold"]
    below = values[(labels == 0) & (values < threshold)]
    # Reserve a narrow range under the cut based on validation negatives alone.
    lower = float(np.quantile(below, .90)) if len(below) else threshold
    return threshold, lower, curve


def policy(values, threshold, lower):
    return np.where(values >= threshold, 1, np.where(values >= lower, -1, 0))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def pipeline_rows(rows, decisions):
    from ml_moderation.cli_demo_v2 import inspect

    baseline, preview = [], []
    decision_codes = {"ACCEPTED": 1, "INSUFFICIENT_CONTEXT": -1}
    for index, row in enumerate(rows):
        title = row["title"]
        result = inspect(title, "document_123.pdf", row["course"])
        reason = result["decision"]
        decision = decision_codes.get(reason, 0)
        baseline.append(decision)
        if reason in {"INAPPROPRIATE_CONTENT", "MEANINGLESS_TITLE"} or GENERIC.fullmatch(normalize(title)):
            preview.append(decision)
        else:
            preview.append(int(decisions[index]))
    return baseline, preview


def evaluate(names):
    from sklearn.linear_model import LogisticRegression

    training, dev, test = train_rows(), rows_for("dev"), rows_for("challenge")
    sets = [training, dev, test]
    seen = [{normalize(row["title"]) for row in rows} for rows in sets]
    if any(seen[a] & seen[b] for a, b in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("Exact title leakage across splits")
    REPORT.mkdir(parents=True, exist_ok=True)
    write_csv(REPORT / "challenge.csv", test)
    write_csv(REPORT / "development.csv", dev)
    vectors = [lexical(rows) for rows in sets]
    base = models()["relevance"]
    baseline_scores = np.array([score(row, base) for row in vectors[2]])
    decisions = {"keyword": vectors[2][:, 0].astype(int),
                 "v2_0": policy(baseline_scores, float(base[2]), float(base[2]) - .10)}
    result = {"challenge_sha256": CHALLENGE_SHA, "sizes": [len(rows) for rows in sets],
              "categories": dict(Counter(row["category"] for row in test)), "models": {},
              "threshold_curves": {}, "artifacts": {}, "course_holdout": {}}
    for name in names:
        folder = DATA / "generated/phase2" / name
        if (digest(folder / "model.onnx"), digest(folder / "tokenizer.json")) != SOURCES[name][-2:]:
            raise ValueError(f"Invalid {name} artifact checksum")
        encoder = Encoder(name, folder)
        encoded = [representations(rows, encoder) for rows in sets]
        result["course_holdout"][name] = {}
        for course in COURSES:
            # Remove every paired sibling of that course's positive topics from development.
            dev_group_ids = {row["base_id"] for row in dev if row["course"] == course and row["label"] == 1}
            dev_mask = np.array([r["course"] != course and r["base_id"] not in dev_group_ids for r in dev])
            train_mask = np.array([r["course"] != course for r in training])
            test_mask = np.array([r["course"] == course for r in test])
            held = LogisticRegression(random_state=13, class_weight="balanced", max_iter=1000)
            # Same titles paired to remaining courses can still appear as negatives in synthetic training.
            held.fit(encoded[0][train_mask], [r["label"] for r, keep in zip(training, train_mask) if keep])
            dev_cut, dev_low, _ = select_threshold(
                [r for r, keep in zip(dev, dev_mask) if keep], held.predict_proba(encoded[1][dev_mask])[:, 1]
            )
            result["course_holdout"][name][course] = assess(
                [r for r, keep in zip(test, test_mask) if keep],
                policy(held.predict_proba(encoded[2][test_mask])[:, 1], dev_cut, dev_low),
            )
        combinations = {
            "course_cosine": [x[:, 0] for x in encoded],
            "topic_cosine": [x[:, 1] for x in encoded],
        }
        for kind, features in (
            ("semantic_lr", encoded),
            ("hybrid_lr", [np.column_stack((a, b)) for a, b in zip(encoded, vectors)]),
        ):
            classifier = LogisticRegression(random_state=13, class_weight="balanced", max_iter=1000)
            classifier.fit(features[0], [row["label"] for row in training])
            combinations[kind] = [classifier.predict_proba(x)[:, 1] for x in features]
            folder_out = REPORT / f"{name}_{kind}.npz"
            threshold, lower, _ = select_threshold(dev, combinations[kind][1])
            np.savez_compressed(folder_out, coef=classifier.coef_[0], bias=classifier.intercept_[0],
                                threshold=threshold, lower=lower)
        for kind, values in combinations.items():
            key = f"{name}_{kind}"
            threshold, lower, curve = select_threshold(dev, values[1])
            result["threshold_curves"][key] = curve
            decisions[key] = policy(values[2], threshold, lower)
            if key == "minilm_course_cosine":
                (REPORT / "preview_policy.json").write_text(
                    json.dumps({"accept": threshold, "clarify": lower}, indent=2) + "\n", encoding="utf8"
                )
            if kind == "semantic_lr":
                # Low catalogue coverage routes to semantics, including strong catalogue misses.
                decisions[f"{name}_cascade"] = np.where(
                    vectors[2][:, 3] > 0, decisions["v2_0"], decisions[key]
                )
        weight = folder / "model.onnx"
        result["artifacts"][name] = {"weights_bytes": weight.stat().st_size, "weights_sha256": digest(weight),
                                      "tokenizer_bytes": (folder / "tokenizer.json").stat().st_size,
                                      "tokenizer_sha256": digest(folder / "tokenizer.json")}
        encoder.course.cache_clear()
    for key, predictions in decisions.items():
        result["models"][key] = assess(test, predictions)
    if "minilm_course_cosine" in decisions:
        baseline, preview = pipeline_rows(test, decisions["minilm_course_cosine"])
        result["full_pipeline"] = {"v2_0": assess(test, baseline), "minilm_preview": assess(test, preview)}
    write_csv(REPORT / "challenge_predictions.csv", [
        {**row, **{key: int(preds[i]) for key, preds in decisions.items()}} for i, row in enumerate(test)
    ])
    (REPORT / "independent_metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def benchmark(name):
    from importlib.metadata import distribution

    import psutil
    from backend.app.main import app
    from ml_moderation.cli_demo_v2 import inspect

    process = psutil.Process()
    memory = {"app_imported": process.memory_info().rss}
    start = perf_counter()
    inspect("SQL joins", "document_123.pdf", "DB101")
    legacy = perf_counter() - start
    memory["v2_0_loaded"] = process.memory_info().rss
    encoder = None
    if name != "v2_0":
        encoder = Encoder(name, DATA / "generated/phase2" / name)
        encoder.course("DB101")
    def call():
        start = perf_counter()
        title = "Keeping two clerks from overwriting each other's edits"
        inspect(title, "document_123.pdf", "DB101")
        if encoder is not None:
            interaction(encoder.embed([title], query=True)[0], encoder.course("DB101"))
        return (perf_counter() - start) * 1000
    first = call()
    cold = (perf_counter() - start) * 1000
    memory["loaded"] = process.memory_info().rss
    cpu_start, start = process_time(), perf_counter()
    warm = [call() for _ in range(40)]
    cpu = (process_time() - cpu_start) / (perf_counter() - start)
    start = perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        concurrent = list(pool.map(lambda _: call(), range(40)))
    throughput = len(concurrent) / (perf_counter() - start)
    info = process.memory_info()
    memory["after_requests"] = info.rss
    memory["peak"] = getattr(info, "peak_wset", None)
    data = dict(model=name, pid=os.getpid(), routes=len(app.routes), rss_bytes=memory, first_inference_ms=first,
                cold_from_before_model_load_ms=cold, v2_0_initialization_ms=legacy * 1000,
                p50_ms=float(np.median(warm)), p95_ms=float(np.percentile(warm, 95)),
                concurrent_p95_ms=float(np.percentile(concurrent, 95)), concurrent_per_second=throughput,
                mean_cpu_core_equivalents=cpu)
    if encoder is not None:
        for package in ("onnxruntime", "tokenizers"):
            installed = distribution(package)
            data.setdefault("direct_dependencies", {})[package] = {
                "version": installed.version,
                "installed_bytes": sum(file.size or 0 for file in installed.files or ()),
            }
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / f"benchmark_{name}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encoders", choices=("e5", "minilm"), nargs="*", default=["e5", "minilm"])
    parser.add_argument("--benchmark", choices=("v2_0", "e5", "minilm"))
    args = parser.parse_args()
    if args.benchmark:
        benchmark(args.benchmark)
    else:
        evaluate(args.encoders)


if __name__ == "__main__":
    main()
