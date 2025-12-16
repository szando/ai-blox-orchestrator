from __future__ import annotations

import asyncio
import time
from typing import Iterable, List, Sequence

from aiblox_orchestrator.chunker.models import ChunkingOptions
from aiblox_orchestrator.chunker.protocols import ChunkerRegistry
from aiblox_orchestrator.protocol.context import RequestContext
from aiblox_orchestrator.retriever.embedder import DeterministicEmbedder
from aiblox_orchestrator.retriever.hybrid_scorer import HybridScorer
from aiblox_orchestrator.retriever.models import CandidateItem, EvidenceChunk, RetrievalBundle, RetrievalPrefs, RetrievalStats
from aiblox_orchestrator.retriever.protocols import Embedder, Retriever
from aiblox_orchestrator.storage.models import KbItem
from aiblox_orchestrator.storage.chunk_cache_repo import ChunkCacheRepo
from aiblox_orchestrator.storage.item_repo import ItemRepo


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class HybridRetriever(Retriever):
    def __init__(
        self,
        item_repo: ItemRepo,
        chunker_registry: ChunkerRegistry,
        embedder: Embedder | None = None,
        chunk_cache_repo: ChunkCacheRepo | None = None,
        hybrid_scorer: HybridScorer | None = None,
    ) -> None:
        self.item_repo = item_repo
        self.chunker_registry = chunker_registry
        self.embedder = embedder or DeterministicEmbedder()
        self.chunk_cache_repo = chunk_cache_repo or ChunkCacheRepo()
        self.hybrid_scorer = hybrid_scorer or HybridScorer()

    async def search(self, ctx: RequestContext, prefs: RetrievalPrefs) -> RetrievalBundle:
        timings: dict[str, float] = {}
        counts: dict[str, int] = {}
        params = {"fts": prefs.fts, "vector": prefs.vector, "chunking": prefs.chunking}

        start = time.perf_counter()
        fts_results = await self.item_repo.search_fts(prefs.query_text, prefs)
        timings["fts_ms"] = (time.perf_counter() - start) * 1000
        counts["fts"] = len(fts_results)

        query_vec: Sequence[float] | None = None
        vec_results: list[tuple[str, float]] = []
        if prefs.vector.get("embed_query", True):
            start = time.perf_counter()
            query_vec = await self.embedder.embed_query(prefs.query_text)
            vec_results = await self.item_repo.search_vec(query_vec, prefs)
            timings["vec_ms"] = (time.perf_counter() - start) * 1000
            counts["vec"] = len(vec_results)

        fused = self.hybrid_scorer.fuse(
            text_results=fts_results,
            vec_results=vec_results,
            top_k=prefs.top_k_items,
        )

        item_ids = [score.item_id for score in fused]
        items = await self.item_repo.fetch_items_by_ids(item_ids)
        item_map = {item.id: item for item in items}

        candidates: List[CandidateItem] = []
        for score in fused:
            item = item_map.get(score.item_id)
            if ctx.cancelled():
                raise asyncio.CancelledError()
            if not item:
                continue
            candidates.append(
                CandidateItem(
                    item_id=item.id,
                    kind=item.kind,
                    source=item.source,
                    source_ref=item.source_ref,
                    title=item.title,
                    summary=item.summary,
                    metadata=getattr(item, "metadata_", None) or {},
                    score=score.score,
                    score_text=float(score.score_text) if score.score_text is not None else None,
                    score_vec=float(score.score_vec) if score.score_vec is not None else None,
                    rank_text=score.rank_text,
                    rank_vec=score.rank_vec,
                )
            )

        evidence = await self._late_chunk(
            ctx=ctx,
            prefs=prefs,
            candidates=candidates,
            item_map=item_map,
            query_vec=query_vec,
        )

        stats = RetrievalStats(
            timing_ms=timings,
            counts={**counts, "candidates": len(candidates), "evidence": len(evidence)},
            params=params if prefs.debug else {},
        )
        return RetrievalBundle(candidates=candidates, evidence=evidence, stats=stats)

    async def _late_chunk(
        self,
        ctx: RequestContext,
        prefs: RetrievalPrefs,
        candidates: list[CandidateItem],
        item_map: dict[str, KbItem],
        query_vec: Sequence[float] | None,
    ) -> list[EvidenceChunk]:
        if not candidates:
            return []
        chunker_id = prefs.chunking.get("chunker_id", "default")
        chunker = self.chunker_registry.get(chunker_id)
        options = ChunkingOptions(
            include_headers=prefs.chunking.get("include_headers", True),
            max_chunk_tokens=prefs.chunking.get("max_chunk_tokens"),
            overlap_tokens=prefs.chunking.get("overlap_tokens"),
        )

        evidence: list[EvidenceChunk] = []
        for candidate in candidates:
            if ctx.cancelled():
                raise asyncio.CancelledError()
            item = item_map.get(candidate.item_id)
            if not item or not getattr(item, "content_text", None):
                continue
            text: str = item.content_text
            cached = []
            if prefs.cache.get("use_chunk_cache", True):
                cached = await self.chunk_cache_repo.get_cached_chunks(
                    item_id=candidate.item_id,
                    content_hash=getattr(item, "content_hash", None),
                    chunker_id=chunker_id,
                    embed_model_id=getattr(self.embedder, "model_id", "unknown"),
                )
            if cached:
                for cache_row in cached:
                    evidence.append(EvidenceChunk(**cache_row))
                continue

            chunks = chunker.chunk(text, options)
            chunk_texts = [c.text for c in chunks]
            chunk_vecs: list[Sequence[float]] = []
            if query_vec:
                chunk_vecs = await self.embedder.embed_texts(chunk_texts)
            per_item = []
            for idx, chunk in enumerate(chunks):
                vec_score = _cosine_similarity(query_vec, chunk_vecs[idx]) if query_vec and chunk_vecs else 0.0
                ev = EvidenceChunk(
                    item_id=candidate.item_id,
                    chunk_id=f"{candidate.item_id}:{chunk.chunk_index}",
                    text=chunk.text,
                    start_idx=chunk.start_idx,
                    end_idx=chunk.end_idx,
                    token_count=chunk.token_count,
                    score=vec_score,
                    score_text=None,
                    score_vec=vec_score,
                    heading_path=chunk.heading_path,
                    anchors=chunk.anchors,
                )
                per_item.append(ev)
            per_item.sort(key=lambda c: c.score_vec or c.score, reverse=True)
            per_item = per_item[: prefs.per_item_chunk_cap]
            evidence.extend(per_item)

            if prefs.cache.get("write_chunk_cache", True) and per_item:
                await self.chunk_cache_repo.write_cached_chunks(
                    item_id=candidate.item_id,
                    content_hash=getattr(item, "content_hash", None),
                    chunker_id=chunker_id,
                    embed_model_id=getattr(self.embedder, "model_id", "unknown"),
                    chunks=[ev.model_dump() for ev in per_item],
                )

        evidence.sort(key=lambda c: c.score_vec or c.score, reverse=True)
        return evidence[: prefs.top_k_chunks]
