"""ML-based filename and material-title moderation package (Week 12)."""

from .config import MODEL_VERSION
from .normalization import NormalizedText, normalize_text

__all__ = ["MODEL_VERSION", "NormalizedText", "normalize_text"]
