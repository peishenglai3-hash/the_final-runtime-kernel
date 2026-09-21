"""The single V1.0 Coding Adapter."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from ..model import Event, EvidenceRef, NodeRef, datetime_from_json


class CodingAdapter:
    """Normalize a coding trace while keeping coding fields in Event.context."""

    def normalize(self, raw_input: Any) -> list[Event]:
        if isinstance(raw_input, str):
            raw_input = json.loads(raw_input)
        if isinstance(raw_input, dict) and "events" in raw_input:
            raw_events = raw_input["events"]
        else:
            raw_events = [raw_input]
        if not isinstance(raw_events, list):
            raise TypeError("coding trace events must be a list")
        return [self._event(item) for item in raw_events]

    def _event(self, raw: Any) -> Event:
        if not isinstance(raw, dict):
            raise TypeError("each coding trace event must be an object")
        timestamp = raw.get("timestamp")
        if isinstance(timestamp, datetime):
            parsed_timestamp = timestamp
        elif isinstance(timestamp, str):
            parsed_timestamp = datetime_from_json(timestamp)
        else:
            raise ValueError("coding trace event requires a timezone-aware timestamp")
        return Event(
            id=str(raw["id"]),
            actor=self._node(raw["actor"]),
            action=str(raw["action"]),
            target=self._node(raw["target"]) if raw.get("target") else None,
            context=dict(raw.get("context", {})),
            expected=raw.get("expected"),
            observed=raw.get("observed"),
            evidence=tuple(
                EvidenceRef(
                    source=str(item["source"]),
                    kind=str(item["kind"]),
                    locator=str(item["locator"]),
                    digest=item.get("digest"),
                )
                for item in raw.get("evidence", [])
            ),
            timestamp=parsed_timestamp,
        )

    @staticmethod
    def _node(raw: Any) -> NodeRef:
        if not isinstance(raw, dict):
            raise TypeError("coding trace node must be an object")
        return NodeRef(id=str(raw["id"]), kind=str(raw["kind"]), label=raw.get("label"))
