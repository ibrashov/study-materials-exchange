"""Inspect the complete upload policy locally."""
import argparse
import json
from time import perf_counter

from ml_moderation.predictor import get_moderator
from ml_moderation.validator_v2 import validate_title

COURSES = {
    "DB101": "Database Systems",
    "PROG101": "Introduction to Programming",
    "BIS101": "Basics of Information Systems",
}


def inspect(title, filename, code):
    start = perf_counter()
    moderation = get_moderator().moderate_submission(title=title, filename=filename)
    reason, meaningfulness, relevance = (
        validate_title(title, code, COURSES[code])
        if moderation.allowed else ("INAPPROPRIATE_CONTENT", None, None)
    )
    return {
        "course": f"{code} — {COURSES[code]}", "title": title,
        "moderation_passed": moderation.allowed, "meaningfulness": meaningfulness,
        "relevance": relevance, "decision": reason, "inference_ms": (perf_counter() - start) * 1000,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course", choices=COURSES)
    parser.add_argument("title", nargs="?")
    parser.add_argument("--compare", choices=COURSES)
    parser.add_argument("--filename", default="document_123.pdf")
    args = parser.parse_args()
    title = args.title if args.title is not None else input("Material title: ")
    for code in filter(None, (args.course, args.compare)):
        print(json.dumps(inspect(title, args.filename, code), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
