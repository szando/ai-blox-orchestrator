from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Tuple

BlendMode = Literal["rrf", "linear"]
NormalizeMode = Literal["sigmoid", "none"]


@dataclass
class HybridScore:
    item_id: str
    score: float
    score_text: float | None
    score_vec: float | None
    rank_text: int | None
    rank_vec: int | None


class HybridScorer:
    def __init__(
        self,
        blend: BlendMode = "rrf",
        w_text: float = 0.35,
        w_vec: float = 0.65,
        normalize: NormalizeMode = "sigmoid",
        k: int = 60,
    ) -> None:
        self.blend = blend
        self.w_text = w_text
        self.w_vec = w_vec
        self.normalize = normalize
        self.k = k

    def fuse(
        self,
        text_results: Iterable[Tuple[str, float]],
        vec_results: Iterable[Tuple[str, float]],
        top_k: int,
    ) -> list[HybridScore]:
        text_scores = {item_id: score for item_id, score in text_results}
        vec_scores = {item_id: score for item_id, score in vec_results}

        text_ranked = self._rank_items(text_scores, reverse=True)
        vec_ranked = self._rank_items(vec_scores, reverse=True)

        text_norm = self._normalize_scores(text_scores) if self.blend == "linear" else text_ranked
        vec_norm = self._normalize_scores(vec_scores) if self.blend == "linear" else vec_ranked

        item_ids = set(text_scores) | set(vec_scores)
        fused: list[HybridScore] = []

        for item_id in item_ids:
            r_text = text_ranked.get(item_id)
            r_vec = vec_ranked.get(item_id)
            s_text = text_norm.get(item_id)
            s_vec = vec_norm.get(item_id)
            if self.blend == "linear":
                score = (self.w_text * (s_text or 0)) + (self.w_vec * (s_vec or 0))
            else:
                score = self._rrf_score(r_text, r_vec)
            fused.append(
                HybridScore(
                    item_id=item_id,
                    score=score,
                    score_text=text_scores.get(item_id),
                    score_vec=vec_scores.get(item_id),
                    rank_text=r_text,
                    rank_vec=r_vec,
                )
            )

        fused.sort(key=lambda s: s.score, reverse=True)
        return fused[:top_k]

    def _rrf_score(self, rank_text: int | None, rank_vec: int | None) -> float:
        score = 0.0
        if rank_text is not None:
            score += 1 / (self.k + rank_text)
        if rank_vec is not None:
            score += 1 / (self.k + rank_vec)
        return score

    def _rank_items(self, scores: Dict[str, float], reverse: bool = True) -> Dict[str, int]:
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=reverse)
        return {item_id: idx + 1 for idx, (item_id, _) in enumerate(sorted_results)}

    def _normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        if self.normalize == "none":
            return {k: float(v) for k, v in scores.items()}
        # TODO: implement real sigmoid/zscore; using min-max as placeholder
        if not scores:
            return {}
        min_score = min(scores.values())
        max_score = max(scores.values())
        if max_score == min_score:
            return {k: 1.0 for k in scores}
        return {k: (v - min_score) / (max_score - min_score) for k, v in scores.items()}
