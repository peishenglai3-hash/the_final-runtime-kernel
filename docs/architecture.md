# TFRK V1.0 Architecture

Status: frozen implementation slice

This document translates the supplied *The Final Runtime Kernel Engineering Bible V1.0* into a small, inspectable repository. The Bible is the source baseline; this file records the implementation mapping and does not replace it.

## Boundary

The only V1.0 production path is:

`RawTrace -> CodingAdapter -> Event -> JsonlStore history -> GraphView -> Detect -> Attribute -> Route -> Compile -> Validate -> Commit / Reject / Revoke`

The project deliberately has one local Store, one Coding Adapter, five operator methods, and a fixed Kernel loop. `GraphView` is derived from history and is never a second current-state authority.

This repository is standalone and does not import code, schemas, migrations, or fixtures from another runtime. Any prior engineering experience is treated only as a planning lesson: preserve phase gates, evidence, reversibility, and explicit mismatch reporting.

## Module map

| Responsibility | Implementation | Evidence |
|---|---|---|
| NodeRef, Event, Relation, EvidenceRef, Protocol | `src/tfrk/model.py` | `tests/test_model.py` |
| Single replayable history and protocol versions | `src/tfrk/store.py` | `tests/test_store_projection.py`, `tests/test_replay.py` |
| Derived relation projection | `src/tfrk/projection.py` | `tests/test_store_projection.py`, Case B |
| Read-only weak-score exploration | `src/tfrk/exploration.py`, `src/tfrk/cli.py` | `tests/test_exploration.py` |
| Detect, Attribute, Route, Compile, Validate | `src/tfrk/operators.py` | `tests/test_operators.py` |
| Fixed orchestration loop | `src/tfrk/kernel.py` | `tests/test_kernel_cases.py`, `tests/test_replay.py` |
| Coding trace normalization | `src/tfrk/adapters/coding.py` | Case A-D fixtures |
| JSON CLI seam | `src/tfrk/cli.py` | manual CLI smoke |

Dependency direction is one-way: model is foundational; Store and Projection consume model; Operators consume model and Projection; Kernel composes them; the Adapter and CLI remain seams. There is no package-level cycle and no ProviderManager or Workflow Engine.

## Requirements traceability

| Bible requirement | Local acceptance | Status |
|---|---|---|
| Frozen five-structure domain model | Dataclass round trips and validation | PASS |
| Single historical source of truth | JSONL append-only history; projection is ephemeral and revision-invalidated | PASS |
| Relation-first projection | GraphView derives nodes and relations | PASS |
| Five replaceable operators | Deterministic operators plus callable Reasoner seam | PASS |
| External veto cannot be self-overridden | Case B returns `Invalid` and no active protocol | PASS |
| Event provenance cannot self-validate | Case A without `context.validation_evidence` remains pending | PASS |
| Negative transfer is rejected | Case D returns `NotApplicable` | PASS |
| Non-code semantic friction is supported | Case C commits a semantic protocol | PASS |
| Full protocol lifecycle is reversible | Active version is retained when a new revoked version is appended | PASS |
| Four benchmark classes | Explicit A-D metadata, replay fixtures, and kernel tests | STRUCTURAL PASS |
| Real trace evidence | No source trace was supplied with this task | PENDING HUMAN INPUT |

The four fixtures are explicitly replayable test data. They are not presented as real-world evidence and do not close the final empirical gate by themselves.

## Complexity budget check

- Core runtime modules: `model`, `store`, `projection`, `operators`, `kernel`, `adapters/coding` — six responsibility areas.
- Persistence backend: one JSONL implementation.
- Adapter: one Coding Adapter.
- Provider seam: one optional `StructuredReasoner` callable.
- No database, ORM, graph database, plugin loader, multi-agent orchestrator, Web UI, or research-metric dependency.
- Projection acceleration: each Kernel keeps one ephemeral accumulator, advances it for its own appended events, and rebuilds it when the Store history revision changes or `reload()` is called. It is never persisted as a second source of truth.
- Advisory exploration is an optional read-only query over existing scored Relations. It does not join the fixed Kernel loop or mutate history.

## Frozen decisions

The repository keeps the Bible's ADR direction: Relation-first; GraphView as projection; friction as `DetectResult`; authority as relation data; scope plus validation instead of Transfer; semantic placeholders without V1.0 classes; one Adapter and one Store; research metrics outside the Runtime.
