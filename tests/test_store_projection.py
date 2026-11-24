from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from tfrk.model import Event, EvidenceRef, NodeRef, Protocol, Relation
from tfrk.projection import project
from tfrk.store import JsonlStore


class StoreProjectionTests(unittest.TestCase):
    def test_decision_record_is_not_duplicated_when_store_cache_is_cold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JsonlStore(Path(directory) / "history.jsonl")
            candidate = Protocol(
                id="protocol:pending",
                trigger={},
                action={},
                scope={},
                required_evidence=("event:1",),
                validation={},
                veto_conditions=(),
                provenance=(),
                status="candidate",
                version=1,
            )
            store.record_pending(candidate, {"status": "InsufficientEvidence"})
            self.assertEqual(len(store.decision_history()), 1)
            store.reload()
            self.assertEqual(len(store.decision_history()), 1)

    def test_history_rebuilds_the_same_graph_view(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JsonlStore(Path(directory) / "history.jsonl")
            actor = NodeRef("actor", "human")
            tool = NodeRef("tool", "tool")
            evidence = EvidenceRef("test", "test_result", "store:1")
            store.append_event(
                Event(
                    id="event:1",
                    actor=actor,
                    action="invoke",
                    target=tool,
                    observed="done",
                    timestamp=datetime(2026, 9, 20, tzinfo=timezone.utc),
                    evidence=(evidence,),
                )
            )
            store.append_relation(Relation("relation:1", actor, tool, "produces", provenance=(evidence,)))
            first = project(store.list_history())
            second = project(store.list_history())
            self.assertEqual(first, second)
            self.assertEqual([node.id for node in first.nodes], ["actor", "tool"])
            self.assertEqual([relation.id for relation in first.relations], ["relation:1"])

    def test_protocol_revocation_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JsonlStore(Path(directory) / "history.jsonl")
            evidence = EvidenceRef("test", "test_result", "protocol:1")
            protocol = Protocol(
                id="protocol:1",
                trigger={},
                action={},
                scope={},
                required_evidence=("protocol:1",),
                validation={
                    "result": "Valid",
                    "validator": "unit-test-validator-v1",
                    "evidence": [evidence.to_dict()],
                },
                veto_conditions=(),
                provenance=(evidence,),
                status="active",
                version=1,
            )
            store.save_protocol(protocol)
            revoked = store.revoke_protocol("protocol:1", (EvidenceRef("test", "external", "revoke:1"),))
            self.assertEqual(revoked.status, "revoked")
            self.assertEqual(len(store.protocol_history()), 2)
            self.assertEqual(store.list_active_protocols(), ())

    def test_active_protocol_requires_validation_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JsonlStore(Path(directory) / "history.jsonl")
            evidence = EvidenceRef("test", "test_result", "protocol:invalid")
            protocol = Protocol(
                id="protocol:invalid",
                trigger={},
                action={},
                scope={},
                required_evidence=("protocol:invalid",),
                validation={},
                veto_conditions=(),
                provenance=(evidence,),
                status="active",
                version=1,
            )
            with self.assertRaisesRegex(ValueError, "Valid validation result"):
                store.save_protocol(protocol)

    def test_projection_rejects_duplicate_relation_ids(self) -> None:
        actor = NodeRef("actor", "human")
        target = NodeRef("target", "tool")
        first = Relation("relation:duplicate", actor, target, "depends_on")
        second = Relation("relation:duplicate", target, actor, "vetoes")
        with self.assertRaisesRegex(ValueError, "duplicate relation id"):
            project([first, second])


if __name__ == "__main__":
    unittest.main()
