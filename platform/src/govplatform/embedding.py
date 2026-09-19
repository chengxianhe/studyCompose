from __future__ import annotations

from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding

# 向量记录要跟这个名字一起存，换模型之后旧向量和新查询向量维度/语义空间
# 都可能对不上，不能直接比余弦相似度——见 knowledge/store.py 里怎么用它。
MODEL_NAME = "BAAI/bge-small-zh-v1.5"


@lru_cache(maxsize=1)
def _get_model() -> TextEmbedding:
    return TextEmbedding(model_name=MODEL_NAME)


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
