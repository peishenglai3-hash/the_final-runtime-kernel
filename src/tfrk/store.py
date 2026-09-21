"""One append-only JSONL store for V1.0 history and protocol versions."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

from .model import Event, EvidenceRef, Protocol, Relation


class JsonlStore:
    """A small replayable store; the JSONL file is the only source of truth."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _append(self, kind: str, payload: dict[str, Any]) -> None:
        record = {"kind": kind, "payload": payload}
        line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _records(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSONL at {self.path}:{number}") from exc
                if not isinstance(record, dict) or not isinstance(record.get("payload"), dict):
                    raise ValueError(f"invalid store record at {self.path}:{number}")
                yield record

    def append_event(self, event: Event) -> None:
        if any(record.get("kind") == "event" and record["payload"].get("id") == event.id for record in self._records()):
            raise ValueError(f"event already exists: {event.id}")
        self._append("event", event.to_dict())

    def append_relation(self, relation: Relation) -> None:
        if any(record.get("kind") == "relation" and record["payload"].get("id") == relation.id for record in self._records()):
            raise ValueError(f"relation already exists: {relation.id}")
        self._append("relation", relation.to_dict())

    def list_history(self) -> tuple[Event | Relation, ...]:
        history: list[Event | Relation] = []
        for record in self._records():
            if record.get("kind") == "event":
                history.append(Event.from_dict(record["payload"]))
            elif record.get("kind") == "relation":
                history.append(Relation.from_dict(record["payload"]))
        return tuple(history)

    def list_events(self) -> tuple[Event, ...]:
        return tuple(item for item in self.list_history() if isinstance(item, Event))

    def list_relations(self) -> tuple[Relation, ...]:
        return tuple(item for item in self.list_history() if isinstance(item, Relation))

    def save_protocol(self, protocol: Protocol) -> None:
        latest = self.latest_protocol(protocol.id)
        if latest is not None and protocol.version <= latest.version:
            raise ValueError(
                f"protocol version must increase: {protocol.id} {protocol.version} <= {latest.version}"
            )
        self._append("protocol", protocol.to_dict())

    def protocol_history(self) -> tuple[Protocol, ...]:
        return tuple(
            Protocol.from_dict(record["payload"])
            for record in self._records()
            if record.get("kind") == "protocol"
        )

    def latest_protocol(self, protocol_id: str) -> Protocol | None:
        versions = [item for item in self.protocol_history() if item.id == protocol_id]
        return max(versions, key=lambda item: item.version, default=None)

    def list_active_protocols(self) -> tuple[Protocol, ...]:
        latest: dict[str, Protocol] = {}
        for protocol in self.protocol_history():
            previous = latest.get(protocol.id)
            if previous is None or protocol.version > previous.version:
                latest[protocol.id] = protocol
        return tuple(
            sorted(
                (protocol for protocol in latest.values() if protocol.status == "active"),
                key=lambda item: item.id,
            )
        )

    def record_rejection(self, candidate: Protocol, result: dict[str, Any]) -> None:
        self._append(
            "decision",
            {"outcome": "rejected", "protocol": candidate.to_dict(), "result": result},
        )

    def record_pending(self, candidate: Protocol, result: dict[str, Any]) -> None:
        self._append(
            "decision",
            {"outcome": "pending", "protocol": candidate.to_dict(), "result": result},
        )

    def decision_history(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            record["payload"]
            for record in self._records()
            if record.get("kind") == "decision"
        )

    def revoke_protocol(self, protocol_id: str, evidence: tuple[EvidenceRef, ...]) -> Protocol:
        if not evidence:
            raise ValueError("revocation requires EvidenceRef provenance")
        current = self.latest_protocol(protocol_id)
        if current is None or current.status not in {"active", "contested"}:
            raise ValueError(f"only active or contested protocols can be revoked: {protocol_id}")
        revoked = current.with_status(
            "revoked",
            provenance=current.provenance + tuple(evidence),
            version=current.version + 1,
        )
        self.save_protocol(revoked)
        return revoked
