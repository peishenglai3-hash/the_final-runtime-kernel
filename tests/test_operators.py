from pathlib import Path
import json
import unittest

from tfrk.adapters import CodingAdapter
from tfrk.model import NodeRef, Relation
from tfrk.operators import Budget, OperatorSet
from tfrk.projection import project


CASES = Path(__file__).parent / "cases"


class OperatorTests(unittest.TestCase):
    def test_case_a_uses_deterministic_five_operator_contract(self) -> None:
        raw = json.loads((CASES / "case_a_technical_path.json").read_text(encoding="utf-8"))
        event = CodingAdapter().normalize(raw)[0]
        ops = OperatorSet()
        friction = ops.detect(event, project([event]), ())
        attribution = ops.attribute(friction, project([event]), event)
        route = ops.route(friction, attribution, Budget(risk=0.8))
        candidate = ops.compile(friction, attribution, event, ())
        validation = ops.validate(candidate, context=event.context)
        self.assertTrue(friction.present)
        self.assertEqual(friction.type, "execution")
        self.assertEqual(route.route, "verify")
        self.assertEqual(validation.status, "Valid")

    def test_reasoner_is_a_replaceable_callable_not_a_provider_manager(self) -> None:
        def reasoner(payload: dict) -> dict:
            self.assertEqual(payload["friction"]["type"], "execution")
            return {"action": {"kind": "reasoned-repair"}, "confidence": 0.9}

        raw = json.loads((CASES / "case_a_technical_path.json").read_text(encoding="utf-8"))
        event = CodingAdapter().normalize(raw)[0]
        ops = OperatorSet(reasoner=reasoner)
        friction = ops.detect(event, project([event]), ())
        attribution = ops.attribute(friction, project([event]), event)
        candidate = ops.compile(friction, attribution, event, ())
        self.assertEqual(candidate.action["kind"], "reasoned-repair")
        self.assertEqual(candidate.confidence, 0.9)

    def test_attribution_uses_node_kind_with_node_id(self) -> None:
        raw = json.loads((CASES / "case_a_technical_path.json").read_text(encoding="utf-8"))
        event = CodingAdapter().normalize(raw)[0]
        colliding_relation = Relation(
            id="relation:kind-collision",
            source=NodeRef("developer", "tool"),
            target=NodeRef("unrelated", "tool"),
            kind="unrelated",
        )
        graph = project([event, colliding_relation])
        ops = OperatorSet()
        friction = ops.detect(event, graph, ())
        attribution = ops.attribute(friction, graph, event)
        self.assertNotIn("relation:kind-collision", attribution.relations)


if __name__ == "__main__":
    unittest.main()
