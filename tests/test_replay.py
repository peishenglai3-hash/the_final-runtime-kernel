from pathlib import Path
import json
import tempfile
import unittest

from tfrk.adapters import CodingAdapter
from tfrk.kernel import Kernel
from tfrk.model import EvidenceRef
from tfrk.projection import project
from tfrk.store import JsonlStore


CASES = Path(__file__).parent / "cases"


class ReplayTests(unittest.TestCase):
    def test_end_to_end_replay_rebuilds_projection_and_preserves_revoke(self) -> None:
        raw = json.loads((CASES / "case_a_technical_path.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            first_store = JsonlStore(path)
            first_kernel = Kernel(CodingAdapter(), first_store)
            first_result = first_kernel.process(raw)[0]
            first_view = project(first_store.list_history())
            protocol_id = first_result["protocol"]["id"]

            second_store = JsonlStore(path)
            second_view = project(second_store.list_history())
            self.assertEqual(first_view.to_dict(), second_view.to_dict())
            self.assertEqual(second_store.list_active_protocols()[0].id, protocol_id)

            second_kernel = Kernel(CodingAdapter(), second_store)
            revoked = second_kernel.revoke(
                protocol_id,
                (EvidenceRef("replay-test", "test_result", "revoke:case-a"),),
            )
            self.assertEqual(revoked["status"], "revoked")
            self.assertEqual(second_store.list_active_protocols(), ())
            self.assertEqual(len(second_store.protocol_history()), 2)


if __name__ == "__main__":
    unittest.main()
