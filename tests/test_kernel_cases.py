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
            graph = project(kernel.store.list_history())
            relation_kinds = [relation.kind for relation in graph.relations]
            relation_ids = [relation.id for relation in graph.relations]
            return results, active_count, relation_kinds, relation_ids

    def test_case_a_commits_validated_protocol(self) -> None:
        results, active_count, _, _ = self.run_case("case_a_technical_path.json")
        self.assertEqual(results[0]["outcome"], "committed")
        self.assertEqual(results[0]["validation"]["status"], "Valid")
        self.assertEqual(active_count, 1)

    def test_case_b_external_veto_cannot_be_overridden(self) -> None:
        results, active_count, relation_kinds, _ = self.run_case("case_b_external_veto.json")
        self.assertEqual(results[0]["outcome"], "rejected")
        self.assertEqual(results[0]["validation"]["status"], "Invalid")
        self.assertEqual(active_count, 0)
        self.assertEqual(relation_kinds, ["vetoes"])

    def test_case_c_handles_non_code_semantic_friction(self) -> None:
        results, _, _, _ = self.run_case("case_c_institutional_translation.json")
        self.assertEqual(results[0]["friction"]["type"], "semantic")
        self.assertEqual(results[0]["outcome"], "committed")

    def test_case_d_rejects_negative_transfer_as_not_applicable(self) -> None:
        results, active_count, _, _ = self.run_case("case_d_negative_transfer.json")
        self.assertEqual(results[0]["validation"]["status"], "NotApplicable")
        self.assertEqual(results[0]["outcome"], "rejected")
        self.assertEqual(active_count, 0)

    def test_benchmark_metadata_matches_replay_outcomes(self) -> None:
        for name in (
            "case_a_technical_path.json",
            "case_b_external_veto.json",
            "case_c_institutional_translation.json",
            "case_d_negative_transfer.json",
        ):
            raw = load_case(name)
            benchmark = raw["benchmark"]
            self.assertIn(benchmark["class"], {"A", "B", "C", "D"})
            self.assertIsInstance(benchmark["unacceptable_protocols"], list)
            results, _, _, relation_ids = self.run_case(name)
            self.assertEqual(results[0]["outcome"], benchmark["expected_outcome"])
            self.assertEqual(results[0]["validation"]["status"], benchmark["expected_validation"])
            self.assertEqual(relation_ids, benchmark["expected_relation_ids"])
            expected_protocol = benchmark["acceptable_protocol"]
            if expected_protocol is None:
                self.assertNotIn("protocol", results[0])
            else:
                protocol = results[0]["protocol"]
                self.assertEqual(protocol["status"], expected_protocol["status"])
                self.assertEqual(protocol["action"]["kind"], expected_protocol["action_kind"])
                self.assertEqual(protocol["scope"]["environment"], expected_protocol["scope_environment"])

    def test_event_provenance_cannot_self_validate_a_protocol(self) -> None:
        raw = load_case("case_a_technical_path.json")
        raw["id"] = "case-a-without-validator"
        raw["context"].pop("validation_evidence")
        with tempfile.TemporaryDirectory() as directory:
            kernel = Kernel(CodingAdapter(), JsonlStore(Path(directory) / "history.jsonl"))
            result = kernel.process(raw)[0]
            active_count = len(kernel.store.list_active_protocols())
        self.assertEqual(result["validation"]["status"], "InsufficientEvidence")
        self.assertEqual(result["outcome"], "pending")
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
