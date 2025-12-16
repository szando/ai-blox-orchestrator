from __future__ import annotations

from typing import Protocol

from aiblox_orchestrator.evidence.models import EvidencePackOptions, SourceItem
from aiblox_orchestrator.retriever.models import CandidateItem, EvidenceChunk


class EvidencePacker(Protocol):
    def pack(
        self,
        candidates: list[CandidateItem],
        evidence_chunks: list[EvidenceChunk] | None,
        options: EvidencePackOptions,
    ) -> list[SourceItem]:
        ...
