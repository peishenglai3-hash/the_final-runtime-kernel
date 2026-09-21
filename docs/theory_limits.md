# Theory Limits

This repository is an engineering implementation of a bounded V1.0 protocol. It is not a claim that the runtime implements AGI socialization, general reflection, trust, negotiation, or a complete social theory.

## Source status

- Source-grounded: the user-supplied *The Final Runtime Kernel Engineering Bible V1.0* and its explicit V1.0 boundaries.
- Engineering proposal: the Python dataclasses, JSONL representation, deterministic thresholds, and CLI in this repository.
- Evaluation evidence: unit tests, replay tests, explicit A-D benchmark metadata, and the four labeled fixtures.
- Not yet supplied: a user-approved corpus of real failure traces and external validation records.

The code must not turn a smooth explanation into authorial proof. It records events, relations, evidence references, scope, validation, and revocation so that a later human can disagree with a protocol and preserve the disagreement.

## Deliberately deferred

Norm, Obligation, Trust, Negotiation, learned routing, graph learning, independent Transfer, multi-agent relational dynamics, multiple stores, plugin discovery, and Web UI remain semantic or research placeholders. Adding a class for any of them would change the V1.0 boundary and requires a new decision record.

## What the tests do and do not show

The tests show that the local contracts are serializable, replayable, replaceable, and able to reject an external veto or a scope mismatch. They also show that event provenance alone cannot make a protocol active: a distinct validator record and validation evidence are required. They do not show that any generated protocol is valid for an actual institution, repository, team, or production environment. That claim requires human-approved traces and evidence outside this repository.
