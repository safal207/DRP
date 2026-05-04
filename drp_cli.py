"""DRP command-line interface for validation and linting.

This is a thin wrapper around :mod:`tools.drp_validator` and :mod:`linter`
that adds glob expansion, multi-file output, severity/rule filters, and
a stable exit-code contract.

Subcommands
-----------
* ``validate`` -- run the reference validator over one or more files.
* ``lint``     -- run lint rules over one or more files.
* ``rules``    -- list registered lint rules.

Exit codes (stable across releases)
-----------------------------------
* ``0`` -- success.
* ``1`` -- one or more validation errors.
* ``2`` -- CLI usage / input error (missing file, bad JSON, bad flag).
* ``3`` -- lint warnings promoted to failure via ``--fail-on-warn``.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Iterable, Optional

from linter import (
    ALL_SEVERITIES,
    SEVERITY_INFO,
    all_rules,
    lint_data,
)
from tools import drp_validator


__version__ = "0.2.0"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2
EXIT_LINT_FAIL = 3

_KNOWN_SUBCOMMANDS = {"validate", "lint", "rules"}


# --------------------------------------------------------------------------- #
# argparse plumbing
# --------------------------------------------------------------------------- #
class _UsageError(SystemExit):
    """Raised by :class:`_Parser` so ``main()`` can return EXIT_USAGE."""


class _Parser(argparse.ArgumentParser):
    """ArgumentParser that surfaces the documented EXIT_USAGE code."""

    def error(self, message):  # type: ignore[override]
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: error: {message}\n")
        raise _UsageError(EXIT_USAGE)


# --------------------------------------------------------------------------- #
# Color handling (TTY + NO_COLOR / FORCE_COLOR aware)
# --------------------------------------------------------------------------- #
def _supports_color(stream=None) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    stream = stream or sys.stdout
    return bool(getattr(stream, "isatty", lambda: False)())


class _Style:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, code, s):
        return f"{code}{s}{RESET}" if self.enabled else str(s)

    def green(self, s): return self._wrap(GREEN, s)
    def red(self, s): return self._wrap(RED, s)
    def yellow(self, s): return self._wrap(YELLOW, s)
    def bold(self, s): return self._wrap(BOLD, s)
    def dim(self, s): return self._wrap(DIM, s)


# --------------------------------------------------------------------------- #
# Path expansion
# --------------------------------------------------------------------------- #
def _expand_paths(patterns: Iterable[str]) -> list:
    """Expand each pattern via glob; preserve unmatched literals so the caller
    can report them as missing inputs (instead of silently dropping them)."""
    paths: list = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        paths.extend(matches if matches else [pattern])
    return paths


def _split_existing(paths: list) -> tuple:
    existing, missing = [], []
    seen = set()
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        if os.path.isfile(p):
            existing.append(p)
        else:
            missing.append(p)
    return existing, missing


# --------------------------------------------------------------------------- #
# Validate
# --------------------------------------------------------------------------- #
def _validate_files(paths: list) -> tuple:
    payload = {"status": "OK", "files": [], "error_count": 0}
    has_errors = False
    for path in paths:
        try:
            result = drp_validator.validate_file(path)
        except (OSError, json.JSONDecodeError) as exc:
            has_errors = True
            payload["error_count"] += 1
            payload["files"].append({
                "path": path,
                "ok": False,
                "errors": [{
                    "layer": "io",
                    "record_id": None,
                    "field": None,
                    "message": str(exc),
                }],
            })
            continue

        if result.ok:
            payload["files"].append({"path": path, "ok": True, "errors": []})
        else:
            has_errors = True
            payload["error_count"] += len(result.errors)
            payload["files"].append({
                "path": path,
                "ok": False,
                "errors": [e.to_dict() for e in result.errors],
            })

    if has_errors:
        payload["status"] = "FAIL"
    return (EXIT_INVALID if has_errors else EXIT_OK), payload


# --------------------------------------------------------------------------- #
# Lint
# --------------------------------------------------------------------------- #
def _lint_files(
    paths,
    *,
    enabled_rules,
    disabled_rules,
    min_severity,
):
    payload = {"status": "OK", "files": [], "warning_count": 0}
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            payload["files"].append(
                {"path": path, "warnings": [], "skipped": str(exc)}
            )
            continue
        warnings = lint_data(
            data,
            enabled_rules=enabled_rules,
            disabled_rules=disabled_rules,
            min_severity=min_severity,
        )
        payload["warning_count"] += len(warnings)
        payload["files"].append(
            {"path": path, "warnings": [w.to_dict() for w in warnings]}
        )
    return EXIT_OK, payload


# --------------------------------------------------------------------------- #
# Output formatters
# --------------------------------------------------------------------------- #
def _print_validate_human(payload, style, quiet=False):
    n_files = len(payload["files"])
    n_ok = sum(1 for f in payload["files"] if f["ok"])
    n_fail = n_files - n_ok
    for item in payload["files"]:
        if item["ok"]:
            if not quiet:
                print(style.green(f"{item['path']}: ok"))
        else:
            print(style.red(f"{item['path']}: FAIL ({len(item['errors'])} error(s))"))
            for err in item["errors"]:
                layer = err.get("layer", "?")
                fld = err.get("field")
                msg = err.get("message", "")
                loc = f" [{fld}]" if fld else ""
                print(f"  - [{layer}]{loc} {msg}")
    summary = (
        f"summary: {n_files} file(s), {n_ok} ok, {n_fail} failing, "
        f"{payload['error_count']} error(s)"
    )
    color = style.green if n_fail == 0 else style.red
    print(color(style.bold(summary)))


def _print_lint_human(payload, style, quiet=False):
    n_files = len(payload["files"])
    n_clean = sum(
        1 for f in payload["files"] if not f.get("warnings") and "skipped" not in f
    )
    n_skipped = sum(1 for f in payload["files"] if "skipped" in f)
    for item in payload["files"]:
        if "skipped" in item:
            print(style.yellow(f"{item['path']}: lint skipped ({item['skipped']})"))
            continue
        warnings = item["warnings"]
        if warnings:
            print(style.yellow(f"{item['path']}: {len(warnings)} warning(s)"))
            for w in warnings:
                where_parts = []
                if w.get("record_id"):
                    where_parts.append(w["record_id"])
                elif w.get("record_index") is not None:
                    where_parts.append(f"[{w['record_index']}]")
                where_parts.append(w["field"])
                where = "/".join(where_parts)
                print(
                    f"  - [{w['rule_id']}] [{w['severity']}] {where}: {w['message']}"
                )
        elif not quiet:
            print(style.green(f"{item['path']}: lint clean"))
    summary = (
        f"summary: {n_files} file(s), {n_clean} clean, "
        f"{n_skipped} skipped, {payload['warning_count']} warning(s)"
    )
    color = style.yellow if payload["warning_count"] > 0 else style.green
    print(color(style.bold(summary)))


def _print_rules(style, as_json=False):
    rules = all_rules()
    if as_json:
        print(json.dumps(
            [
                {"rule_id": r.rule_id, "severity": r.severity, "description": r.description}
                for r in rules
            ],
            ensure_ascii=False,
            indent=2,
        ))
        return
    print(style.bold(f"Available DRP lint rules ({len(rules)}):"))
    width = max((len(r.severity) for r in rules), default=0)
    for r in rules:
        print(f"  {r.rule_id}  [{r.severity:<{width}s}]  {r.description}")


# --------------------------------------------------------------------------- #
# Argument parser
# --------------------------------------------------------------------------- #
def _add_filter_args(parser):
    parser.add_argument(
        "--min-severity",
        choices=ALL_SEVERITIES,
        default=SEVERITY_INFO,
        help="Suppress warnings below this severity (default: info).",
    )
    parser.add_argument(
        "--rule",
        action="append",
        metavar="RULE_ID",
        help="Only run the specified rule(s); repeat to allow several.",
    )
    parser.add_argument(
        "--disable-rule",
        action="append",
        metavar="RULE_ID",
        help="Skip the specified rule(s); repeat to skip several.",
    )


def _build_parser() -> _Parser:
    parser = _Parser(
        prog="drp-validate",
        description="Validate and lint DRP JSON records.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"drp-validate {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    val = sub.add_parser(
        "validate",
        help="Validate DRP JSON files.",
        description="Run the reference validator over one or more files.",
    )
    val.add_argument("paths", nargs="+", help="JSON files or glob patterns.")
    val.add_argument(
        "--format", choices=["human", "json"], default="human",
        help="Output format (default: human).",
    )
    val.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI colors (also honors NO_COLOR env var).",
    )
    val.add_argument(
        "--quiet", action="store_true",
        help="Suppress lines for passing files; print failures and summary only.",
    )
    val.add_argument(
        "--lint", action="store_true",
        help="Also run lint checks after validation.",
    )
    val.add_argument(
        "--fail-on-warn", action="store_true",
        help="Return EXIT_LINT_FAIL when --lint surfaces any warnings.",
    )
    _add_filter_args(val)

    lint_p = sub.add_parser(
        "lint",
        help="Lint DRP JSON files.",
        description="Run extensible best-practice and style checks.",
    )
    lint_p.add_argument("paths", nargs="+", help="JSON files or glob patterns.")
    lint_p.add_argument(
        "--format", choices=["human", "json"], default="human",
        help="Output format (default: human).",
    )
    lint_p.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI colors (also honors NO_COLOR env var).",
    )
    lint_p.add_argument(
        "--quiet", action="store_true",
        help="Suppress lines for clean files; print warnings and summary only.",
    )
    lint_p.add_argument(
        "--fail-on-warn", action="store_true",
        help="Return EXIT_LINT_FAIL when any warnings exist.",
    )
    _add_filter_args(lint_p)

    rules_p = sub.add_parser(
        "rules",
        help="List registered lint rules.",
        description="List all known lint rule IDs, severities, and descriptions.",
    )
    rules_p.add_argument(
        "--format", choices=["human", "json"], default="human",
        help="Output format (default: human).",
    )
    rules_p.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI colors (also honors NO_COLOR env var).",
    )

    return parser


def _normalize_argv(argv):
    """Allow ``drp-validate FILE`` as shorthand for ``drp-validate validate FILE``.

    Only triggers when the first token is a non-flag, non-subcommand string.
    Flags (``-h``, ``--version``, etc.) are passed through untouched.
    """
    if not argv:
        return argv
    first = argv[0]
    if first.startswith("-"):
        return argv
    if first in _KNOWN_SUBCOMMANDS:
        return argv
    return ["validate", *argv]


def _resolve_rule_filters(args, style):
    enabled = set(args.rule) if getattr(args, "rule", None) else None
    disabled = set(args.disable_rule) if getattr(args, "disable_rule", None) else set()
    known = {r.rule_id for r in all_rules()}
    for given, label in ((enabled or set(), "rule"), (disabled, "disable-rule")):
        unknown = given - known
        for u in sorted(unknown):
            print(
                style.yellow(f"warning: --{label} references unknown rule {u!r}; ignored"),
                file=sys.stderr,
            )
    if enabled is not None:
        enabled &= known
        if not enabled:
            print(
                style.yellow("warning: --rule filter matched no known rules; nothing to do"),
                file=sys.stderr,
            )
    return enabled, disabled & known


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv: Optional[list] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    argv = _normalize_argv(argv)

    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except _UsageError as exc:
        return int(exc.code)
    except SystemExit as exc:  # --help / --version short-circuits
        return int(exc.code) if exc.code is not None else EXIT_OK

    style = _Style(enabled=(not args.no_color) and _supports_color())

    if args.command == "rules":
        _print_rules(style, as_json=(args.format == "json"))
        return EXIT_OK

    raw = _expand_paths(args.paths)
    existing, missing = _split_existing(raw)
    if not existing:
        for m in missing:
            print(f"drp-validate: input not found: {m}", file=sys.stderr)
        return EXIT_USAGE
    for m in missing:
        print(
            style.yellow(f"warning: skipping unreadable input {m!r}"),
            file=sys.stderr,
        )

    if args.command == "validate":
        rc, vpayload = _validate_files(existing)
        lpayload = None
        if args.lint:
            enabled, disabled = _resolve_rule_filters(args, style)
            _, lpayload = _lint_files(
                existing,
                enabled_rules=enabled,
                disabled_rules=disabled,
                min_severity=args.min_severity,
            )
            if args.fail_on_warn and lpayload["warning_count"] > 0 and rc == EXIT_OK:
                rc = EXIT_LINT_FAIL

        if args.format == "json":
            out = {"validate": vpayload}
            if lpayload is not None:
                out["lint"] = lpayload
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            _print_validate_human(vpayload, style, quiet=args.quiet)
            if lpayload is not None:
                print()
                _print_lint_human(lpayload, style, quiet=args.quiet)
        return rc

    if args.command == "lint":
        enabled, disabled = _resolve_rule_filters(args, style)
        _, lpayload = _lint_files(
            existing,
            enabled_rules=enabled,
            disabled_rules=disabled,
            min_severity=args.min_severity,
        )
        if args.format == "json":
            print(json.dumps(lpayload, ensure_ascii=False, indent=2))
        else:
            _print_lint_human(lpayload, style, quiet=args.quiet)
        if args.fail_on_warn and lpayload["warning_count"] > 0:
            return EXIT_LINT_FAIL
        return EXIT_OK

    return EXIT_OK  # unreachable: argparse enforces required subcommand


if __name__ == "__main__":
    sys.exit(main())
