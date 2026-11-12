from __future__ import annotations

from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding

from govplatform import model_cache

MODEL_NAME = model_cache.MODEL_NAME


@lru_cache(maxsize=1)
def _get_model() -> TextEmbedding:
    return model_cache.load_model(allow_download=True)


def embed(text: str) -> bytes:
    vector = next(iter(_get_model().embed([text])))
    return vector.astype("float32").tobytes()


def cosine_similarity(a: bytes, b: bytes) -> float:
    vec_a = np.frombuffer(a, dtype="float32")
    vec_b = np.frombuffer(b, dtype="float32")
    denom = float(np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / denom)
