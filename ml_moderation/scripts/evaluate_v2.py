"""Evaluate the upload policy on authored examples and measure local CLI latency."""
import csv
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

import numpy as np

from ml_moderation.cli_demo_v2 import inspect
from ml_moderation.validator_v2 import ROOT

A = "ACCEPTED"
I = "IRRELEVANT_TITLE"
M = "MEANINGLESS_TITLE"
C = "INSUFFICIENT_CONTEXT"
P = "INAPPROPRIATE_CONTENT"
CASES = [
    ("DB101", "SQL", A), ("PROG101", "SQL", I),
    ("DB101", "Деректер қорын басқару", A), ("DB101", "Нормализация баз данных", A),
    ("DB101", "PostgreSQL Index Optimization", A), ("DB101", "SQL сұраныстар", A),
    ("DB101", "Constraints for parent-child table relationships", A),
    ("DB101", "Using Neural Networks for Database Query Optimization", A),
    ("DB101", "Neural Network Architecture", I), ("DB101", "Football Highlights", I),
    ("DB101", "Hello", I), ("DB101", "Привет", I), ("DB101", "Сәлем", I),
    ("DB101", "Lecture 5", C), ("DB101", "Дәріс 7", C), ("DB101", "Week 5", C),
    ("DB101", "asdfghjkl", M), ("DB101", "qwerty123", M), ("DB101", "аааааааааа", M),
    ("DB101", "pppAAASSSS", P),
    ("PROG101", "C++", A), ("PROG101", "OOP", A), ("PROG101", "Рекурсия", A),
    ("BIS101", "ERP", A), ("BIS101", "Бизнес үдерістері", A),
    ("BIS101", "How organizations coordinate decisions", A),
    ("BIS101", "SQL query execution plan", I),
]


def main():
    directory = ROOT / "reports/week13"
    rows = []
    for code, title, expected in CASES:
        results = inspect(title, "document_123.pdf", code)
        rows.append({**results, "expected": expected, "source": "author_generated_unreviewed"})
    with (directory / "demo_and_challenge.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    samples = [inspect("SQL Joins and Queries", "document_123.pdf", "DB101")["inference_ms"]
               for _ in range(200)]
    start = perf_counter()
    with ThreadPoolExecutor(max_workers=4) as executor:
        concurrent = list(executor.map(
            lambda _: inspect("SQL Joins and Queries", "document_123.pdf", "DB101")["decision"], range(200)
        ))
    total = perf_counter() - start
    summary = {
        "cases": len(rows), "correct": sum(row["decision"] == row["expected"] for row in rows),
        "first_cli_call_ms": rows[0]["inference_ms"],
        "warm_p50_ms": float(np.median(samples)), "warm_p95_ms": float(np.percentile(samples, 95)),
        "concurrent_requests_per_second": len(concurrent) / total,
        "concurrent_decisions": dict(Counter(concurrent)),
    }
    (directory / "local_evaluation.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
