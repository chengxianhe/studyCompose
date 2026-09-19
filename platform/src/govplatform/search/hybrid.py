from __future__ import annotations

from typing import NamedTuple

from govplatform import embedding as embedding_module
from govplatform.knowledge.models import KnowledgeObject
from govplatform.knowledge.store import StoredEmbedding
from govplatform.search.index import BM25Corpus

_RRF_K = 60
# 每一路排序只取前 N 个参与融合，避免语料量大了之后把明显不相关的结果也
# 拖进来陪跑。语料量还小的时候这个上限基本不起作用（候选总数远小于它）。
_CANDIDATE_POOL_SIZE = 20


class RankResult(NamedTuple):
    results: list[tuple[KnowledgeObject, float]]
    # 这次排序里向量那一路是不是真的贡献了结果——模型挂了、或者候选里没有
    # 一个能比的向量（比如都用旧模型算的），都会是 False，调用方（以后的
    # Harness）可以据此判断"这次检索证据是不是缺了语义那一路"，不用去猜。
    used_vector_search: bool


def rank(
    candidates: list[tuple[KnowledgeObject, StoredEmbedding]],
    query: str,
    limit: int,
) -> RankResult:
    objects = [obj for obj, _embedding in candidates]

    bm25_hits = BM25Corpus(objects).query(query, limit=_CANDIDATE_POOL_SIZE)
    bm25_rank_of = {obj.knowledge_id: rank for rank, (obj, _score) in enumerate(bm25_hits, start=1)}

    # 向量模型查询期挂了（跟写入期一样可能发生）不该让搜索整个报错——
    # 退化成只用 BM25 那一路，总比搜索功能直接不可用强。
    try:
        query_embedding: bytes | None = embedding_module.embed(query)
    except Exception:
        query_embedding = None

    vector_rank_of: dict[str, int] = {}
    if query_embedding is not None:
        # 只拿"用同一个模型算出来的"向量参与比较——向量没算成功
        # （stored.vector is None）或者是用别的模型算的（换模型之后的旧
        # 数据），都跳过，不硬比不能比的东西。
        vector_hits = sorted(
            (
                (obj, embedding_module.cosine_similarity(query_embedding, stored.vector))
                for obj, stored in candidates
                if stored.vector is not None and stored.model == embedding_module.MODEL_NAME
            ),
            key=lambda pair: pair[1],
            reverse=True,
        )[:_CANDIDATE_POOL_SIZE]
        vector_rank_of = {
            obj.knowledge_id: rank for rank, (obj, _score) in enumerate(vector_hits, start=1)
        }

    # 用 Reciprocal Rank Fusion 合并两路排序：只看"排第几"，不看原始分数，
    # 因为 BM25 分数和余弦相似度根本不是一个量纲，没法直接相加。命中任意
    # 一路的都保留，两路都命中的排名自然靠前。
    hit_ids = set(bm25_rank_of) | set(vector_rank_of)
    fused_scores = {
        knowledge_id: (
            (1.0 / (_RRF_K + bm25_rank_of[knowledge_id]) if knowledge_id in bm25_rank_of else 0.0)
            + (
                1.0 / (_RRF_K + vector_rank_of[knowledge_id])
                if knowledge_id in vector_rank_of
                else 0.0
            )
        )
        for knowledge_id in hit_ids
    }

    objects_by_id = {obj.knowledge_id: obj for obj in objects}
    ranked_ids = sorted(fused_scores, key=lambda kid: fused_scores[kid], reverse=True)
    results = [(objects_by_id[kid], fused_scores[kid]) for kid in ranked_ids[:limit]]
    return RankResult(results=results, used_vector_search=len(vector_rank_of) > 0)
