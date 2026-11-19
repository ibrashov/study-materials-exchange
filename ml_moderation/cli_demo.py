"""Phase 16: Local interactive CLI demonstration for filename moderation.

Loads the actual trained production model (`ml_moderation/models/filename_moderator.joblib`)
and evaluates user-supplied filenames or material titles in real time.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_moderation.config import DEFAULT_MODEL_PATH
from ml_moderation.predictor import get_moderator


def format_result(filename: str, decision) -> str:
    status = "ALLOWED" if decision.allowed else "BLOCKED"
    lines = [
        f"Original input:   {filename}",
        f"Normalized input: {decision.normalized_text}",
        f"Decision:         {status} ({decision.reason})",
        f"Model confidence: {decision.confidence:.4f}",
        f"Inference time:   {decision.latency_ms:.3f} ms",
        f"Model version:    {decision.model_version}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive ML Filename Moderation CLI Demo")
    parser.add_argument("filenames", nargs="*", help="Optional filenames to evaluate non-interactively")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH, help="Path to joblib model artifact")
    args = parser.parse_args()

    moderator = get_moderator(args.model)

    if args.filenames:
        for fname in args.filenames:
            decision = moderator.moderate(fname)
            print(format_result(fname, decision))
            print("-" * 50)
        return

    print(f"ML Filename Moderation CLI (model={moderator.model_type}, v{moderator.model_version})")
    print("Type a filename or material title and press Enter (or 'exit' to quit).\n")
    while True:
        try:
            raw = input("Enter filename: ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if raw.strip().lower() in {"exit", "quit", "q"}:
            break
        decision = moderator.moderate(raw)
        print()
        print(format_result(raw, decision))
        print()


if __name__ == "__main__":
    main()
