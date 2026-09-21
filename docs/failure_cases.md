# Failure Cases and Mismatch Register

This file records implementation-level failures and evidence gaps. It is intentionally short; a new entry should name the observed trace, the violated contract, the correction, and the remaining gate.

## Open evidence gap

### Real trace corpus not supplied

- Observed: the Bible requires real or replayable real cases for the strongest V1.0 claim, but this task supplied no trace corpus beyond the engineering Bible.
- Current treatment: four deterministic fixtures are labeled `fixture:*` and are used only for structural and replay tests.
- Consequence: the repository can demonstrate the closure mechanically, but cannot claim empirical validity for a real project or institution.
- Resolution gate: add human-approved traces and external evidence without rewriting fixture provenance.

## Resolved during implementation

### Store test read after temporary directory cleanup

- Observed: the first test helper returned a Store after its temporary directory had already been deleted.
- Consequence: a committed protocol appeared absent even though the kernel had written it.
- Correction: assertions now read the Store before the temporary directory exits; the production Store remained unchanged.
- Lesson: filesystem lifetime is part of replay evidence, not a cosmetic test detail.

### Derived relation mistaken for a second Relation Store

- Observed: Case B carries a relation declaration in Event context so the Coding Adapter can still return `list[Event]`; the projection derives it into GraphView.
- Consequence: asserting it as a separately persisted relation would violate the single-history rule.
- Correction: tests assert the derived GraphView relation, while the JSONL file keeps the Event as the source record.
