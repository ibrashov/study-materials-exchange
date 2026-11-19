"""Phase 5 Baselines: Conventional Blacklist and Fuzzy Matching moderators."""

from __future__ import annotations

import csv
from difflib import SequenceMatcher
from pathlib import Path
import re

from .config import PROFANITY_WORDS_PATH
from .normalization import normalize_text


def load_profanity_terms(path: Path = PROFANITY_WORDS_PATH) -> list[str]:
    """Load unique lowercase profanity terms from the curated CSV vocabulary."""
    terms: list[str] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            term = (row.get("word") or "").strip().casefold()
            if term and term not in seen:
                seen.add(term)
                terms.append(term)
    return terms


class BlacklistModerator:
    """Baseline A: Conventional prohibited-word blacklist (exact token or naive substring)."""

    def __init__(self, terms: list[str], match_mode: str = "substring") -> None:
        self.terms = [t.casefold().strip() for t in terms if t.strip()]
        self.term_set = set(self.terms)
        self.match_mode = match_mode

    def predict_one(self, text: str) -> tuple[int, float]:
        norm = normalize_text(text)
        raw_lower = norm.raw_clean
        tokens = re.findall(r"[a-zа-яёәіңғүұқөһ0-9]+", raw_lower)
        if self.match_mode == "exact":
            hit = any(tok in self.term_set for tok in tokens)
            return (1, 1.0) if hit else (0, 0.0)
        # Conventional naive substring blacklist (classic Scunthorpe-problem failure mode).
        for term in self.terms:
            if len(term) >= 3 and term in raw_lower:
                return 1, 1.0
        return 0, 0.0

    def predict(self, texts: list[str]) -> list[int]:
        return [self.predict_one(t)[0] for t in texts]

    def predict_proba(self, texts: list[str]) -> list[float]:
        return [self.predict_one(t)[1] for t in texts]


class FuzzyMatchingModerator:
    """Baseline B: Normalized token-level Levenshtein/SequenceMatcher fuzzy moderator."""

    def __init__(self, terms: list[str], similarity_threshold: float = 0.84) -> None:
        # Index terms by approximate length for faster CPU scanning.
        self.terms = [t.casefold().strip() for t in terms if len(t.strip()) >= 3]
        self.term_set = set(self.terms)
        self.by_length: dict[int, list[str]] = {}
        for term in self.terms:
            self.by_length.setdefault(len(term), []).append(term)
        self.threshold = similarity_threshold

    def _best_token_similarity(self, token: str) -> float:
        if token in self.term_set:
            return 1.0
        length = len(token)
        if length < 3:
            return 0.0
        best = 0.0
        # Only compare against terms of similar length to keep fuzzy search bounded.
        for candidate_len in range(max(3, length - 2), length + 3):
            for term in self.by_length.get(candidate_len, ()):
                # Quick upper-bound check on shared characters before full ratio.
                if token[0] != term[0] and token[-1] != term[-1] and length <= 4:
                    continue
                ratio = SequenceMatcher(None, token, term).ratio()
                if ratio > best:
                    best = ratio
                    if best >= 0.99:
                        return best
        return best

    def predict_one(self, text: str) -> tuple[int, float]:
        norm = normalize_text(text)
        tokens = set(norm.normalized.split()) | set(norm.deobfuscated.split())
        best_score = 0.0
        for tok in tokens:
            score = self._best_token_similarity(tok)
            if score > best_score:
                best_score = score
                if best_score >= 1.0:
                    break
        return (1 if best_score >= self.threshold else 0), float(best_score)

    def predict(self, texts: list[str]) -> list[int]:
        return [self.predict_one(t)[0] for t in texts]

    def predict_proba(self, texts: list[str]) -> list[float]:
        return [self.predict_one(t)[1] for t in texts]
