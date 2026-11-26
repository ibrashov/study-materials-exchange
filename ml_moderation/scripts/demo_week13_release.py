"""Demonstrate real Week 13 policies without connecting to a server or database."""
import argparse
import logging
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from backend.app.services.moderation import enforce_material_moderation
from backend.app.services.title_validation import enforce_title_validation
from ml_moderation.cli_demo_v2 import COURSES, inspect

FILENAME = "document_123.pdf"
PARAPHRASE = "Storing an address only once when several orders share it"
UNRELATED = "Why changing one list unexpectedly changes a second name"


def simulate(title, code, model, mode="shadow"):
    course = SimpleNamespace(course_code=code, course_name=COURSES[code], description=None)
    with patch.dict("os.environ", MATERIAL_OPTIONS | {
        "MATERIAL_VALIDATOR_V2_MODEL": model, "MATERIAL_VALIDATOR_V2_2_MODE": mode,
    }):
        try:
            enforce_material_moderation(title=title, filename=FILENAME)
            enforce_title_validation(title, course)
        except HTTPException as error:
            return f"HTTP {error.status_code}: {error.detail}"
    return "Allowed by validation"


MATERIAL_OPTIONS = {"MATERIAL_VALIDATOR_V2_ENABLED": "true"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--without-minilm", action="store_true", help="Skip the optional ONNX example")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for code, title in (
        ("DB101", "pppAAASSSS"), ("DB101", "asdfghjkl"), ("DB101", "Hello"),
        ("DB101", "SQL Joins and Queries"), ("PROG101", "SQL Joins and Queries"),
        ("DB101", PARAPHRASE),
    ):
        result = inspect(title, FILENAME, code)
        print(f"V2.0 | {code} | {title} | {result['decision']}")
    if not args.without_minilm:
        print(f"MiniLM | DB101 | {PARAPHRASE} | {simulate(PARAPHRASE, 'DB101', 'minilm_preview')}")
    for mode in ("shadow", "enforce"):
        print(f"V2.2 {mode} | BIS101 | {UNRELATED} | {simulate(UNRELATED, 'BIS101', 'v2_2', mode)}")


if __name__ == "__main__":
    main()
