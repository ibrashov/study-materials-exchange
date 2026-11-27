"""Local CPU inference for material title validation."""
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path
from zlib import crc32

import numpy as np

ROOT = Path(__file__).parent
WIDTH = 4096
SHORT_TERMS = frozenset({
    "sql", "c++", "c#", "oop", "tcp/ip", "xor", "relu", "pytorch", "db101", "3nf",
    "acid", "b-tree", "x2 + y2", "қмж", "бқ", "hello", "привет", "сәлем",
})
GENERIC = re.compile(
    r"(?:(?:lecture|week|assignment|notes|presentation|lab|homework|slides|seminar|practice|material|"
    r"лекция|неделя|задание|конспект|презентация|лабораторная|практика|материал|"
    r"дәріс|апта|тапсырма|қмж|слайд|зертханалық)\s*(?:#|№)?\s*\d*|"
    r"(?:intro|introduction|overview|summary|введение|обзор|кіріспе|шолу))",
    re.I,
)


def normalize(title):
    return unicodedata.normalize("NFKC", title).casefold().strip()


@lru_cache(maxsize=1)
def catalog():
    import json
    return json.loads((ROOT / "course_contexts_v2.json").read_text(encoding="utf-8"))


def meaningful_features(title):
    value = normalize(title)
    length = max(len(value), 1)
    counts = Counter(value)
    features = np.zeros(WIDTH + 8, dtype=np.float32)
    padded = " " + value + " "
    for n in (2, 3, 4):
        for i in range(len(padded) - n + 1):
            features[crc32(padded[i:i+n].encode()) % WIDTH] += 1
    features[:WIDTH] /= max(float(np.linalg.norm(features[:WIDTH])), 1)
    features[WIDTH:] = (
        np.log1p(len(value)), len(counts) / length,
        max(counts.values(), default=0) / length,
        sum(c.isdigit() for c in value) / length,
        sum(c.isalpha() for c in value) / length,
        sum(c.isspace() for c in value) / length,
        sum("а" <= c <= "я" for c in value) / length,
        len(re.findall(r"(.)\1{2,}", value)) / length,
    )
    return features


def words(value):
    return set(re.findall(r"\w+|c\+\+|c#", normalize(value)))


@lru_cache(maxsize=4096)
def concepts(value):
    result = set()
    for code, groups in catalog().items():
        for index, aliases in enumerate(groups):
            for alias in aliases:
                # Allow inflectional suffixes on longer stems (RU/KK/EN), exact boundaries on short acronyms
                pattern = (
                    r"(?<!\w)" + re.escape(alias)
                    if len(alias) >= 5 and alias[-1].isalpha()
                    else r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
                )
                if re.search(pattern, value):
                    result.add((code, index))
                    break
    return frozenset(result)


def relevance_features(title, code, context):
    tokens, course_tokens = words(title), words(context)
    found = concepts(normalize(title))
    target = concepts(normalize(context)) | {
        (code, i) for i in range(len(catalog().get(code, ())))
    }
    common = len(found & target)
    overlap = len(tokens & course_tokens)
    return np.array([
        overlap > 0, overlap / max(np.sqrt(len(tokens) * len(course_tokens)), 1),
        common / max(np.sqrt(len(found) * len(target)), 1),
        bool(common), bool(found - target), min(common, 3),
        overlap / max(len(tokens), 1),
    ])


@lru_cache(maxsize=1)
def models():
    with np.load(ROOT / "models/title_validator_v2.npz", allow_pickle=False) as data:
        weights = {}
        for name, width in (("meaning", WIDTH + 8), ("relevance", 7)):
            coef, bias, threshold = (data[f"{name}_{suffix}"] for suffix in ("coef", "bias", "threshold"))
            if (coef.shape != (width,) or bias.shape or threshold.shape
                    or not np.isfinite(coef).all() or not np.isfinite(bias)
                    or not 0 < threshold < 1):
                raise ValueError("Invalid title validator artifact")
            weights[name] = coef, bias, threshold
        return weights


def score(features, model):
    coef, bias, _ = model
    return float(1 / (1 + np.exp(-np.clip(features @ coef + bias, -40, 40))))


def validate_title(title, code, context):
    weights = models()
    meaning = score(meaningful_features(title), weights["meaning"])
    if GENERIC.fullmatch(normalize(title)):
        return "INSUFFICIENT_CONTEXT", meaning, None
    normalized = normalize(title)
    if meaning < weights["meaning"][2] and normalized not in SHORT_TERMS and not concepts(normalized):
        return "MEANINGLESS_TITLE", meaning, None
    if not context.strip():
        return "INSUFFICIENT_CONTEXT", meaning, None
    features = relevance_features(title, code, context)
    relevance = score(features, weights["relevance"])
    if not code in catalog() and not any(features[:4]):
        return "INSUFFICIENT_CONTEXT", meaning, relevance
    cutoff = weights["relevance"][2]
    if relevance >= cutoff:
        return "ACCEPTED", meaning, relevance
    if cutoff - relevance <= .10:
        return "INSUFFICIENT_CONTEXT", meaning, relevance
    return "IRRELEVANT_TITLE", meaning, relevance
