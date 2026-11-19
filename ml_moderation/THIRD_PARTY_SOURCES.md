# Third-Party Open-Source Research & Licensing Audit (Phase 2)

Every external repository and dataset below was verified directly via GitHub API / Hugging Face on **2026-11-19**. No third-party profanity filter library is installed as a drop-in production dependency; instead, we train our own reproducible multilingual character-level ML model on a curated academic filename dataset.

| Source | URL | Verified License | Status & Usage Decision |
| --- | --- | --- | --- |
| **LDNOOBW** (`List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words`) | https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words | **CC-BY-4.0** (verified via `LICENSE` and GitHub API) | **Used (filtered).** Downloaded `en` and `ru` lists into `ml_moderation/datasets/sources/`. Filtered out neutral/academic terms (e.g., medical, geographic, general nouns) before assembling `profanity_words.csv`. Attribution preserved. |
| **roose/ru-kk-swear-words** | https://github.com/roose/ru-kk-swear-words | **MIT License** (verified via GitHub API) | **Used.** Downloaded `words.json` (41 Russian-Kazakh swear word pairs) into `ml_moderation/datasets/sources/` to provide verified Kazakh (`kk`) and Russian (`ru`) seed vocabulary. |
| **alt-profanity-check** | https://github.com/dimitrismistriotis/alt-profanity-check | **MIT License** (verified via GitHub API) | **Researched only (not installed).** Uses `scikit-learn` Linear SVM + bag-of-words on English text. Not suitable as a drop-in because it targets English sentences rather than short multilingual obfuscated filenames, and the Week 12 requirement is a locally trained reproducible ML pipeline. |
| **glin-profanity** | https://github.com/glincker/glin-profanity | **MIT License** (verified via GitHub API) | **Researched only (not installed).** Inspired normalization ideas for Unicode confusables and leetspeak handling; we implemented our own shared academic-safe `ml_moderation/normalization.py`. |
| **profanity-filter2** | https://github.com/GooRoo/profanity-filter2 | **GPL-3.0** (verified via GitHub API, 0 stars, last pushed 2021-10-01) | **Rejected.** Copyleft GPL-3.0 license incompatibility, unmaintained since 2021, relies on heavy spaCy pipelines unsuitable for Render Free 512 MB RAM, and weak against arbitrary character-level obfuscation. |
| **farabi-lab/Content-Moderation-and-Safety** | https://huggingface.co/datasets/farabi-lab/Content-Moderation-and-Safety | **Gated / Institutional Research Terms** (Al-Farabi Kazakh National University) | **Researched only (not downloaded).** Repository is gated on Hugging Face (requires account authentication and terms acceptance) and contains long LLM safety dialogues rather than short academic filenames. |

## Attribution Notice

- **LDNOOBW** word lists (`en`, `ru`) are licensed under **Creative Commons Attribution 4.0 International (CC-BY-4.0)** by Shutterstock / LDNOOBW contributors. Filtered subsets are used strictly to generate training data for academic filename content moderation.
- **roose/ru-kk-swear-words** (`words.json`) is licensed under the **MIT License**.
