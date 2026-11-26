"""NumPy-only static relevance student, independent of its ONNX teacher."""
import re
from collections import Counter
from functools import lru_cache
from zlib import crc32

import numpy as np

from ml_moderation.validator_v2 import ROOT, normalize, relevance_features

WIDTH = 8192
CODES = ("DB101", "PROG101", "BIS101")


def bag(text):
    features = Counter()
    for word in re.findall(r"[^\W_]+", normalize(text)):
        features[crc32(("w:" + word).encode()) % WIDTH] += 2
        marked = f"^{word}$"
        for width in (3, 4):
            for offset in range(len(marked) - width + 1):
                token = marked[offset:offset + width]
                features[crc32(("s:" + token).encode()) % WIDTH] += 1
    norm = sum(v * v for v in features.values()) ** .5 or 1
    return {key: value / norm for key, value in features.items()}


def unit(vector):
    return vector / np.linalg.norm(vector, axis=-1, keepdims=True).clip(min=1e-9)


def embed(text, matrix):
    weights = bag(text)
    return unit(np.asarray(list(weights.values()), dtype=np.float32) @ matrix[list(weights)])


def interactions(title_vector, contexts, course):
    selected = CODES.index(course)
    full = contexts[:, 0] @ title_vector
    topics = np.sort(contexts[:, 1:] @ title_vector, axis=1)
    margin = full[selected] - max(full[i] for i in range(len(CODES)) if i != selected)
    return np.array([full[selected], topics[selected, -1], topics[selected, -3:].mean(),
                     margin, topics[selected, -1] - max(topics[i, -1]
                                                       for i in range(len(CODES)) if i != selected)])


def feature_row(title, course, context, matrix, contexts):
    return np.r_[interactions(embed(title, matrix), contexts, course),
                 relevance_features(title, course, context)]


@lru_cache(maxsize=1)
def load_student():
    with np.load(ROOT / "models/title_validator_v2_2.npz", allow_pickle=False) as asset:
        return (asset["quantized"].astype(np.float32) * asset["scale"], asset["contexts"],
                asset["coef"], float(asset["bias"]), float(asset["upper"]), float(asset["lower"]))


def predict_student(title, course, context):
    if course not in CODES:
        return "INSUFFICIENT_CONTEXT"
    matrix, contexts, coef, bias, upper, lower = load_student()
    value = float(np.sum(feature_row(title, course, context, matrix, contexts) * coef) + bias)
    return "ACCEPTED" if value >= upper else "IRRELEVANT_TITLE" if value < lower else "INSUFFICIENT_CONTEXT"
