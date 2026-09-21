from datetime import datetime, timezone
import unittest

from tfrk.model import Event, EvidenceRef, NodeRef, Protocol, Relation


class ModelRoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.when = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)
        self.actor = NodeRef("actor", "human", "Actor")
        self.target = NodeRef("target", "tool", "Tool")
        self.evidence = EvidenceRef("fixture", "test_result", "case:1", "digest")

    def test_frozen_models_round_trip(self) -> None:
        event = Event(
            id="event:1",
            actor=self.actor,
            action="run",
            target=self.target,
            context={"path": "C:/repo"},
            expected="ok",
            observed="mismatch",
            evidence=(self.evidence,),
            timestamp=self.when,
        )
        relation = Relation(
            id="relation:1",
            source=self.actor,
            target=self.target,
            kind="depends_on",
            attributes={"direction": "forward"},
            provenance=(self.evidence,),
        )
        protocol = Protocol(
            id="protocol:1",
            trigger={"event_id": event.id},
            action={"kind": "repair"},
            scope={"environment": "test"},
            required_evidence=("case:1",),
            validation={"status": "external"},
            veto_conditions=({"kind": "gate"},),
            provenance=(self.evidence,),
            status="candidate",
            version=1,
            confidence=0.8,
        )

        self.assertEqual(Event.from_dict(event.to_dict()), event)
        self.assertEqual(Relation.from_dict(relation.to_dict()), relation)
        self.assertEqual(Protocol.from_dict(protocol.to_dict()), protocol)

    def test_naive_datetime_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Event("event:naive", self.actor, "run", "x", datetime.now())


if __name__ == "__main__":
    unittest.main()
