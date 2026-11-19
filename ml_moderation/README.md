# ML Filename Moderation (`ml_moderation/`)

Lightweight, locally trained, CPU-only machine learning module for moderating student-submitted filenames and study material titles in **Study Materials Exchange** (Week 12 — Ibrashov Anuar).

## Key Properties

- **Languages:** English, Russian, Kazakh, and mixed-language filenames/titles.
- **No external AI APIs:** 100% local CPU inference from `ml_moderation/models/filename_moderator.joblib`.
- **Render Free-tier compatible:** Production runtime requires only `joblib` and `numpy` (no PyTorch, no GPU, no separate ML server, no DB migrations).
- **Shared preprocessing:** `normalization.py` is shared verbatim between dataset generation, training, evaluation, CLI demo, and FastAPI runtime.
- **Fail-closed safety:** If the model artifact cannot load, uploads fail explicitly with HTTP `503` instead of silently disabling moderation.

## Reproducible Commands

Run from repository root (`C:\Users\Ануар\Desktop\Папки\Anuar\BIS`):

```powershell
# 1. Generate leak-free dataset (seed=42, 70/15/15 group split by base_id + challenge set)
.\.venv\Scripts\python.exe ml_moderation/scripts/generate_dataset.py

# 2. Train Baselines A/B, Feature Ablation, Model A (LogReg), Model B (Linear SVM), Model D (Hybrid)
#    and export the selected production artifact to ml_moderation/models/filename_moderator.joblib
.\.venv\Scripts\python.exe ml_moderation/scripts/train_models.py

# 3. Train Model C (PyTorch Char-CNN) using training-only environment (requires torch)
python ml_moderation/scripts/train_char_cnn.py

# 4. Aggregate metrics, CSV comparison, error analysis, and matplotlib plots
python ml_moderation/scripts/evaluate_models.py

# 5. Measure Render memory/latency compatibility
.\.venv\Scripts\python.exe ml_moderation/scripts/measure_render_compat.py

# 6. Run interactive local CLI demo
.\.venv\Scripts\python.exe ml_moderation/cli_demo.py
# Or non-interactive batch check:
.\.venv\Scripts\python.exe ml_moderation/cli_demo.py Class_Notes.pdf pppAAASSSS.pdf Қазақстан_тарихы.pdf
```

## Directory Structure

- `config.py` — Paths, version, length limit, and user-facing messages.
- `normalization.py` — Shared Unicode NFKC, invisible-char removal, controlled separator joining, mixed-script confusable handling, academic-safe leetspeak, and repetition capping.
- `features.py` — Multi-view character n-gram TF-IDF (2–5) + scaled obfuscation signals + portable linear scorer.
- `baseline.py` — Phase 5 baselines (Blacklist substring/exact + Fuzzy matching).
- `predictor.py` — Thread-safe production loader and threshold/uncertain-zone policy engine.
- `cli_demo.py` — Interactive CLI demonstration script.
- `models/filename_moderator.joblib` — Portable production model artifact (`protocol=4`).
- `datasets/` — Curated open-source seeds, `profanity_words.csv`, `clean_filenames.csv`.
- `reports/` — `metrics.json`, `model_comparison.csv`, `error_analysis.md`, `render_compatibility.json`, and `figures/`.
- `THIRD_PARTY_SOURCES.md` — Verified open-source repositories, licenses, and attribution.
