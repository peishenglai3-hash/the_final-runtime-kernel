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


def project(history: Iterable[Event | Relation]) -> GraphView:
    """Build a stable projection that can be recreated from the same history."""

    nodes: dict[tuple[str, str], NodeRef] = {}
    relations: dict[str, Relation] = {}
    event_ids: list[str] = []

    for item in history:
        if isinstance(item, Event):
            event_ids.append(item.id)
            nodes[(item.actor.kind, item.actor.id)] = item.actor
            if item.target is not None:
                nodes[(item.target.kind, item.target.id)] = item.target
            for relation in _context_relations(item):
                relations[relation.id] = relation
                nodes[(relation.source.kind, relation.source.id)] = relation.source
                nodes[(relation.target.kind, relation.target.id)] = relation.target
        elif isinstance(item, Relation):
            relations[item.id] = item
            nodes[(item.source.kind, item.source.id)] = item.source
            nodes[(item.target.kind, item.target.id)] = item.target
        else:
            raise TypeError(f"unsupported history item: {type(item).__name__}")

    return GraphView(
        nodes=tuple(nodes[key] for key in sorted(nodes)),
        relations=tuple(relations[key] for key in sorted(relations)),
        event_ids=tuple(event_ids),
    )
