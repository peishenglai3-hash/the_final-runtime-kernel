from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from tfrk.model import Event, EvidenceRef, NodeRef, Relation
from tfrk.projection import project
from tfrk.store import JsonlStore


class StoreProjectionTests(unittest.TestCase):
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
        from tfrk.model import Protocol

        with tempfile.TemporaryDirectory() as directory:
            store = JsonlStore(Path(directory) / "history.jsonl")
            evidence = EvidenceRef("test", "test_result", "protocol:1")
            protocol = Protocol(
                id="protocol:1",
                trigger={},
                action={},
                scope={},
                required_evidence=("protocol:1",),
                validation={},
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


if __name__ == "__main__":
    unittest.main()
