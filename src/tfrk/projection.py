"""Derive a GraphView from history; no graph store is maintained."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .model import Event, NodeRef, Relation


@dataclass(frozen=True)
class GraphView:
    nodes: tuple[NodeRef, ...]
    relations: tuple[Relation, ...]
    event_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "relations": [relation.to_dict() for relation in self.relations],
            "event_ids": list(self.event_ids),
        }


def _context_relations(event: Event) -> Iterable[Relation]:
    """Read optional adapter relation projections without widening Event's schema."""

    raw = event.context.get("relation")
    values = event.context.get("relations", [])
    if values is None:
        values = []
    if not isinstance(values, list):
        raise ValueError(f"event relations context must be a list: {event.id}")
    values = list(values)
    if raw is not None:
        values.insert(0, raw)
    for item in values:
        if not isinstance(item, dict):
            raise ValueError(f"event relation context must be an object: {event.id}")
        yield Relation.from_dict(item)


class _ProjectionAccumulator:
    """Ephemeral projection builder; the JSONL history remains the authority."""

    def __init__(self) -> None:
        self.nodes: dict[tuple[str, str], NodeRef] = {}
        self.relations: dict[str, Relation] = {}
        self.event_ids: list[str] = []

    def add(self, item: Event | Relation) -> None:
        if isinstance(item, Event):
            self.event_ids.append(item.id)
            self.nodes[(item.actor.kind, item.actor.id)] = item.actor
            if item.target is not None:
                self.nodes[(item.target.kind, item.target.id)] = item.target
            for relation in _context_relations(item):
                self._add_relation(relation)
        elif isinstance(item, Relation):
            self._add_relation(item)
        else:
            raise TypeError(f"unsupported history item: {type(item).__name__}")

    def _add_relation(self, relation: Relation) -> None:
        if relation.id in self.relations:
            raise ValueError(f"duplicate relation id in history: {relation.id}")
        self.relations[relation.id] = relation
        self.nodes[(relation.source.kind, relation.source.id)] = relation.source
        self.nodes[(relation.target.kind, relation.target.id)] = relation.target

    def view(self) -> GraphView:
        return GraphView(
            nodes=tuple(self.nodes[key] for key in sorted(self.nodes)),
            relations=tuple(self.relations[key] for key in sorted(self.relations)),
            event_ids=tuple(self.event_ids),
        )


def project(history: Iterable[Event | Relation]) -> GraphView:
    """Build a stable projection that can be recreated from the same history."""

    accumulator = _ProjectionAccumulator()
    for item in history:
        accumulator.add(item)
    return accumulator.view()
