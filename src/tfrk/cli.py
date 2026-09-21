"""Small JSON CLI; it exposes the kernel without adding a workflow engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters import CodingAdapter
from .kernel import Kernel
from .model import EvidenceRef
from .store import JsonlStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tfrk")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="normalize and process a coding trace")
    run.add_argument("input", help="JSON file path or - for stdin")
    run.add_argument("--store", required=True, help="append-only JSONL store path")

    revoke = subparsers.add_parser("revoke", help="revoke the latest active protocol version")
    revoke.add_argument("protocol_id")
    revoke.add_argument("--store", required=True)
    revoke.add_argument("--source", required=True)
    revoke.add_argument("--kind", required=True)
    revoke.add_argument("--locator", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    store = JsonlStore(args.store)
    kernel = Kernel(CodingAdapter(), store)
    if args.command == "run":
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        print(json.dumps(kernel.process(raw), ensure_ascii=False, indent=2))
        return 0
    evidence = (EvidenceRef(args.source, args.kind, args.locator),)
    print(json.dumps(kernel.revoke(args.protocol_id, evidence), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
