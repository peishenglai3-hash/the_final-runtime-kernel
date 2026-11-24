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
        self._record_cache: list[dict[str, Any]] | None = None
        self._event_ids: set[str] = set()
        self._relation_ids: set[str] = set()
        self._latest_protocols: dict[str, Protocol] = {}
        self._history_revision = 0

    @property
    def history_revision(self) -> int:
        """Revision for ephemeral history projections owned by this Store instance."""

        return self._history_revision

    def _load_cache(self) -> list[dict[str, Any]]:
        if self._record_cache is not None:
            return self._record_cache
        records: list[dict[str, Any]] = []
        if self.path.exists():
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
                    records.append(record)
        self._record_cache = records
        for record in records:
            self._index(record)
        return records

    def _index(self, record: dict[str, Any]) -> None:
        kind = record.get("kind")
        payload = record["payload"]
        if kind == "event":
            self._event_ids.add(str(payload["id"]))
        elif kind == "relation":
            self._relation_ids.add(str(payload["id"]))
        elif kind == "protocol":
            protocol = Protocol.from_dict(payload)
            previous = self._latest_protocols.get(protocol.id)
            if previous is None or protocol.version > previous.version:
                self._latest_protocols[protocol.id] = protocol

    def _append(self, kind: str, payload: dict[str, Any]) -> None:
        records = self._load_cache()
        record = {"kind": kind, "payload": payload}
        line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        records.append(record)
        self._index(record)
        if kind in {"event", "relation"}:
            self._history_revision += 1

    def _records(self) -> Iterator[dict[str, Any]]:
        return iter(self._load_cache())

    def reload(self) -> None:
        """Reload after an external writer changes the append-only file."""
        self._record_cache = None
        self._event_ids.clear()
        self._relation_ids.clear()
        self._latest_protocols.clear()
        self._history_revision += 1

    def append_event(self, event: Event) -> None:
        self._load_cache()
        if event.id in self._event_ids:
            raise ValueError(f"event already exists: {event.id}")
        self._append("event", event.to_dict())

    def append_relation(self, relation: Relation) -> None:
        self._load_cache()
        if relation.id in self._relation_ids:
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
        if protocol.status == "active":
            if not protocol.provenance:
                raise ValueError("active protocol requires provenance")
            if protocol.validation.get("result") != "Valid":
                raise ValueError("active protocol requires a Valid validation result")
            validator = protocol.validation.get("validator")
            if not isinstance(validator, str) or not validator.strip():
                raise ValueError("active protocol requires validator provenance")
            validation_evidence = protocol.validation.get("evidence")
            if not isinstance(validation_evidence, list) or not validation_evidence:
                raise ValueError("active protocol requires validation evidence")
        self._append("protocol", protocol.to_dict())

    def protocol_history(self) -> tuple[Protocol, ...]:
        return tuple(
            Protocol.from_dict(record["payload"])
            for record in self._records()
            if record.get("kind") == "protocol"
        )

    def latest_protocol(self, protocol_id: str) -> Protocol | None:
        self._load_cache()
        return self._latest_protocols.get(protocol_id)

    def list_active_protocols(self) -> tuple[Protocol, ...]:
        self._load_cache()
        return tuple(
            sorted(
                (protocol for protocol in self._latest_protocols.values() if protocol.status == "active"),
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
