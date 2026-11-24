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

### Event provenance was able to self-confirm a protocol

- Observed: the first validator implementation treated candidate provenance and the event ID as sufficient validation evidence.
- Consequence: a protocol could become `active` without a distinct validation result or validator record.
- Correction: `Validate` now accepts only explicit `context.validation_evidence`; `JsonlStore.save_protocol` requires `Valid`, a validator, and validation evidence for active protocols.
- Remaining gate: deterministic fixture validation is structural evidence, not real-world external validation.

### Ambiguous node and relation identities

- Observed: attribution compared node IDs without node kinds, and projection silently overwrote duplicate relation IDs.
- Consequence: unrelated nodes could inherit a relation, or replay could hide conflicting history.
- Correction: attribution keys nodes by `(kind, id)` and projection rejects duplicate relation IDs. Regression tests cover both cases.

### Batch processing repeatedly rescanned history

- Observed: each event rebuilt the projection and active-protocol index from the full store.
- Consequence: larger replay batches accumulated avoidable repeated scans.
- Correction: the Store caches its append-only records and the Kernel advances one ephemeral projection accumulator and protocol tuple through a batch.

### Repeated Kernel calls replayed unchanged history

- Observed: a new `Kernel.process` call rebuilt the graph projection from the complete history even when the same Kernel and Store had already processed that history.
- Consequence: repeated short calls paid a full-history replay cost despite the existing append-only Store cache.
- Correction: the Kernel now retains one ephemeral projection, advances it after its own appends, and rebuilds after the Store history revision changes or `reload()` invalidates the view. The JSONL file remains the only authority.
- Remaining gate: this is a deterministic local optimization; no production workload or real trace latency claim is made.
