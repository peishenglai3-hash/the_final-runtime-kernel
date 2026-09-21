# Changelog

## [0.1.0] - 2026-09-21

### Added

- Frozen V1.0 domain contracts for NodeRef, Event, Relation, EvidenceRef, and Protocol.
- One append-only JSONL Store with replayable history and protocol version revocation.
- Derived GraphView and deterministic Detect, Attribute, Route, Compile, and Validate operators.
- One Coding Adapter, a small JSON CLI, four labeled replay fixtures, and a standard-library test suite.
- MIT licensing, architecture traceability, theory limits, failure register, and future-direction boundary.

### Verification

- Local unit and replay suite: 12 tests passed.
- Real-world empirical validation remains pending because no human-approved trace corpus was supplied with the implementation task.
