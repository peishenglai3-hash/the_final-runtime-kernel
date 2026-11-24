from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import math
import tempfile
import unittest

from tfrk.cli import main
from tfrk.exploration import explore_low_score_relations
from tfrk.model import EvidenceRef, NodeRef, Relation
from tfrk.store import JsonlStore


def make_relation(relation_id: str, score: object = None, *, evidence: bool = True) -> Relation:
    attributes = {} if score is None else {"score": score}
    provenance = (
        (EvidenceRef("fixture", "observation", f"evidence:{relation_id}"),)
        if evidence
        else ()
    )
    return Relation(
        id=relation_id,
        source=NodeRef(f"source:{relation_id}", "concept"),
        target=NodeRef(f"target:{relation_id}", "case"),
        kind="relates_to",
        attributes=attributes,
        provenance=provenance,
    )


class ExplorationTests(unittest.TestCase):
    def test_nonzero_evidence_bearing_candidates_are_stable_and_capped(self) -> None:
        relations = [
            make_relation("weak:middle", 0.2),
            make_relation("weak:zeta", 0.39),
            make_relation("weak:alpha", 0.39),
            make_relation("excluded:zero", 0.0),
            make_relation("excluded:cutoff", 0.4),
            make_relation("excluded:missing-score"),
            make_relation("excluded:no-evidence", 0.2, evidence=False),
            make_relation("excluded:high", 0.8),
            make_relation("excluded:non-finite", math.nan),
            make_relation("excluded:boolean", True),
        ]

        first = explore_low_score_relations(relations)
        second = explore_low_score_relations(relations)

        self.assertEqual(
            [item.relation.id for item in first],
            ["weak:alpha", "weak:zeta", "weak:middle"],
        )
        self.assertEqual([item.to_dict() for item in first], [item.to_dict() for item in second])
        self.assertTrue(all(item.to_dict()["activation"] is False for item in first))
        self.assertEqual(first[0].to_dict()["evidence"][0]["locator"], "evidence:weak:alpha")
        self.assertIn("below ordinary cutoff 0.4", first[0].to_dict()["explanation"])

    def test_limits_and_cutoff_are_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "from 1 to 3"):
            explore_low_score_relations([], limit=4)
        with self.assertRaisesRegex(ValueError, r"in \(0, 1\]"):
            explore_low_score_relations([], max_score=0.0)
        with self.assertRaisesRegex(TypeError, "finite number"):
            explore_low_score_relations([], max_score=True)

    def test_cli_exploration_is_read_only_and_keeps_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            store = JsonlStore(path)
            store.append_relation(make_relation("weak:cli", 0.25))
            before = path.read_bytes()
            stdout = StringIO()

            with redirect_stdout(stdout):
                status = main(["explore", "--store", str(path)])

            output = json.loads(stdout.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(output["mode"], "advisory")
            self.assertFalse(output["activation"])
            self.assertEqual(
                output["candidates"][0]["evidence"][0]["locator"],
                "evidence:weak:cli",
            )


if __name__ == "__main__":
    unittest.main()
