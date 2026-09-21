"""The explicit V1.0 runtime loop."""

from __future__ import annotations

from typing import Any, Protocol

from .model import Event, EvidenceRef, jsonable
from .operators import Budget, OperatorSet
from .projection import project
from .store import JsonlStore


class Adapter(Protocol):
    def normalize(self, raw_input: Any) -> list[Event]: ...


class Kernel:
    """Orchestrate Adapter -> Store -> Projection -> D/A/R/C/V."""

    def __init__(
        self,
        adapter: Adapter,
        store: JsonlStore,
        operators: OperatorSet | None = None,
        budget: Budget | None = None,
    ) -> None:
        self.adapter = adapter
        self.store = store
        self.operators = operators or OperatorSet()
        self.budget = budget or Budget()

    def process(self, raw_input: Any) -> tuple[dict[str, Any], ...]:
        events = self.adapter.normalize(raw_input)
        if not isinstance(events, list) or not all(isinstance(item, Event) for item in events):
            raise TypeError("Adapter.normalize must return list[Event]")

        results: list[dict[str, Any]] = []
        for event in events:
            self.store.append_event(event)
            graph = project(self.store.list_history())
            protocols = self.store.list_active_protocols()
            friction = self.operators.detect(event, graph, protocols)
            if not friction.present:
                results.append(
                    {
                        "event_id": event.id,
                        "friction": friction.to_dict(),
                        "route": {"route": "pass", "reasons": ["no friction detected"]},
                        "outcome": "no-op",
                    }
                )
                continue

            attribution = self.operators.attribute(friction, graph, event)
            route = self.operators.route(friction, attribution, self.budget)
            result: dict[str, Any] = {
                "event_id": event.id,
                "friction": friction.to_dict(),
                "attribution": attribution.to_dict(),
                "route": route.to_dict(),
            }
            if route.route in {"pass", "local"}:
                result["outcome"] = "local-no-op"
                results.append(result)
                continue

            candidate = self.operators.compile(friction, attribution, event, protocols)
            validation = self.operators.validate(candidate, context=event.context)
            result["candidate"] = candidate.to_dict()
            result["validation"] = validation.to_dict()
            if validation.status == "Valid":
                active = candidate.with_status("active")
                self.store.save_protocol(active)
                result["protocol"] = active.to_dict()
                result["outcome"] = "committed"
            elif validation.status in {"Invalid", "NotApplicable"}:
                self.store.record_rejection(candidate, validation.to_dict())
                result["outcome"] = "rejected"
            else:
                self.store.record_pending(candidate, validation.to_dict())
                result["outcome"] = "pending"
            results.append(result)
        return tuple(jsonable(item) for item in results)

    def revoke(self, protocol_id: str, evidence: tuple[EvidenceRef, ...]) -> dict[str, Any]:
        revoked = self.store.revoke_protocol(protocol_id, evidence)
        return revoked.to_dict()
