# Academic Filename Moderation Dataset (`ml_moderation/datasets/`)

## Tracked Curated Files

- `sources/ldnoobw_en.txt` and `sources/ldnoobw_ru.txt` — Downloaded from [LDNOOBW](https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words) (**CC-BY-4.0**).
- `sources/roose_ru_kk.json` — Downloaded from [roose/ru-kk-swear-words](https://github.com/roose/ru-kk-swear-words) (**MIT License**).
- `profanity_words.csv` — Filtered multilingual profanity vocabulary (`word,language,source,license`) across English, Russian, and Kazakh, excluding neutral/academic terms.
- `clean_filenames.csv` — Curated clean academic subjects and hard-negative vocabulary (`base_id,filename,language,category,source`) across English, Russian, Kazakh, and mixed languages.

## Reproducible Generated Splits (`generated/`, git-ignored)

Running `ml_moderation/scripts/generate_dataset.py` with `RANDOM_SEED = 42` deterministically creates:

- `train.csv` (~70%)
- `val.csv` (~15%)
- `test.csv` (~15%)
- `challenge_test.csv` (180 manually reviewed unseen examples, obfuscations, and hard negatives)
- `ambiguous_eval.csv` (10 borderline evaluation examples)
- `dataset_summary.json`

### CSV Schema

`sample_id,filename,language,label,category,source,base_id,augmentation_type`

- `label`: `0` = Allowed, `1` = Inappropriate.
- `category`: `clean_academic`, `hard_negative`, `explicit_profanity`, `obfuscated_profanity`.
- **Leakage prevention:** All `base_id` groups are split into `train`/`val`/`test` **before** generating any filename templates or obfuscation augmentations. Assertions verify zero overlap of `base_id` and exact `filename` across splits.
