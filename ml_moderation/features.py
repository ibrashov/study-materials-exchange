"""Shared feature extraction for character-level filename moderation models.

Supports comparing raw-only, normalized-only, and combined raw+normalized
character n-grams alongside lightweight obfuscation-signal features.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

import numpy as np

from .normalization import NormalizedText, normalize_text


SIGNAL_SCALE = 0.20


def extract_signal_vector(norm: NormalizedText) -> list[float]:
    """Compute 9 lightweight scaled numeric obfuscation signals from normalized text."""
    stem = norm.stem or ""
    length = max(len(stem), 1)
    upper_count = sum(1 for ch in stem if ch.isupper())
    alpha_count = max(sum(1 for ch in stem if ch.isalpha()), 1)
    digit_count = sum(1 for ch in stem if ch.isdigit())
    symbol_count = sum(1 for ch in stem if ch in "@$!*#%^~`")
    raw = [
        float(norm.has_invisible),
        float(norm.has_mixed_script),
        float(norm.has_excessive_repeat),
        float(norm.has_leet),
        float(norm.has_inserted_digits),
        float(norm.has_split_chars),
        upper_count / alpha_count,
        digit_count / length,
        symbol_count / length,
    ]
    return [v * SIGNAL_SCALE for v in raw]


class FilenameFeatureExtractor:
    """Multi-view character n-gram TF-IDF + numeric obfuscation signal extractor."""

    def __init__(
        self,
        mode: str = "combined",
        ngram_range: tuple[int, int] = (2, 5),
        max_features_raw: int = 12000,
        max_features_norm: int = 18000,
    ) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        if mode not in ("raw", "normalized", "combined"):
            raise ValueError(f"Unsupported feature mode: {mode}")
        self.mode = mode
        self.ngram_range = ngram_range
        self.max_features_raw = max_features_raw
        self.max_features_norm = max_features_norm

        self.raw_vectorizer = (
            TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=ngram_range,
                max_features=max_features_raw,
                sublinear_tf=True,
                dtype=np.float32,
            )
            if mode in ("raw", "combined")
            else None
        )
        self.norm_vectorizer = (
            TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=ngram_range,
                max_features=max_features_norm,
                sublinear_tf=True,
                dtype=np.float32,
            )
            if mode in ("normalized", "combined")
            else None
        )

    def _prepare_views(self, texts: Iterable[str]) -> tuple[list[str], list[str], Any]:
        from scipy import sparse

        raw_docs: list[str] = []
        norm_docs: list[str] = []
        signals: list[list[float]] = []
        for text in texts:
            n = normalize_text(text)
            raw_docs.append(n.raw_clean)
            norm_docs.append(n.combined_model_text)
            signals.append(extract_signal_vector(n))
        sig_mat = sparse.csr_matrix(np.asarray(signals, dtype=np.float32))
        return raw_docs, norm_docs, sig_mat

    def fit_transform(self, texts: Iterable[str]) -> Any:
        from scipy import sparse

        raw_docs, norm_docs, sig_mat = self._prepare_views(texts)
        blocks = []
        if self.raw_vectorizer is not None:
            blocks.append(self.raw_vectorizer.fit_transform(raw_docs))
        if self.norm_vectorizer is not None:
            blocks.append(self.norm_vectorizer.fit_transform(norm_docs))
        if self.mode == "combined":
            blocks.append(sig_mat)
        return sparse.hstack(blocks, format="csr", dtype=np.float32)

    def transform(self, texts: Iterable[str]) -> Any:
        from scipy import sparse

        raw_docs, norm_docs, sig_mat = self._prepare_views(texts)
        blocks = []
        if self.raw_vectorizer is not None:
            blocks.append(self.raw_vectorizer.transform(raw_docs))
        if self.norm_vectorizer is not None:
            blocks.append(self.norm_vectorizer.transform(norm_docs))
        if self.mode == "combined":
            blocks.append(sig_mat)
        return sparse.hstack(blocks, format="csr", dtype=np.float32)

    def export_portable(self) -> dict:
        """Export vectorizer vocabularies and IDF weights into version-agnostic dict."""
        data: dict = {
            "mode": self.mode,
            "ngram_range": list(self.ngram_range),
            "sublinear_tf": True,
        }
        if self.raw_vectorizer is not None:
            data["raw_vocab"] = {k: int(v) for k, v in self.raw_vectorizer.vocabulary_.items()}
            data["raw_idf"] = self.raw_vectorizer.idf_.astype(np.float32)
        if self.norm_vectorizer is not None:
            data["norm_vocab"] = {k: int(v) for k, v in self.norm_vectorizer.vocabulary_.items()}
            data["norm_idf"] = self.norm_vectorizer.idf_.astype(np.float32)
        return data


def _char_wb_ngrams(text: str, min_n: int, max_n: int) -> list[str]:
    """Replicate scikit-learn TfidfVectorizer(analyzer='char_wb') tokenization."""
    ngrams: list[str] = []
    for word in text.split():
        padded = f" {word} "
        plen = len(padded)
        for n in range(min_n, min(max_n, plen) + 1):
            for i in range(plen - n + 1):
                ngrams.append(padded[i : i + n])
    return ngrams


def _portable_tfidf_dot(
    text: str,
    vocab: dict[str, int],
    idf: np.ndarray,
    coef_slice: np.ndarray,
    min_n: int,
    max_n: int,
) -> float:
    """Compute exact L2-normalized sublinear char_wb TF-IDF dot product for a single string."""
    counts: dict[int, int] = {}
    for ng in _char_wb_ngrams(text, min_n, max_n):
        idx = vocab.get(ng)
        if idx is not None:
            counts[idx] = counts.get(idx, 0) + 1
    if not counts:
        return 0.0

    norm_sq = 0.0
    dot = 0.0
    for idx, cnt in counts.items():
        val = (1.0 + math.log(cnt)) * float(idf[idx])
        norm_sq += val * val
        dot += val * float(coef_slice[idx])
    if norm_sq <= 0.0:
        return 0.0
    return dot / math.sqrt(norm_sq)


def portable_linear_logit(norm: NormalizedText, artifact: dict) -> float:
    """Compute exact linear logit from a version-agnostic exported linear artifact."""
    min_n, max_n = int(artifact["ngram_range"][0]), int(artifact["ngram_range"][1])
    coef: np.ndarray = artifact["coef"]
    intercept = float(artifact["intercept"])
    offset = 0
    total = intercept

    if "raw_vocab" in artifact:
        raw_idf = artifact["raw_idf"]
        size = len(raw_idf)
        total += _portable_tfidf_dot(
            norm.raw_clean, artifact["raw_vocab"], raw_idf, coef[offset : offset + size], min_n, max_n
        )
        offset += size

    if "norm_vocab" in artifact:
        norm_idf = artifact["norm_idf"]
        size = len(norm_idf)
        total += _portable_tfidf_dot(
            norm.combined_model_text, artifact["norm_vocab"], norm_idf, coef[offset : offset + size], min_n, max_n
        )
        offset += size

    if artifact.get("mode") == "combined" and offset < len(coef):
        sigs = extract_signal_vector(norm)
        sig_coef = coef[offset : offset + len(sigs)]
        for s_val, w_val in zip(sigs, sig_coef):
            total += s_val * float(w_val)

    return total
