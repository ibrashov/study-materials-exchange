"""Production predictor for ML-based filename and material-title moderation.

Loads a trusted joblib artifact once per process, executes fast CPU-only inference
without external AI APIs, applies validation-tuned thresholds and an explicit
uncertain-zone policy, and fails explicitly if the model artifact cannot load.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import threading
import time
from typing import Any

import joblib
import numpy as np

from .config import (
    DEFAULT_MODEL_PATH,
    DEFAULT_THRESHOLD,
    DEFAULT_UNCERTAIN_HIGH,
    DEFAULT_UNCERTAIN_LOW,
    MODEL_VERSION,
)
from .features import portable_linear_logit
from .normalization import NormalizedText, normalize_text


class ModerationModelLoadError(RuntimeError):
    """Raised explicitly when the moderation model artifact cannot be loaded."""


@dataclass(frozen=True)
class ModerationDecision:
    """Structured moderation result returned by the predictor."""

    allowed: bool
    reason: str
    confidence: float
    model_version: str
    normalized_text: str
    latency_ms: float
    policy_zone: str = "confident"

    def to_internal_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "confidence": round(self.confidence, 4),
            "model_version": self.model_version,
        }


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


class FilenameModerator:
    """Thread-safe CPU filename and title moderator backed by a trusted joblib artifact."""

    REQUIRED_KEYS = {"artifact_format", "model_type", "model_version", "threshold", "coef", "intercept", "ngram_range"}

    def __init__(self, model_path: Path | str = DEFAULT_MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        self._artifact: dict[str, Any] = self._load_trusted_artifact(self.model_path)
        self.model_version: str = str(self._artifact.get("model_version", MODEL_VERSION))
        self.model_type: str = str(self._artifact.get("model_type", "unknown"))
        self.threshold: float = float(self._artifact.get("threshold", DEFAULT_THRESHOLD))
        self.uncertain_low: float = float(self._artifact.get("uncertain_low", DEFAULT_UNCERTAIN_LOW))
        self.uncertain_high: float = float(self._artifact.get("uncertain_high", DEFAULT_UNCERTAIN_HIGH))
        self._exact_terms: frozenset[str] = frozenset(self._artifact.get("hybrid_exact_terms", ()))
        self._safe_hard_negatives: frozenset[str] = frozenset(self._artifact.get("safe_exact_words", ()))

    @classmethod
    def _load_trusted_artifact(cls, path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise ModerationModelLoadError(f"Moderation model artifact not found: {path}")
        try:
            artifact = joblib.load(path)
        except Exception as exc:
            raise ModerationModelLoadError(f"Failed to load moderation model artifact: {exc}") from exc
        if not isinstance(artifact, dict):
            raise ModerationModelLoadError("Invalid moderation artifact format: expected dict")
        missing = cls.REQUIRED_KEYS - set(artifact.keys())
        if missing:
            raise ModerationModelLoadError(f"Moderation artifact missing required keys: {sorted(missing)}")
        if artifact.get("artifact_format") != "portable_linear_v1":
            raise ModerationModelLoadError(f"Unsupported artifact_format: {artifact.get('artifact_format')}")
        artifact["coef"] = np.asarray(artifact["coef"], dtype=np.float32)
        if "raw_idf" in artifact:
            artifact["raw_idf"] = np.asarray(artifact["raw_idf"], dtype=np.float32)
        if "norm_idf" in artifact:
            artifact["norm_idf"] = np.asarray(artifact["norm_idf"], dtype=np.float32)
        return artifact

    def _raw_probability(self, norm: NormalizedText) -> float:
        logit = portable_linear_logit(norm, self._artifact)
        # Optional Platt scaling parameters if calibrated LinearSVC was selected.
        platt_a = float(self._artifact.get("platt_a", 1.0))
        platt_b = float(self._artifact.get("platt_b", 0.0))
        prob = _sigmoid(platt_a * logit + platt_b)

        # Optional deterministic high-precision logit boost when Model D (Hybrid) is selected.
        if self._exact_terms:
            tokens = set(norm.normalized.split()) | set(norm.deobfuscated.split())
            # Never trigger deterministic boost on single clean academic words (e.g., "pass").
            if not (len(tokens) == 1 and next(iter(tokens)) in self._safe_hard_negatives):
                if any(tok in self._exact_terms for tok in tokens):
                    prob = _sigmoid(platt_a * (logit + 5.0) + platt_b)
        return float(prob)

    def predict_proba_one(self, text: str | None) -> float:
        norm = normalize_text(text)
        if not norm.normalized and not norm.raw_clean:
            return 0.0
        return self._raw_probability(norm)

    def moderate(self, text: str | None) -> ModerationDecision:
        """Evaluate a filename or title and return a structured ModerationDecision."""
        started = time.perf_counter()
        norm = normalize_text(text)
        if not norm.normalized and not norm.raw_clean:
            elapsed = (time.perf_counter() - started) * 1000.0
            return ModerationDecision(
                allowed=True,
                reason="empty_input",
                confidence=0.0,
                model_version=self.model_version,
                normalized_text="",
                latency_ms=elapsed,
                policy_zone="empty",
            )

        # 1-2 character clean tokens (e.g., "n.pdf", "AI.pdf", "ML.pdf", "ДЗ.pdf")
        # cannot form a >=3-character prohibited word when no obfuscation is present.
        compact_len = len(norm.normalized.replace(" ", ""))
        if compact_len < 3 and not (norm.has_leet or norm.has_split_chars or norm.has_invisible):
            elapsed = (time.perf_counter() - started) * 1000.0
            return ModerationDecision(
                allowed=True,
                reason="allowed",
                confidence=0.0,
                model_version=self.model_version,
                normalized_text=norm.normalized,
                latency_ms=elapsed,
                policy_zone="short_clean",
            )

        prob = self._raw_probability(norm)
        has_obf = (
            norm.has_invisible
            or norm.has_mixed_script
            or norm.has_excessive_repeat
            or norm.has_leet
            or norm.has_inserted_digits
            or norm.has_split_chars
        )

        # Documented threshold and uncertain-zone policy:
        # 1) >= threshold: clearly inappropriate -> BLOCK.
        # 2) [uncertain_low, threshold): uncertain band -> block only when explicit
        #    obfuscation signals are present (prevents evasive borderline attacks while
        #    protecting clean academic terminology from unnecessary false positives).
        # 3) < uncertain_low: clearly allowed -> ALLOW.
        if prob >= self.threshold:
            allowed = False
            reason = "inappropriate_filename"
            zone = "blocked_confident"
        elif prob >= self.uncertain_low and has_obf:
            allowed = False
            reason = "inappropriate_filename"
            zone = "blocked_uncertain_obfuscated"
        else:
            allowed = True
            reason = "allowed"
            zone = "allowed_uncertain_clean" if prob >= self.uncertain_low else "allowed_confident"

        elapsed = (time.perf_counter() - started) * 1000.0
        return ModerationDecision(
            allowed=allowed,
            reason=reason,
            confidence=prob,
            model_version=self.model_version,
            normalized_text=norm.normalized,
            latency_ms=elapsed,
            policy_zone=zone,
        )

    def moderate_submission(self, title: str | None, filename: str | None) -> ModerationDecision:
        """Moderate both material title and uploaded filename, rejecting if either is inappropriate."""
        checks = []
        if title and title.strip():
            checks.append(self.moderate(title))
        if filename and filename.strip():
            checks.append(self.moderate(filename))
        if not checks:
            return ModerationDecision(
                allowed=True,
                reason="empty_input",
                confidence=0.0,
                model_version=self.model_version,
                normalized_text="",
                latency_ms=0.0,
                policy_zone="empty",
            )
        blocked = [c for c in checks if not c.allowed]
        if blocked:
            return max(blocked, key=lambda c: c.confidence)
        return max(checks, key=lambda c: c.confidence)


_LOCK = threading.Lock()
_SINGLETON: FilenameModerator | None = None
_SINGLETON_PATH: Path | None = None


def get_moderator(model_path: Path | str = DEFAULT_MODEL_PATH) -> FilenameModerator:
    """Return a process-wide cached FilenameModerator loaded once on startup."""
    global _SINGLETON, _SINGLETON_PATH
    resolved = Path(model_path).resolve()
    if _SINGLETON is not None and _SINGLETON_PATH == resolved:
        return _SINGLETON
    with _LOCK:
        if _SINGLETON is not None and _SINGLETON_PATH == resolved:
            return _SINGLETON
        instance = FilenameModerator(resolved)
        _SINGLETON = instance
        _SINGLETON_PATH = resolved
        return instance


def reset_moderator_cache() -> None:
    """Clear the cached singleton (used in tests for failure and reload scenarios)."""
    global _SINGLETON, _SINGLETON_PATH
    with _LOCK:
        _SINGLETON = None
        _SINGLETON_PATH = None
