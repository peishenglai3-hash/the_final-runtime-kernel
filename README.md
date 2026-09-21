# The Final Runtime Kernel

The Final Runtime Kernel (TFRK) is a small Python runtime for turning a replayable failure trace into an evidence-bounded, scope-aware, revocable protocol. Version 0.1.0 implements the V1.0 engineering slice described by the supplied *The Final Runtime Kernel Engineering Bible V1.0*.

It is deliberately not a general Agent platform. The central question is narrower: can a real or replayable failure be represented as an Event, related to a small derived GraphView, attributed as friction, routed under an explicit budget, compiled into a structured Protocol, validated against evidence and scope, and committed, rejected, or revoked without erasing history?

## V1.0 path

`RawTrace -> CodingAdapter -> Event -> History -> GraphView -> Detect -> Attribute -> Route -> Compile -> Validate -> Commit / Reject / Revoke`

The JSONL history is the only persisted source of truth. GraphView is derived. Protocol versions are appended rather than overwritten. An external veto is a binding validation result, not something the runtime may explain away.

## Install

TFRK requires Python 3.12 or newer and has no runtime dependency outside the standard library.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

For a source checkout without installation:

```powershell
$env:PYTHONPATH = "src"
```

## Test and replay the cases

```powershell
python -m unittest discover -s tests -v
tfrk run tests/cases/case_a_technical_path.json --store .local\case-a.jsonl
tfrk run tests/cases/case_b_external_veto.json --store .local\case-b.jsonl
tfrk revoke protocol:case-a-path-mismatch:execution `
  --store .local\case-a.jsonl `
  --source human-review --kind human_confirmation --locator review:case-a
```

Cases A-D are deterministic replay fixtures for the four Bible benchmark classes. They are explicitly not supplied real-world traces and must not be advertised as empirical evidence until a human-approved trace corpus and external validation are added.

## Minimal API

```python
from pathlib import Path

from tfrk import CodingAdapter, JsonlStore, Kernel

kernel = Kernel(
    adapter=CodingAdapter(),
    store=JsonlStore(Path(".local/history.jsonl")),
)
results = kernel.process({
    "id": "event-1",
    "actor": {"id": "developer", "kind": "human"},
    "action": "open-path",
    "expected": "C:/repo",
    "observed": "/workspace",
    "context": {"environment": "windows"},
    "evidence": [{
        "source": "trace",
        "kind": "test_result",
        "locator": "trace:event-1",
    }],
    "timestamp": "2026-09-20T10:00:00Z",
})
```

To replace the deterministic Reasoner seam, pass one callable to `OperatorSet(reasoner=...)`. The callable receives structured input and returns a dictionary containing only the proposal fields it needs to change. There is no ProviderManager, credential layer, or custom retry framework.

## Repository map

```text
src/tfrk/
  model.py                 frozen domain contracts and JSON conversion
  store.py                 one append-only JSONL Store
  projection.py            history -> GraphView
  operators.py             Detect / Attribute / Route / Compile / Validate
  kernel.py                fixed explicit runtime loop
  adapters/coding.py       one Coding Adapter
  cli.py                   small JSON CLI
tests/
  cases/                   labeled replay fixtures A-D
schemas/domain.v1.schema.json
docs/                     architecture, failure, limits, future boundary
```

## Scope and non-goals

V1.0 does not build a multi-Agent orchestrator, plugin system, Workflow Engine, Web UI, database abstraction, ORM, graph database layer, vector database, independent Transfer operator, learned router, GNN, Norm/Obligation/Trust/Negotiation classes, or research-metric dependency. These are either explicitly removed or deferred by the Bible.

## Source, authorship, and open development

The repository keeps three layers separate: the user-supplied Bible is the source baseline; the Python implementation is an engineering proposal; tests and external review are evaluation evidence. The `lai-peisheng` integration and `laipeisheng-doctor` boundary are used here as authorship safeguards: source restoration and organization do not become an invented author quote, a fluent analogy does not become a settled theory, and the major conceptual jump remains open to human revision. The implementation side follows the corresponding engineering discipline of explicit scope, provenance, reversibility, and a human release gate.

MIT licensing permits use, modification, forking, and redistribution. That openness does not remove provenance, security, labor, or responsibility. A public release should therefore keep the source boundary, test evidence, unresolved gaps, and rollback history visible.

## Verification status

The current local acceptance packet covers JSON round trips, append-only history, projection rebuild, all five operator contracts, Cases A-D, external veto rejection, negative-transfer rejection, and protocol revocation. The remaining empirical gate is human-approved real traces and external validation; see [`docs/theory_limits.md`](docs/theory_limits.md) and [`docs/failure_cases.md`](docs/failure_cases.md).

## License

MIT. See [`LICENSE`](LICENSE).
