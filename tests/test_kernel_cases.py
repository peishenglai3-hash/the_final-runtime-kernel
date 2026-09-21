from pathlib import Path
import json
import tempfile
import unittest

from tfrk.adapters import CodingAdapter
from tfrk.kernel import Kernel
from tfrk.projection import project
from tfrk.store import JsonlStore


CASES = Path(__file__).parent / "cases"


def load_case(name: str) -> dict:
    return json.loads((CASES / name).read_text(encoding="utf-8"))


class KernelCaseTests(unittest.TestCase):
    def run_case(self, name: str):
        with tempfile.TemporaryDirectory() as directory:
            kernel = Kernel(CodingAdapter(), JsonlStore(Path(directory) / "history.jsonl"))
            results = kernel.process(load_case(name))
            active_count = len(kernel.store.list_active_protocols())
            relation_kinds = [relation.kind for relation in project(kernel.store.list_history()).relations]
            return results, active_count, relation_kinds

    def test_case_a_commits_validated_protocol(self) -> None:
        results, active_count, _ = self.run_case("case_a_technical_path.json")
        self.assertEqual(results[0]["outcome"], "committed")
        self.assertEqual(results[0]["validation"]["status"], "Valid")
        self.assertEqual(active_count, 1)

    def test_case_b_external_veto_cannot_be_overridden(self) -> None:
        results, active_count, relation_kinds = self.run_case("case_b_external_veto.json")
        self.assertEqual(results[0]["outcome"], "rejected")
        self.assertEqual(results[0]["validation"]["status"], "Invalid")
        self.assertEqual(active_count, 0)
        self.assertEqual(relation_kinds, ["vetoes"])

    def test_case_c_handles_non_code_semantic_friction(self) -> None:
        results, _, _ = self.run_case("case_c_institutional_translation.json")
        self.assertEqual(results[0]["friction"]["type"], "semantic")
        self.assertEqual(results[0]["outcome"], "committed")

    def test_case_d_rejects_negative_transfer_as_not_applicable(self) -> None:
        results, active_count, _ = self.run_case("case_d_negative_transfer.json")
        self.assertEqual(results[0]["validation"]["status"], "NotApplicable")
        self.assertEqual(results[0]["outcome"], "rejected")
        self.assertEqual(active_count, 0)

    def test_matching_event_can_pass_without_objectification(self) -> None:
        raw = load_case("case_a_technical_path.json")
        raw["id"] = "case-no-friction"
        raw["expected"] = raw["observed"]
        raw["evidence"][0]["locator"] = "trace:no-friction"
        with tempfile.TemporaryDirectory() as directory:
            kernel = Kernel(CodingAdapter(), JsonlStore(Path(directory) / "history.jsonl"))
            result = kernel.process(raw)[0]
        self.assertEqual(result["outcome"], "no-op")
        self.assertFalse(result["friction"]["present"])


if __name__ == "__main__":
    unittest.main()
