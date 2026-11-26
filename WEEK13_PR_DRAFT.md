# Week 13: AI Material Validator V2 — Semantic Relevance and Lightweight Student Model

Suggested commit: `feat(ml): add multilingual course-aware material validation and shadow mode`

## Behavior

The upload route evaluates the title against the course retrieved from PostgreSQL before saving anything. Week 12 moderation runs first and continues to check both title and filename. The optional Week 13 pipeline adds title meaningfulness and course relevance. It preserves the existing public response contract. V2.2 shadow mode records a decision code, or an exception type on failure, and continues with the existing upload flow. It does not record title text, filename, identity, or scores.

Local examples use real trained artifacts. A database title is accepted for DB101 and rejected for PROG101. MiniLM recognizes an unfamiliar DB101 paraphrase that V2.0 rejects. V2.2 records an irrelevant result in shadow; the same local example returns 422 in enforcement mode.

## Evidence

| Model | Historical Macro F1 | Final holdout Macro F1 | Final paraphrases accepted | Final irrelevant acceptance |
|---|---:|---:|---:|---:|
| V2.0 | 0.363 | 0.609 | 0/60 | 2.1% |
| E5 INT8, full-context cosine | 0.584 | 0.552 | 14/60 | 29.7% |
| MiniLM INT8, full-context cosine | 0.622 | 0.616 | 17/60 | 20.3% |
| V2.2 distilled static LR, selected on dev | 0.518 | 0.544 | 10/60 | 15.6% |
| V2.2 static hybrid LR, experimental | 0.500 | 0.644 | 18/60 | 20.3% |

The initial synthetic F1 of 100% was measured on examples built around the terminology catalog. The historical benchmark and the final holdout each contain 300 pairs. The latter was frozen before model selection. Expected labels were authored for the project and still need human review. The blind review CLI hides reference labels and predictions during labeling, writing human answers to a separate CSV.

The V2.2 artifact is 370,815 bytes. On Windows, the local FastAPI process with Week 12 and V2.2 peaked at 153 MiB; warm p50/p95 were 1.79/2.30 ms. E5 and MiniLM peaked at 536.7 and 537.4 MiB respectively. These are process-level measurements outside HTTP and do not establish Linux or Render compatibility. The student uses the existing NumPy dependency. Large public ONNX files are excluded from Git and have reproducible downloads with checksums.

## Validation

All 129 backend tests passed after final cleanup, including the PostgreSQL side-effect checks and a shadow failure test that verifies title text stays out of logs. Ruff, the real-model demo, and the blind reviewer CLI smoke check also passed. The previous 54 frontend tests, 54 browser regressions and isolated V2.2 shadow run are documented in `WEEK13_ML_REPORT.md`. See `WEEK13_DEFENSE_RU.md` for the exact local demonstration commands.

## Settings and rollback

| Setting | Behavior |
|---|---|
| `MATERIAL_VALIDATOR_V2_ENABLED=false` or unset | Default. Keep Week 12 moderation only. |
| `MATERIAL_VALIDATOR_V2_ENABLED=true`, model `v2_0` | Lightweight V2.0 relevance when explicitly enabled. |
| `MATERIAL_VALIDATOR_V2_MODEL=minilm_preview` | Local MiniLM experiment; requires verified weights and ONNX dependencies. |
| `MATERIAL_VALIDATOR_V2_MODEL=v2_2`, `MATERIAL_VALIDATOR_V2_2_MODE=shadow` | Evaluate without blocking or changing the API response. |
| V2.2 `off` or `enforce` | Bypass new checks or apply confident decisions, respectively. Enforcement is intended for local testing. Uncertain semantic decisions pass. |

Use the global flag set to `false` for rollback. The experimental reporting and compact models stay available. Semantics should remain off on the current live service. Remaining limits include catalog breadth, overlap between courses, weaker Kazakh generalization, and high student abstention (57.6% of binary holdout cases). No production deployment or hosting changes are included in this PR.
