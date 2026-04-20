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
the schema, or the validator.

Exit codes:
  0 -- every category matched its expectation.
  1 -- at least one category did not match.
  2 -- usage error: pack path is missing, not a directory, or the
       reference validator could not be imported.
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

try:
    from drp_validator import validate_file  # noqa: E402
except ImportError as e:  # pragma: no cover - defensive
    print(
        f"run_benchmark: cannot import reference validator "
        f"(tools/drp_validator.py): {e}",
        file=sys.stderr,
    )
    sys.exit(2)


DEFAULT_PACK = os.path.join(_ROOT, "benchmark", "drp_auditability_pack")

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_USAGE = 2


@dataclass
class FileOutcome:
    path: str
    ok: bool
    error_count: int
    errors: list  # list[str], only populated in verbose mode


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


def _run_category(pack_dir: str, name: str, verbose: bool) -> CategoryReport:
    expectation = _EXPECTATIONS[name]
    files: list[FileOutcome] = []
    for path in _iter_json_files(os.path.join(pack_dir, name)):
        try:
            result = validate_file(path)
            files.append(
                FileOutcome(
                    path=path,
                    ok=result.ok,
                    error_count=len(result.errors),
                    errors=[e.format() for e in result.errors] if verbose else [],
                )
            )
        except (OSError, json.JSONDecodeError) as e:
            print(f"error reading {path}: {e}", file=sys.stderr)
            files.append(
                FileOutcome(path=path, ok=False, error_count=-1, errors=[str(e)])
            )
    return CategoryReport(name=name, expectation=expectation, files=files)


def _print_text(reports: list[CategoryReport], verbose: bool) -> bool:
    all_matched = True
    for r in reports:
        print(f"[{r.name}] expectation={r.expectation}")
        for f in r.files:
            rel = os.path.relpath(f.path, _ROOT)
            marker = "OK  " if f.ok else "FAIL"
            err_note = "" if f.error_count <= 0 else f" ({f.error_count} error(s))"
            print(f"  {marker}  {rel}{err_note}")
            if verbose and f.errors:
                for msg in f.errors:
                    print(f"         {msg}")
        status = "MATCH" if r.matches_expectation else "MISMATCH"
        print(f"  -> {status} ({len(r.files)} file(s))")
        all_matched = all_matched and r.matches_expectation
    print()
    print(
        "SUMMARY: "
        + ("all categories matched" if all_matched else "mismatch in at least one category")
    )
    return all_matched


def _print_json(reports: list[CategoryReport], verbose: bool) -> bool:
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
                        **({"errors": f.errors} if verbose else {}),
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


def _validate_pack(pack_dir: str) -> None:
    if not os.path.exists(pack_dir):
        raise SystemExit(
            f"run_benchmark: pack directory does not exist: {pack_dir}"
        )
    if not os.path.isdir(pack_dir):
        raise SystemExit(
            f"run_benchmark: pack path is not a directory: {pack_dir}"
        )


def _validate_categories(pack_dir: str) -> None:
    """
    Warn if a subdirectory under ``pack_dir`` is not a known category.
    This keeps accidental typos (e.g. ``valld/``) from being silently
    skipped.
    """
    try:
        entries = os.listdir(pack_dir)
    except OSError:
        return
    known = set(_EXPECTATIONS.keys())
    for entry in sorted(entries):
        full = os.path.join(pack_dir, entry)
        if os.path.isdir(full) and entry not in known:
            print(
                f"run_benchmark: warning: unknown category directory "
                f"'{entry}/' at {pack_dir}; expected one of "
                f"{sorted(known)}",
                file=sys.stderr,
            )


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
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Include per-file validator error messages in the output.",
    )
    args = parser.parse_args(argv)

    try:
        _validate_pack(args.pack)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return EXIT_USAGE

    _validate_categories(args.pack)

    reports = [
        _run_category(args.pack, name, args.verbose) for name in _EXPECTATIONS
    ]
    ok = (
        _print_json(reports, args.verbose)
        if args.json
        else _print_text(reports, args.verbose)
    )
    return EXIT_OK if ok else EXIT_MISMATCH


if __name__ == "__main__":
    sys.exit(main())
