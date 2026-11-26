"""Map private model decisions to the public upload error contract."""
import logging
import os

from fastapi import HTTPException

from ml_moderation.validator_v2 import validate_title

logger = logging.getLogger(__name__)
MESSAGES = {
    "MEANINGLESS_TITLE": "Please provide a meaningful material title.",
    "IRRELEVANT_TITLE": (
        "The material title does not match the selected course. "
        "Please provide a relevant academic title."
    ),
    "INSUFFICIENT_CONTEXT": "Please include the topic of the lecture or assignment in the material title.",
}


def enforce_title_validation(title, course):
    if os.getenv("MATERIAL_VALIDATOR_V2_ENABLED", "false").lower() not in {"true", "1"}:
        return
    context = " ".join(filter(None, (course.course_name, course.description)))
    selection = os.getenv("MATERIAL_VALIDATOR_V2_MODEL", "v2_0")
    mode = os.getenv("MATERIAL_VALIDATOR_V2_2_MODE", "shadow").lower()
    if selection == "v2_2" and mode == "off":
        return
    try:
        reason, _, _ = validate_title(title, course.course_code, context)
        if selection == "minilm_preview":
            from ml_moderation.semantic_preview import preview_decision

            reason = preview_decision(title, course.course_code, context, reason)
        elif selection == "v2_2":
            from ml_moderation.static_student import predict_student
            from ml_moderation.validator_v2 import GENERIC, normalize

            if mode not in {"shadow", "enforce"}:
                raise ValueError("Unknown static student mode")
            if reason != "MEANINGLESS_TITLE" and not GENERIC.fullmatch(normalize(title)):
                reason = predict_student(title, course.course_code, context)
            if mode == "shadow":
                logger.info("Static title validation result: %s", reason)
                return
            if reason == "INSUFFICIENT_CONTEXT":
                return
        elif selection != "v2_0":
            raise ValueError("Unknown title validation model")
    except Exception as error:
        if selection == "v2_2" and mode == "shadow":
            logger.warning("Static title validation unavailable (%s)", type(error).__name__)
            return
        logger.exception("Material title validator unavailable")
        raise HTTPException(503, "Material title validation is temporarily unavailable.") from None
    if reason != "ACCEPTED":
        raise HTTPException(422, MESSAGES[reason])
