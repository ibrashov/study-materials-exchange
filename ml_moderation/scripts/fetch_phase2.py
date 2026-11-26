"""Download and verify the exact public INT8 weights used in the experiment."""
import hashlib
import shutil
from urllib.request import urlopen

from ml_moderation.validator_v2 import ROOT

SOURCES = {
    "e5": (
        "intfloat/multilingual-e5-small", "614241f622f53c4eeff9890bdc4f31cfecc418b3",
        "model_qint8_avx512_vnni.onnx",
        "dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88",
        "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
    ),
    "minilm": (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "e8f8c211226b894fcb81acc59f3b34ba3efd5f42", "model_quint8_avx2.onnx",
        "98a01d88b7de996cdea58c32ca71208c09968d143798814b2ea09d3439dc334f",
        "2c3387be76557bd40970cec13153b3bbf80407865484b209e655e5e4729076b8",
    ),
}


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    for name, (repo, rev, filename, model_hash, tokenizer_hash) in SOURCES.items():
        folder = ROOT / "datasets/generated/phase2" / name
        folder.mkdir(parents=True, exist_ok=True)
        for remote, local, checksum in (
            (f"onnx/{filename}", "model.onnx", model_hash),
            ("tokenizer.json", "tokenizer.json", tokenizer_hash),
        ):
            target = folder / local
            if target.is_file() and digest(target) == checksum:
                continue
            temporary = target.with_suffix(".download")
            try:
                with urlopen(f"https://huggingface.co/{repo}/resolve/{rev}/{remote}", timeout=60) as response:
                    with temporary.open("wb") as stream:
                        shutil.copyfileobj(response, stream)
                if digest(temporary) != checksum:
                    raise ValueError(f"Wrong checksum for {repo}/{remote}")
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
