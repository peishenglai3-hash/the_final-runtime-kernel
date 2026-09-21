"""The five replaceable V1.0 operators with deterministic defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from .model import Event, EvidenceRef, Protocol
from .projection import GraphView


FrictionType = Literal[
    "execution",
    "semantic",
    "rule",
    "permission",
    "evidence",
    "goal",
    "coordination",
]
RouteName = Literal["pass", "local", "verify", "deep", "human"]
ValidationStatus = Literal["Valid", "Invalid", "InsufficientEvidence", "NotApplicable"]
StructuredReasoner = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class Budget:
    risk: float = 0.0
    cost: float = 0.0
    novelty: float = 0.0
    irreversibility: float = 0.0
    authority: float = 0.0

    def __post_init__(self) -> None:
        for name in ("risk", "cost", "novelty", "irreversibility", "authority"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"Budget.{name} must be between 0 and 1")


@dataclass(frozen=True)
class DetectResult:
    present: bool
    type: FrictionType | None = None
    severity: float | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.present and self.type is None:
            raise ValueError("a present friction requires a type")
        if self.severity is not None and not 0 <= self.severity <= 1:
            raise ValueError("DetectResult.severity must be between 0 and 1")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("DetectResult.confidence must be between 0 and 1")
        object.__setattr__(self, "signals", dict(self.signals or {}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "present": self.present,
            "type": self.type,
            "severity": self.severity,
            "signals": self.signals,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class AttributionResult:
    nodes: tuple[str, ...]
    relations: tuple[str, ...]
    rules: tuple[str, ...]
    confidence: float | None
    status: Literal["attributed", "partial", "unknown"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": list(self.nodes),
            "relations": list(self.relations),
            "rules": list(self.rules),
            "confidence": self.confidence,
            "status": self.status,
        }


@dataclass(frozen=True)
class RouteDecision:
    route: RouteName
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"route": self.route, "reasons": list(self.reasons)}


@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    evidence: tuple[EvidenceRef, ...]
    reasons: tuple[str, ...]
    validator: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "evidence": [item.to_dict() for item in self.evidence],
            "reasons": list(self.reasons),
            "validator": self.validator,
        }


class OperatorSet:
    """A replaceable operator bundle; no provider or manager hierarchy."""

    def __init__(self, reasoner: StructuredReasoner | None = None) -> None:
        self.reasoner = reasoner

    def detect(
        self,
        event: Event,
        graph: GraphView,
        protocols: tuple[Protocol, ...],
    ) -> DetectResult:
        context = event.context
        friction_type = context.get("friction_type")
        mismatch = event.expected is not None and event.observed != event.expected
        explicit = context.get("friction") is True
        external_veto = context.get("external_veto") is True
        missing_evidence = context.get("missing_evidence") is True
        if not (mismatch or explicit or external_veto or missing_evidence):
            return DetectResult(present=False)

        if external_veto:
            detected_type: FrictionType = "permission"
        elif missing_evidence:
            detected_type = "evidence"
        elif friction_type in {
            "execution",
            "semantic",
            "rule",
            "permission",
            "evidence",
            "goal",
            "coordination",
        }:
            detected_type = friction_type
        else:
            detected_type = "execution" if mismatch else "semantic"

        severity = float(context.get("severity", 0.7 if mismatch else 0.5))
        signals = {
            "mismatch": mismatch,
            "external_veto": external_veto,
            "missing_evidence": missing_evidence,
            "active_protocol_ids": [item.id for item in protocols],
            "graph_relation_count": len(graph.relations),
        }
        return DetectResult(
            present=True,
            type=detected_type,
            severity=severity,
            signals=signals,
            confidence=1.0 if mismatch or external_veto else 0.8,
        )

    def attribute(self, friction: DetectResult, graph: GraphView, event: Event) -> AttributionResult:
        if not friction.present:
            return AttributionResult((), (), (), 1.0, "attributed")
        node_ids = [event.actor.id]
        if event.target is not None:
            node_ids.append(event.target.id)
        involved = {(event.actor.kind, event.actor.id)}
        if event.target is not None:
            involved.add((event.target.kind, event.target.id))
        relation_ids = tuple(
            relation.id
            for relation in graph.relations
            if (relation.source.kind, relation.source.id) in involved
            or (relation.target.kind, relation.target.id) in involved
        )
        rules = tuple(str(item) for item in event.context.get("rules", []))
        if node_ids or relation_ids or rules:
            status: Literal["attributed", "partial", "unknown"] = "attributed"
            confidence = friction.confidence
        else:
            status = "unknown"
            confidence = None
        return AttributionResult(tuple(node_ids), relation_ids, rules, confidence, status)

    def route(
        self,
        friction: DetectResult,
        attribution: AttributionResult,
        budget: Budget,
    ) -> RouteDecision:
        if not friction.present:
            return RouteDecision("pass", ("no friction detected",))
        reasons: list[str] = []
        if budget.authority >= 0.8:
            reasons.append("authority boundary requires human gate")
        if budget.irreversibility >= 0.8:
            reasons.append("irreversible action requires human gate")
        if reasons:
            return RouteDecision("human", tuple(reasons))
        if budget.risk >= 0.7 or budget.novelty >= 0.7 or friction.type in {"permission", "evidence"}:
            return RouteDecision("verify", ("external evidence or elevated risk is required",))
        if attribution.status == "unknown":
            return RouteDecision("deep", ("attribution is unknown",))
        if (friction.severity or 0) <= 0.25 and budget.cost <= 0.25:
            return RouteDecision("local", ("low-severity reversible friction",))
        return RouteDecision("deep", ("objectification is warranted",))

    def compile(
        self,
        friction: DetectResult,
        attribution: AttributionResult,
        event: Event,
        protocols: tuple[Protocol, ...],
    ) -> Protocol:
        if not friction.present or friction.type is None:
            raise ValueError("cannot compile a protocol without friction")
        proposal: dict[str, Any] = {}
        if self.reasoner is not None:
            proposal = self.reasoner(
                {
                    "event": event.to_dict(),
                    "friction": friction.to_dict(),
                    "attribution": attribution.to_dict(),
                    "active_protocols": [item.to_dict() for item in protocols],
                }
            )
            if not isinstance(proposal, dict):
                raise TypeError("StructuredReasoner must return a dict")

        scope = dict(proposal.get("scope", event.context.get("protocol_scope", {})))
        action = dict(
            proposal.get(
                "action",
                event.context.get(
                    "suggested_action",
                    {"kind": "recorded-adaptation", "strategy": friction.type},
                ),
            )
        )
        validation = dict(
            proposal.get(
                "validation",
                {"resolves": friction.type, "expected": event.expected},
            )
        )
        veto_conditions = tuple(
            dict(item)
            for item in proposal.get("veto_conditions", event.context.get("veto_conditions", []))
        )
        required_evidence = tuple(
            str(item)
            for item in proposal.get(
                "required_evidence",
                [item.locator for item in event.evidence] or [f"event:{event.id}"],
            )
        )
        return Protocol(
            id=str(proposal.get("id", f"protocol:{event.id}:{friction.type}")),
            trigger={"event_id": event.id, "action": event.action, "friction_type": friction.type},
            action=action,
            scope=scope,
            required_evidence=required_evidence,
            validation=validation,
            veto_conditions=veto_conditions,
            provenance=event.evidence,
            status="candidate",
            version=int(proposal.get("version", 1)),
            confidence=proposal.get("confidence", friction.confidence),
        )

    def validate(
        self,
        candidate: Protocol,
        *,
        context: dict[str, Any],
    ) -> ValidationResult:
        validator = str(context.get("validator_type", "deterministic-scope-evidence-v1"))
        evidence = self._validation_evidence(context)
        if context.get("external_veto") is True:
            return ValidationResult("Invalid", evidence or candidate.provenance, ("external veto is binding",), validator)

        environment = candidate.scope.get("environment")
        current_environment = context.get("environment")
        if environment is not None and current_environment is not None and environment != current_environment:
            return ValidationResult(
                "NotApplicable",
                evidence,
                (f"scope environment {environment!r} does not match {current_environment!r}",),
                validator,
            )

        if not evidence:
            return ValidationResult(
                "InsufficientEvidence",
                (),
                ("validator did not provide external EvidenceRef",),
                validator,
            )

        available = {item.locator for item in evidence}
        missing = [item for item in candidate.required_evidence if item not in available]
        if missing:
            return ValidationResult(
                "InsufficientEvidence",
                evidence,
                tuple(f"missing evidence: {item}" for item in missing),
                validator,
            )

        requested = context.get("validation_status")
        if requested == "Invalid":
            return ValidationResult("Invalid", evidence, ("context requested invalidation",), validator)
        if requested == "NotApplicable":
            return ValidationResult("NotApplicable", evidence, ("context marked protocol not applicable",), validator)
        if requested == "InsufficientEvidence":
            return ValidationResult(
                "InsufficientEvidence",
                evidence,
                ("context withheld sufficient evidence",),
                validator,
            )
        return ValidationResult("Valid", evidence, ("scope and evidence checks passed",), validator)

    @staticmethod
    def _validation_evidence(context: dict[str, Any]) -> tuple[EvidenceRef, ...]:
        raw = context.get("validation_evidence", [])
        if not isinstance(raw, list):
            raise TypeError("context.validation_evidence must be a list")
        evidence: list[EvidenceRef] = []
        for item in raw:
            if isinstance(item, EvidenceRef):
                evidence.append(item)
            elif isinstance(item, dict):
                evidence.append(EvidenceRef.from_dict(item))
            else:
                raise TypeError("context.validation_evidence must contain EvidenceRef objects")
        return tuple(evidence)
