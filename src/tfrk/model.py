"""Frozen V1.0 domain contracts and deterministic JSON conversion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


ProtocolStatus = Literal["candidate", "active", "contested", "revoked"]


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _utc_datetime(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("timestamp must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def datetime_to_json(value: datetime) -> str:
    return _utc_datetime(value).isoformat().replace("+00:00", "Z")


def datetime_from_json(value: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError("timestamp JSON value must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _utc_datetime(parsed)


@dataclass(frozen=True)
class NodeRef:
    id: str
    kind: str
    label: str | None = None

    def __post_init__(self) -> None:
        _non_empty(self.id, "NodeRef.id")
        _non_empty(self.kind, "NodeRef.kind")
        if self.label is not None and not isinstance(self.label, str):
            raise TypeError("NodeRef.label must be a string or None")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "label": self.label}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> NodeRef:
        return cls(id=value["id"], kind=value["kind"], label=value.get("label"))


@dataclass(frozen=True)
class EvidenceRef:
    source: str
    kind: str
    locator: str
    digest: str | None = None

    def __post_init__(self) -> None:
        _non_empty(self.source, "EvidenceRef.source")
        _non_empty(self.kind, "EvidenceRef.kind")
        _non_empty(self.locator, "EvidenceRef.locator")
        if self.digest is not None and not isinstance(self.digest, str):
            raise TypeError("EvidenceRef.digest must be a string or None")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "kind": self.kind,
            "locator": self.locator,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EvidenceRef:
        return cls(
            source=value["source"],
            kind=value["kind"],
            locator=value["locator"],
            digest=value.get("digest"),
        )


@dataclass(frozen=True)
class Event:
    id: str
    actor: NodeRef
    action: str
    observed: Any
    timestamp: datetime
    target: NodeRef | None = None
    context: dict[str, Any] = field(default_factory=dict)
    expected: Any | None = None
    evidence: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        _non_empty(self.id, "Event.id")
        _non_empty(self.action, "Event.action")
        if not isinstance(self.actor, NodeRef):
            raise TypeError("Event.actor must be a NodeRef")
        if self.target is not None and not isinstance(self.target, NodeRef):
            raise TypeError("Event.target must be a NodeRef or None")
        if not isinstance(self.context, dict):
            raise TypeError("Event.context must be a dict")
        object.__setattr__(self, "context", dict(self.context))
        object.__setattr__(self, "timestamp", _utc_datetime(self.timestamp))
        evidence = tuple(self.evidence)
        if not all(isinstance(item, EvidenceRef) for item in evidence):
            raise TypeError("Event.evidence must contain EvidenceRef values")
        object.__setattr__(self, "evidence", evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "actor": self.actor.to_dict(),
            "action": self.action,
            "target": self.target.to_dict() if self.target else None,
            "context": jsonable(self.context),
            "expected": jsonable(self.expected),
            "observed": jsonable(self.observed),
            "evidence": [item.to_dict() for item in self.evidence],
            "timestamp": datetime_to_json(self.timestamp),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Event:
        target = value.get("target")
        return cls(
            id=value["id"],
            actor=NodeRef.from_dict(value["actor"]),
            action=value["action"],
            observed=value.get("observed"),
            timestamp=datetime_from_json(value["timestamp"]),
            target=NodeRef.from_dict(target) if target else None,
            context=dict(value.get("context", {})),
            expected=value.get("expected"),
            evidence=tuple(EvidenceRef.from_dict(item) for item in value.get("evidence", [])),
        )


@dataclass(frozen=True)
class Relation:
    id: str
    source: NodeRef
    target: NodeRef
    kind: str
    attributes: dict[str, Any] = field(default_factory=dict)
    provenance: tuple[EvidenceRef, ...] = ()
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    def __post_init__(self) -> None:
        _non_empty(self.id, "Relation.id")
        _non_empty(self.kind, "Relation.kind")
        if not isinstance(self.source, NodeRef) or not isinstance(self.target, NodeRef):
            raise TypeError("Relation source and target must be NodeRef values")
        if not isinstance(self.attributes, dict):
            raise TypeError("Relation.attributes must be a dict")
        object.__setattr__(self, "attributes", dict(self.attributes))
        provenance = tuple(self.provenance)
        if not all(isinstance(item, EvidenceRef) for item in provenance):
            raise TypeError("Relation.provenance must contain EvidenceRef values")
        object.__setattr__(self, "provenance", provenance)
        if self.valid_from is not None:
            object.__setattr__(self, "valid_from", _utc_datetime(self.valid_from))
        if self.valid_to is not None:
            object.__setattr__(self, "valid_to", _utc_datetime(self.valid_to))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "kind": self.kind,
            "attributes": jsonable(self.attributes),
            "provenance": [item.to_dict() for item in self.provenance],
            "valid_from": datetime_to_json(self.valid_from) if self.valid_from else None,
            "valid_to": datetime_to_json(self.valid_to) if self.valid_to else None,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Relation:
        return cls(
            id=value["id"],
            source=NodeRef.from_dict(value["source"]),
            target=NodeRef.from_dict(value["target"]),
            kind=value["kind"],
            attributes=dict(value.get("attributes", {})),
            provenance=tuple(EvidenceRef.from_dict(item) for item in value.get("provenance", [])),
            valid_from=datetime_from_json(value["valid_from"]) if value.get("valid_from") else None,
            valid_to=datetime_from_json(value["valid_to"]) if value.get("valid_to") else None,
        )


@dataclass(frozen=True)
class Protocol:
    id: str
    trigger: dict[str, Any]
    action: dict[str, Any]
    scope: dict[str, Any]
    required_evidence: tuple[str, ...]
    validation: dict[str, Any]
    veto_conditions: tuple[dict[str, Any], ...]
    provenance: tuple[EvidenceRef, ...]
    status: ProtocolStatus
    version: int
    confidence: float | None = None

    def __post_init__(self) -> None:
        _non_empty(self.id, "Protocol.id")
        if self.status not in {"candidate", "active", "contested", "revoked"}:
            raise ValueError(f"unsupported Protocol.status: {self.status}")
        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("Protocol.version must be a positive integer")
        for name in ("trigger", "action", "scope", "validation"):
            value = getattr(self, name)
            if not isinstance(value, dict):
                raise TypeError(f"Protocol.{name} must be a dict")
            object.__setattr__(self, name, dict(value))
        required = tuple(self.required_evidence)
        if not all(isinstance(item, str) and item for item in required):
            raise TypeError("Protocol.required_evidence must contain non-empty strings")
        object.__setattr__(self, "required_evidence", required)
        veto_items = tuple(self.veto_conditions)
        if not all(isinstance(item, dict) for item in veto_items):
            raise TypeError("Protocol.veto_conditions must contain dict values")
        veto = tuple(dict(item) for item in veto_items)
        object.__setattr__(self, "veto_conditions", veto)
        provenance = tuple(self.provenance)
        if not all(isinstance(item, EvidenceRef) for item in provenance):
            raise TypeError("Protocol.provenance must contain EvidenceRef values")
        object.__setattr__(self, "provenance", provenance)
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("Protocol.confidence must be between 0 and 1")

    def with_status(
        self,
        status: ProtocolStatus,
        *,
        provenance: tuple[EvidenceRef, ...] | None = None,
        version: int | None = None,
    ) -> Protocol:
        return Protocol(
            id=self.id,
            trigger=self.trigger,
            action=self.action,
            scope=self.scope,
            required_evidence=self.required_evidence,
            validation=self.validation,
            veto_conditions=self.veto_conditions,
            provenance=provenance if provenance is not None else self.provenance,
            status=status,
            version=version if version is not None else self.version,
            confidence=self.confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trigger": jsonable(self.trigger),
            "action": jsonable(self.action),
            "scope": jsonable(self.scope),
            "required_evidence": list(self.required_evidence),
            "validation": jsonable(self.validation),
            "veto_conditions": jsonable(self.veto_conditions),
            "provenance": [item.to_dict() for item in self.provenance],
            "status": self.status,
            "version": self.version,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Protocol:
        return cls(
            id=value["id"],
            trigger=dict(value.get("trigger", {})),
            action=dict(value.get("action", {})),
            scope=dict(value.get("scope", {})),
            required_evidence=tuple(value.get("required_evidence", [])),
            validation=dict(value.get("validation", {})),
            veto_conditions=tuple(value.get("veto_conditions", [])),
            provenance=tuple(EvidenceRef.from_dict(item) for item in value.get("provenance", [])),
            status=value["status"],
            version=value["version"],
            confidence=value.get("confidence"),
        )


def jsonable(value: Any) -> Any:
    """Convert supported values without changing their semantic shape."""

    if isinstance(value, datetime):
        return datetime_to_json(value)
    if isinstance(value, (NodeRef, EvidenceRef, Event, Relation, Protocol)):
        return value.to_dict()
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    return value
