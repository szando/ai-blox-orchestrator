from __future__ import annotations

from typing import Dict, List, Optional

from aiblox_orchestrator.evidence.models import EvidencePackOptions, SourceItem
from aiblox_orchestrator.evidence.protocols import EvidencePacker
from aiblox_orchestrator.retriever.models import CandidateItem, EvidenceChunk


class DefaultEvidencePacker(EvidencePacker):
    """Deterministic evidence packer producing SourceItem list."""

    def pack(
        self,
        candidates: List[CandidateItem],
        evidence_chunks: Optional[List[EvidenceChunk]],
        options: EvidencePackOptions,
    ) -> List[SourceItem]:
        ordered = self._order_candidates(candidates, options)
        selected = ordered[: options.max_sources]
        result: List[SourceItem] = []
        for idx, cand in enumerate(selected):
            snippet, snippet_from = self._select_snippet(cand, evidence_chunks, options)
            metadata = self._filter_metadata(cand.metadata or {}, options)
            result.append(
                SourceItem(
                    source_id=cand.item_id,
                    kind=cand.kind,
                    title=cand.title,
                    url=cand.source_ref,
                    snippet=snippet,
                    snippet_from=snippet_from,
                    score=cand.score,
                    rank=idx + 1,
                    metadata=metadata,
                )
            )
        return result

    def _order_candidates(
        self,
        candidates: List[CandidateItem],
        options: EvidencePackOptions,
    ) -> List[CandidateItem]:
        if options.order_by == "input":
            return list(candidates)
        if options.order_by == "rank":
            def rank_key(c: CandidateItem) -> tuple:
                rank = c.rank_text or c.rank_vec
                return (rank if rank is not None else float("inf"), -(c.score or 0.0))
            return sorted(candidates, key=rank_key)
        # default: score
        return sorted(candidates, key=lambda c: (c.score is None, -(c.score or 0.0)))

    def _select_snippet(
        self,
        candidate: CandidateItem,
        evidence_chunks: Optional[List[EvidenceChunk]],
        options: EvidencePackOptions,
    ) -> tuple[Optional[str], str]:
        if options.prefer_chunk_snippets and evidence_chunks:
            matching = [c for c in evidence_chunks if c.item_id == candidate.item_id]
            if matching:
                best = sorted(matching, key=lambda c: (c.score is None, -(c.score or 0.0)))[0]
                snippet = (best.text or "")[: options.max_snippet_chars]
                snippet_from = "chunk"
                return snippet, snippet_from
        # doc fallback
        snippet_source = candidate.summary or candidate.snippet
        if snippet_source:
            return snippet_source[: options.max_snippet_chars], "doc"
        return None, "unknown"

    def _filter_metadata(
        self,
        metadata: Dict[str, object],
        options: EvidencePackOptions,
    ) -> Dict[str, object]:
        if metadata is None:
            metadata = {}
        if options.include_metadata_keys is not None:
            metadata = {k: v for k, v in metadata.items() if k in options.include_metadata_keys}
        if options.exclude_metadata_keys is not None:
            metadata = {k: v for k, v in metadata.items() if k not in options.exclude_metadata_keys}
        return metadata
