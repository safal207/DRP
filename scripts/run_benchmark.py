#!/usr/bin/env python3
"""
Walk the DRP auditability benchmark pack and summarize validator
outcomes per category.

Categories and expectations:
  - valid/       -> every batch must validate.
  - invalid/     -> every batch must fail validation.
  - ambiguous/   -> every batch is structurally valid (the validator is
                    expected to accept it); these fixtures exist to
                    illustrate audit-hostile shapes that structural
                    validation does not catch.
  - comparison/  -> the structured_*.json chain(s) must validate; the
                    Markdown notes in this directory are ignored.

This script wraps the public reference validator
(tools/drp_validator.validate_file). It does not alter the protocol,
the schema, or the validator. Exit code is 0 if every category matched
its expectation, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass


_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "tools"))

from drp_validator import validate_file  # noqa: E402


DEFAULT_PACK = os.path.join(_ROOT, "benchmark", "drp_auditability_pack")


@dataclass
class FileOutcome:
    path: str
    ok: bool
    error_count: int


@dataclass
class CategoryReport:
    name: str
    expectation: str  # "all_valid" | "all_invalid"
    files: list[FileOutcome]

    @property
    def matches_expectation(self) -> bool:
        if self.expectation == "all_valid":
            return all(f.ok for f in self.files)
        if self.expectation == "all_invalid":
            return all(not f.ok for f in self.files)
        return False


_EXPECTATIONS = {
    "valid": "all_valid",
    "invalid": "all_invalid",
    "ambiguous": "all_valid",
    "comparison": "all_valid",
}


def _iter_json_files(category_dir: str) -> list[str]:
    if not os.path.isdir(category_dir):
        return []
    out: list[str] = []
    for name in sorted(os.listdir(category_dir)):
        if name.endswith(".json"):
            out.append(os.path.join(category_dir, name))
    return out


def _run_category(pack_dir: str, name: str) -> CategoryReport:
    expectation = _EXPECTATIONS[name]
    files: list[FileOutcome] = []
    for path in _iter_json_files(os.path.join(pack_dir, name)):
        try:
            result = validate_file(path)
            files.append(
                FileOutcome(path=path, ok=result.ok, error_count=len(result.errors))
            )
        except (OSError, json.JSONDecodeError) as e:
            print(f"error reading {path}: {e}", file=sys.stderr)
            files.append(FileOutcome(path=path, ok=False, error_count=-1))
    return CategoryReport(name=name, expectation=expectation, files=files)


def _print_text(reports: list[CategoryReport]) -> bool:
    all_matched = True
    for r in reports:
        print(f"[{r.name}] expectation={r.expectation}")
        for f in r.files:
            rel = os.path.relpath(f.path, _ROOT)
            marker = "OK  " if f.ok else "FAIL"
            err_note = "" if f.error_count <= 0 else f" ({f.error_count} error(s))"
            print(f"  {marker}  {rel}{err_note}")
        status = "MATCH" if r.matches_expectation else "MISMATCH"
        print(f"  -> {status} ({len(r.files)} file(s))")
        all_matched = all_matched and r.matches_expectation
    print()
    print("SUMMARY: " + ("all categories matched" if all_matched else "mismatch in at least one category"))
    return all_matched


def _print_json(reports: list[CategoryReport]) -> bool:
    out = {
        "pack": "drp_auditability_pack",
        "categories": [
            {
                "name": r.name,
                "expectation": r.expectation,
                "matches_expectation": r.matches_expectation,
                "files": [
                    {
                        "path": os.path.relpath(f.path, _ROOT),
                        "ok": f.ok,
                        "error_count": f.error_count,
                    }
                    for f in r.files
                ],
            }
            for r in reports
        ],
    }
    out["all_matched"] = all(r.matches_expectation for r in reports)
    print(json.dumps(out, indent=2))
    return bool(out["all_matched"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_benchmark",
        description="Run the DRP auditability benchmark pack.",
    )
    parser.add_argument(
        "--pack",
        default=DEFAULT_PACK,
        help="Path to the benchmark pack (default: benchmark/drp_auditability_pack).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable JSON report on stdout.",
    )
    args = parser.parse_args(argv)

    reports = [_run_category(args.pack, name) for name in _EXPECTATIONS]
    ok = _print_json(reports) if args.json else _print_text(reports)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
