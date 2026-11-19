"""Backend integration wrapper for ML-based filename and material-title moderation."""

from __future__ import annotations

import logging
from fastapi import HTTPException

from ml_moderation.config import REJECTION_MESSAGE, UNAVAILABLE_MESSAGE
from ml_moderation.predictor import ModerationDecision, ModerationModelLoadError, get_moderator
from ..core.config import settings

logger = logging.getLogger(__name__)


def warmup_moderation() -> None:
    """Preload the trusted moderation model once during application startup."""
    try:
        moderator = get_moderator(settings.moderation_model_path)
        logger.info(
            "Filename moderation model loaded: type=%s version=%s threshold=%.4f",
            moderator.model_type,
            moderator.model_version,
            moderator.threshold,
        )
    except ModerationModelLoadError as exc:
        # Do not silently disable moderation; requests will explicitly fail closed with 503.
        logger.error("Filename moderation model failed to load at startup: %s", exc)


def enforce_material_moderation(title: str | None, filename: str | None) -> ModerationDecision:
    """Validate both material title and uploaded filename before storage or DB writes."""
    try:
        moderator = get_moderator(settings.moderation_model_path)
    except ModerationModelLoadError as exc:
        logger.error("Filename moderation unavailable: %s", exc)
        raise HTTPException(503, UNAVAILABLE_MESSAGE) from None

    decision = moderator.moderate_submission(title=title, filename=filename)
    if not decision.allowed:
        logger.info("Rejected upload by ML moderation: %s", decision.to_internal_dict())
        raise HTTPException(422, REJECTION_MESSAGE)
    return decision
