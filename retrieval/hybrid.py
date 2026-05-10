"""Stage 1+2: hybrid dense+BM25 retrieval with server-side RRF fusion.

Per docs/TIER_2_SPEC.md §5 Stages 1-2. One Qdrant Query-API call:
  - dense prefetch (voyage-context-3 query embedding) limit=80
  - BM25 sparse prefetch (FastEmbed Qdrant/bm25) limit=80
  - server-side RRF fusion -> top K (default 60)

Per-source weights from Routing are not natively supported by Qdrant's
Fusion.RRF, so we emulate them by adjusting per-prefetch limits, boosting
the side the router favors. Equivalent to weighted RRF at this scale per
hybrid_search_rerank_2026.md §1.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import voyageai
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from voyageai.error import RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from retrieval.router import Routing

COLLECTION = "chunks"
DENSE_NAME = "dense"
SPARSE_NAME = "bm25"
DEFAULT_FUSED_K = 60
PREFETCH_TOTAL = 160  # 80 dense + 80 sparse, redistributed by routing weight

DENSE_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-context-3")
SPARSE_MODEL = "Qdrant/bm25"
DIM = int(os.getenv("EMBEDDING_DIM", "1024"))


@dataclass
class Hit:
    chunk_id: str
    score: float
    payload: dict[str, Any]


@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=8, min=15, max=90),
    stop=stop_after_attempt(5),
    reraise=True,
)
def embed_query_dense(vo: voyageai.Client, query: str) -> list[float]:
    """voyage-context-3 only ships via the contextualized_embed API. We embed
    the query as a 1-element document so the vector lives in the same space
    as the indexed document vectors."""
    res = vo.contextualized_embed(
        inputs=[[query]],
        model=DENSE_MODEL,
        input_type="query",
        output_dimension=DIM,
    )
    return res.results[0].embeddings[0]


def embed_query_sparse(sp: SparseTextEmbedding, query: str) -> qm.SparseVector:
    embs = list(sp.query_embed([query]))
    e = embs[0]
    return qm.SparseVector(indices=e.indices.tolist(), values=e.values.tolist())


def _split_prefetch(routing: Routing, total: int = PREFETCH_TOTAL) -> tuple[int, int]:
    """Distribute prefetch budget between dense and sparse by routing weight."""
    dense_n = max(20, int(round(total * routing.dense_w)))
    sparse_n = max(20, total - dense_n)
    return dense_n, sparse_n


def hybrid_search(
    qc: QdrantClient,
    vo: voyageai.Client,
    sp: SparseTextEmbedding,
    query: str,
    routing: Routing,
    fused_k: int = DEFAULT_FUSED_K,
    filters: qm.Filter | None = None,
) -> list[Hit]:
    """Run dense + BM25 prefetch with RRF fusion. Returns up to fused_k hits."""
    dense_vec = embed_query_dense(vo, query)
    sparse_vec = embed_query_sparse(sp, query)
    dense_n, sparse_n = _split_prefetch(routing)

    res = qc.query_points(
        collection_name=COLLECTION,
        prefetch=[
            qm.Prefetch(query=dense_vec, using=DENSE_NAME, limit=dense_n, filter=filters),
            qm.Prefetch(
                query=qm.SparseVector(indices=sparse_vec.indices, values=sparse_vec.values),
                using=SPARSE_NAME,
                limit=sparse_n,
                filter=filters,
            ),
        ],
        query=qm.FusionQuery(fusion=qm.Fusion.RRF),
        limit=fused_k,
        with_payload=True,
    )

    return [
        Hit(chunk_id=p.payload["chunk_id"], score=p.score, payload=dict(p.payload))
        for p in res.points
    ]
