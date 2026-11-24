"""Evidence-bounded advisory exploration of explicitly scored relations."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Iterable

from .model import Relation


MAX_EXPLORATION_CANDIDATES = 3


@dataclass(frozen=True)
class ExplorationCandidate:
    relation: Relation
    score: float
    cutoff: float

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "advisory",
            "activation": False,
            "relation": self.relation.to_dict(),
            "score": self.score,
            "ordinary_cutoff": self.cutoff,
            "evidence": [item.to_dict() for item in self.relation.provenance],
            "explanation": (
                f"Relation score {self.score:g} is nonzero and below ordinary cutoff "
                f"{self.cutoff:g}; inspect its recorded evidence before using it."
            ),
        }


def explore_low_score_relations(
    relations: Iterable[Relation],
    *,
    max_score: float = 0.4,
    limit: int = MAX_EXPLORATION_CANDIDATES,
) -> tuple[ExplorationCandidate, ...]:
    """Surface up to three evidence-backed, nonzero relations below ``max_score``.

    This function reads existing relation data only. It neither creates relations nor
    changes Kernel decisions, Store history, or protocol status.
    """

    if isinstance(max_score, bool) or not isinstance(max_score, (int, float)):
        raise TypeError("max_score must be a finite number in (0, 1]")
    if not math.isfinite(max_score) or not 0 < max_score <= 1:
        raise ValueError("max_score must be a finite number in (0, 1]")
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer from 1 to 3")
    if not 1 <= limit <= MAX_EXPLORATION_CANDIDATES:
        raise ValueError("limit must be an integer from 1 to 3")

    def eligible() -> Iterable[tuple[float, str, ExplorationCandidate]]:
        for relation in relations:
            if not isinstance(relation, Relation) or not relation.provenance:
                continue
            raw_score = relation.attributes.get("score")
            if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
                continue
            score = float(raw_score)
            if not math.isfinite(score) or not 0 < score < max_score:
                continue
            candidate = ExplorationCandidate(relation, score, float(max_score))
            # Higher weak scores sit nearer the usual cutoff; IDs break ties reliably.
            yield (-score, relation.id, candidate)

    ranked = heapq.nsmallest(limit, eligible(), key=lambda item: (item[0], item[1]))
    return tuple(item[2] for item in ranked)
