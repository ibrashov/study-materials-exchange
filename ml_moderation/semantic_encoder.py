"""Optional local ONNX inference shared by experiments and the preview backend."""
from functools import lru_cache

import numpy as np

from ml_moderation.cli_demo_v2 import COURSES
from ml_moderation.validator_v2 import catalog


class Encoder:
    def __init__(self, name, folder):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(folder / "model.onnx"), options,
                                           providers=["CPUExecutionProvider"])
        self.inputs = {node.name for node in self.session.get_inputs()}
        self.tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=128)
        pad_id = self.tokenizer.token_to_id("[PAD]")
        if pad_id is None:
            pad_id = self.tokenizer.token_to_id("<pad>")
        self.tokenizer.enable_padding(pad_id=pad_id, pad_token=self.tokenizer.id_to_token(pad_id))
        self.e5 = name == "e5"

    def embed(self, texts, query):
        batch = self.tokenizer.encode_batch(
            [("query: " if query else "passage: ") + t for t in texts] if self.e5 else texts
        )
        values = {
            "input_ids": np.array([row.ids for row in batch], dtype=np.int64),
            "attention_mask": np.array([row.attention_mask for row in batch], dtype=np.int64),
            "token_type_ids": np.array([row.type_ids for row in batch], dtype=np.int64),
        }
        hidden = self.session.run(["last_hidden_state"], {key: values[key] for key in self.inputs})[0]
        mask = values["attention_mask"][:, :, None].astype(np.float32)
        pooled = (hidden * mask).sum(axis=1) / mask.sum(axis=1).clip(min=1)
        return (pooled / np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-12)).astype(np.float32)

    @lru_cache(maxsize=32)
    def course(self, code, context=None):
        groups = catalog()[code]
        return self.embed([(context or COURSES[code]) + ": " + "; ".join(", ".join(g) for g in groups),
                           *[", ".join(group) for group in groups]], query=False)


def interaction(title_vector, context):
    similarity = context[1:] @ title_vector
    return [float(context[0] @ title_vector), similarity.max(), similarity.mean(),
            np.sort(similarity)[-2], similarity.std(),
            np.abs(context[0] - title_vector).mean()]
