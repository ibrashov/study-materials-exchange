"""Experimental MiniLM upload policy for local evaluation."""
import json
from functools import lru_cache
from threading import Lock

from ml_moderation.scripts.fetch_phase2 import SOURCES, digest
from ml_moderation.semantic_encoder import Encoder
from ml_moderation.validator_v2 import GENERIC, ROOT, catalog, normalize

_load_lock = Lock()


@lru_cache(maxsize=1)
def load_preview():
    folder = ROOT / "datasets/generated/phase2/minilm"
    if (digest(folder / "model.onnx"), digest(folder / "tokenizer.json")) != SOURCES["minilm"][-2:]:
        raise ValueError("MiniLM artifact checksum mismatch")
    source = ROOT / "reports/week13/phase2/preview_policy.json"
    policy = json.loads(source.read_text(encoding="utf8"))
    cutoff, lower = policy["accept"], policy["clarify"]
    if not -1 <= lower <= cutoff <= 1:
        raise ValueError("Invalid MiniLM decision cutoffs")
    return Encoder("minilm", folder), cutoff, lower


def preview_decision(title, code, context, baseline):
    if code not in catalog() or baseline == "MEANINGLESS_TITLE":
        return baseline
    if GENERIC.fullmatch(normalize(title)):
        return baseline
    with _load_lock:
        encoder, cutoff, lower = load_preview()
    similarity = float(encoder.course(code, context)[0] @ encoder.embed([title], query=True)[0])
    if similarity >= cutoff:
        return "ACCEPTED"
    if similarity >= lower:
        return "INSUFFICIENT_CONTEXT"
    return "IRRELEVANT_TITLE"
