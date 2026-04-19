"""
DRP reference validator.

Validates a single DRP record or a batch of records in three layers:
schema, semantic, and graph. See docs/VALIDATION.md for the full
contract and docs/SPEC.md for the normative rules.

This module requires only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator


SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "schema",
    "drp.schema.json",
)

ALLOWED_STATUS = frozenset(
    {"draft", "proposed", "complete", "superseded", "rejected"}
)
ALLOWED_IMPACT = (-1, 0, 1, None)
ALLOWED_TOP_LEVEL_FIELDS = frozenset(
    {
        "record_id",
        "timestamp",
        "context",
        "decision",
        "options",
        "status",
        "rationale",
        "impact",
        "parent_record_ids",
        "child_record_ids",
        "supersedes_record_id",
        "tags",
        "metadata",
    }
)
REQUIRED_FIELDS = (
    "record_id",
    "timestamp",
    "context",
    "decision",
    "options",
    "status",
)


# --------------------------------------------------------------------------- #
# CLI exit codes
# --------------------------------------------------------------------------- #
# Stable across releases. See docs/VALIDATION.md for the contract.
EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2


# --------------------------------------------------------------------------- #
# Error model
# --------------------------------------------------------------------------- #

@dataclass
class ValidationError:
    layer: str  # "schema" | "semantic" | "graph"
    record_id: str | None
    field: str | None
    message: str

    def format(self) -> str:
        ident = self.record_id if self.record_id else "<unknown>"
        loc = f" [{self.field}]" if self.field else ""
        return f"[{self.layer}] {ident}{loc}: {self.message}"

    def to_dict(self) -> dict:
        return {
            "layer": self.layer,
            "record_id": self.record_id,
            "field": self.field,
            "message": self.message,
        }


@dataclass
class ValidationResult:
    errors: list[ValidationError] = field(default_factory=list)
    record_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors

    def extend(self, errs: Iterable[ValidationError]) -> None:
        self.errors.extend(errs)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

_ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]00:00)$"
)


def _is_bool(x: Any) -> bool:
    return isinstance(x, bool)


def _is_int(x: Any) -> bool:
    # Python treats booleans as integers; we do not.
    return isinstance(x, int) and not _is_bool(x)


def _is_str(x: Any) -> bool:
    return isinstance(x, str)


def _parse_iso_utc(ts: str) -> datetime | None:
    if not _is_str(ts):
        return None
    if not _ISO_RE.match(ts):
        return None
    try:
        normalized = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(None):
        # Must be UTC. +00:00 offset passes; anything else fails.
        if dt.utcoffset() is None or dt.utcoffset().total_seconds() != 0:
            return None
    return dt


def _get_rid(record: Any) -> str | None:
    if isinstance(record, dict):
        rid = record.get("record_id")
        if isinstance(rid, str):
            return rid
    return None


# --------------------------------------------------------------------------- #
# Schema layer
# --------------------------------------------------------------------------- #

def _schema_validate(record: Any, index: int) -> list[ValidationError]:
    errs: list[ValidationError] = []
    rid = _get_rid(record)

    if not isinstance(record, dict):
        errs.append(
            ValidationError(
                "schema",
                None,
                None,
                f"record at index {index} is not a JSON object",
            )
        )
        return errs

    # Unknown top-level fields.
    for key in record.keys():
        if key not in ALLOWED_TOP_LEVEL_FIELDS:
            errs.append(
                ValidationError(
                    "schema", rid, key, f"unknown top-level field '{key}'"
                )
            )

    # Required fields present.
    for fld in REQUIRED_FIELDS:
        if fld not in record:
            errs.append(
                ValidationError(
                    "schema", rid, fld, f"required field '{fld}' is missing"
                )
            )

    # Field type checks.
    def _check_type(name: str, predicate, typelabel: str) -> None:
        if name in record and not predicate(record[name]):
            errs.append(
                ValidationError(
                    "schema",
                    rid,
                    name,
                    f"'{name}' must be {typelabel}",
                )
            )

    _check_type("record_id", _is_str, "a string")
    _check_type("timestamp", _is_str, "a string")
    _check_type("context", _is_str, "a string")
    _check_type("decision", _is_str, "a string")
    _check_type("rationale", _is_str, "a string")
    _check_type("supersedes_record_id", _is_str, "a string")
    _check_type("status", _is_str, "a string")
    _check_type(
        "options", lambda v: isinstance(v, list), "an array"
    )
    _check_type(
        "parent_record_ids", lambda v: isinstance(v, list), "an array"
    )
    _check_type(
        "child_record_ids", lambda v: isinstance(v, list), "an array"
    )
    _check_type("tags", lambda v: isinstance(v, list), "an array")
    _check_type(
        "metadata",
        lambda v: isinstance(v, dict),
        "an object",
    )

    # Array element types.
    for arr_field in ("options", "parent_record_ids", "child_record_ids", "tags"):
        if arr_field in record and isinstance(record[arr_field], list):
            for i, el in enumerate(record[arr_field]):
                if not _is_str(el):
                    errs.append(
                        ValidationError(
                            "schema",
                            rid,
                            f"{arr_field}[{i}]",
                            f"'{arr_field}' elements must be strings",
                        )
                    )

    # Status enum.
    if "status" in record and _is_str(record["status"]):
        if record["status"] not in ALLOWED_STATUS:
            errs.append(
                ValidationError(
                    "schema",
                    rid,
                    "status",
                    f"'status' must be one of "
                    f"{sorted(ALLOWED_STATUS)}, got {record['status']!r}",
                )
            )

    # Impact enum. Booleans are rejected here so that later layers never
    # see a boolean leaking through as 0/1.
    if "impact" in record:
        v = record["impact"]
        if _is_bool(v) or (v is not None and not _is_int(v)) or (
            _is_int(v) and v not in (-1, 0, 1)
        ):
            errs.append(
                ValidationError(
                    "schema",
                    rid,
                    "impact",
                    "'impact' must be one of -1, 0, 1, null "
                    "(booleans are not accepted)",
                )
            )

    return errs


# --------------------------------------------------------------------------- #
# Semantic layer (per-record)
# --------------------------------------------------------------------------- #

def _semantic_validate(record: dict, rid: str | None) -> list[ValidationError]:
    errs: list[ValidationError] = []

    def _nonempty_trimmed(name: str) -> None:
        v = record.get(name)
        if _is_str(v) and not v.strip():
            errs.append(
                ValidationError(
                    "semantic",
                    rid,
                    name,
                    f"'{name}' must be a non-empty trimmed string",
                )
            )

    _nonempty_trimmed("record_id")
    _nonempty_trimmed("context")
    _nonempty_trimmed("decision")
    _nonempty_trimmed("supersedes_record_id")

    # options must be non-empty; elements non-empty trimmed strings.
    opts = record.get("options")
    if isinstance(opts, list):
        if len(opts) == 0:
            errs.append(
                ValidationError(
                    "semantic",
                    rid,
                    "options",
                    "'options' must be a non-empty array",
                )
            )
        for i, el in enumerate(opts):
            if _is_str(el) and not el.strip():
                errs.append(
                    ValidationError(
                        "semantic",
                        rid,
                        f"options[{i}]",
                        "option strings must be non-empty after trimming",
                    )
                )

    # tags, if present.
    tags = record.get("tags")
    if isinstance(tags, list):
        for i, el in enumerate(tags):
            if _is_str(el) and not el.strip():
                errs.append(
                    ValidationError(
                        "semantic",
                        rid,
                        f"tags[{i}]",
                        "tags must be non-empty after trimming",
                    )
                )

    # Timestamp.
    ts = record.get("timestamp")
    if _is_str(ts) and _parse_iso_utc(ts) is None:
        errs.append(
            ValidationError(
                "semantic",
                rid,
                "timestamp",
                f"'timestamp' is not a valid ISO 8601 UTC timestamp: {ts!r}",
            )
        )

    # Supersession: status=superseded requires supersedes_record_id.
    if record.get("status") == "superseded":
        sid = record.get("supersedes_record_id")
        if not (_is_str(sid) and sid.strip()):
            errs.append(
                ValidationError(
                    "semantic",
                    rid,
                    "supersedes_record_id",
                    "status 'superseded' requires a non-empty "
                    "'supersedes_record_id'",
                )
            )

    # No self-supersession.
    sid = record.get("supersedes_record_id")
    if _is_str(sid) and rid is not None and sid == rid:
        errs.append(
            ValidationError(
                "semantic",
                rid,
                "supersedes_record_id",
                "a record must not supersede itself",
            )
        )

    # No self parent/child.
    for fld in ("parent_record_ids", "child_record_ids"):
        ids = record.get(fld)
        if isinstance(ids, list) and rid is not None and rid in ids:
            errs.append(
                ValidationError(
                    "semantic",
                    rid,
                    fld,
                    f"a record must not reference itself in '{fld}'",
                )
            )

    return errs


# --------------------------------------------------------------------------- #
# Graph layer (whole-batch)
# --------------------------------------------------------------------------- #

def _graph_validate(records: list[dict]) -> list[ValidationError]:
    errs: list[ValidationError] = []

    # Build id -> record map and detect duplicates.
    by_id: dict[str, dict] = {}
    seen_ids: set[str] = set()
    duplicates: set[str] = set()
    for rec in records:
        rid = rec.get("record_id")
        if not _is_str(rid):
            continue
        if rid in seen_ids:
            duplicates.add(rid)
        else:
            seen_ids.add(rid)
            by_id[rid] = rec

    for dup in sorted(duplicates):
        errs.append(
            ValidationError(
                "graph",
                dup,
                "record_id",
                f"duplicate record_id '{dup}' within batch",
            )
        )

    # Reference resolution and bidirectional consistency.
    for rec in records:
        rid = rec.get("record_id")
        if not _is_str(rid):
            continue

        parents = rec.get("parent_record_ids") or []
        children = rec.get("child_record_ids") or []

        if isinstance(parents, list):
            for p in parents:
                if not _is_str(p):
                    continue
                if p not in by_id:
                    errs.append(
                        ValidationError(
                            "graph",
                            rid,
                            "parent_record_ids",
                            f"parent reference '{p}' does not resolve",
                        )
                    )
                    continue
                # Bidirectional check: parent must list rid as child.
                parent_children = by_id[p].get("child_record_ids") or []
                if not isinstance(parent_children, list) or rid not in parent_children:
                    errs.append(
                        ValidationError(
                            "graph",
                            rid,
                            "parent_record_ids",
                            f"parent '{p}' does not list '{rid}' "
                            f"in its child_record_ids",
                        )
                    )
                # Timestamp ordering.
                pts = _parse_iso_utc(by_id[p].get("timestamp", ""))
                cts = _parse_iso_utc(rec.get("timestamp", ""))
                if pts and cts and pts > cts:
                    errs.append(
                        ValidationError(
                            "graph",
                            rid,
                            "timestamp",
                            f"parent '{p}' timestamp is later than "
                            f"child '{rid}' timestamp",
                        )
                    )

        if isinstance(children, list):
            for c in children:
                if not _is_str(c):
                    continue
                if c not in by_id:
                    errs.append(
                        ValidationError(
                            "graph",
                            rid,
                            "child_record_ids",
                            f"child reference '{c}' does not resolve",
                        )
                    )
                    continue
                child_parents = by_id[c].get("parent_record_ids") or []
                if not isinstance(child_parents, list) or rid not in child_parents:
                    errs.append(
                        ValidationError(
                            "graph",
                            rid,
                            "child_record_ids",
                            f"child '{c}' does not list '{rid}' "
                            f"in its parent_record_ids",
                        )
                    )

        # Supersession resolution and ordering.
        sid = rec.get("supersedes_record_id")
        if _is_str(sid) and sid.strip():
            if sid not in by_id:
                errs.append(
                    ValidationError(
                        "graph",
                        rid,
                        "supersedes_record_id",
                        f"supersedes reference '{sid}' does not resolve",
                    )
                )
            else:
                sts = _parse_iso_utc(by_id[sid].get("timestamp", ""))
                nts = _parse_iso_utc(rec.get("timestamp", ""))
                if sts and nts and nts < sts:
                    errs.append(
                        ValidationError(
                            "graph",
                            rid,
                            "timestamp",
                            f"superseding record '{rid}' timestamp is "
                            f"earlier than superseded record '{sid}' "
                            "timestamp",
                        )
                    )

    # G6: acyclicity. Always run regardless of prior errors; the cycle
    # detector only traverses edges that resolve within by_id, so
    # unresolved references do not cause false positives here.
    errs.extend(_detect_cycles(by_id))

    return errs


def _detect_cycles(by_id: dict[str, dict]) -> list[ValidationError]:
    """
    Detect directed cycles in the parent->child graph using iterative DFS.

    G4 (timestamp ordering) is sufficient to rule out cycles when all
    timestamps are strictly ordered, but it does not catch cycles where
    two or more nodes share the same timestamp. This function explicitly
    enforces G6 regardless of timestamp values.
    """
    errs: list[ValidationError] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {rid: WHITE for rid in by_id}

    def successors(rid: str) -> list[str]:
        kids = by_id[rid].get("child_record_ids") or []
        return [c for c in kids if isinstance(c, str) and c in by_id]

    for start in list(by_id.keys()):
        if color[start] != WHITE:
            continue
        color[start] = GRAY
        stack: list[tuple[str, Iterator[str]]] = [
            (start, iter(successors(start)))
        ]
        while stack:
            node, it = stack[-1]
            try:
                child = next(it)
                if color[child] == GRAY:
                    errs.append(
                        ValidationError(
                            "graph",
                            node,
                            "child_record_ids",
                            f"cycle detected: '{node}' -> '{child}' "
                            f"creates a cycle in the parent/child graph",
                        )
                    )
                elif color[child] == WHITE:
                    color[child] = GRAY
                    stack.append((child, iter(successors(child))))
            except StopIteration:
                color[node] = BLACK
                stack.pop()

    return errs


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def validate(data: Any) -> ValidationResult:
    """
    Validate a DRP record or batch.

    `data` may be a dict (single record) or a list (batch of records).
    """
    result = ValidationResult()

    if isinstance(data, dict):
        records: list[Any] = [data]
    elif isinstance(data, list):
        records = data
    else:
        result.errors.append(
            ValidationError(
                "schema",
                None,
                None,
                "top-level value must be an object or an array of objects",
            )
        )
        return result

    result.record_count = len(records)

    # Layer 1: schema.
    schema_errors: list[ValidationError] = []
    for i, rec in enumerate(records):
        schema_errors.extend(_schema_validate(rec, i))
    if schema_errors:
        result.extend(schema_errors)
        return result

    # Layer 2: semantic (per-record).
    semantic_errors: list[ValidationError] = []
    for rec in records:
        semantic_errors.extend(_semantic_validate(rec, _get_rid(rec)))
    if semantic_errors:
        result.extend(semantic_errors)
        return result

    # Layer 3: graph (whole-batch).
    graph_errors = _graph_validate(records)
    if graph_errors:
        result.extend(graph_errors)
        return result

    return result


def validate_file(path: str) -> ValidationResult:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return validate(data)


# --------------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------------- #

def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="drp-validate",
        description="Validate a DRP record or batch.",
    )
    parser.add_argument("path", help="Path to a JSON file (record or batch).")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output instead of plain text.",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        msg = f"file not found: {args.path}"
        if args.json:
            print(json.dumps({"status": "ERROR", "message": msg}))
        else:
            print(f"drp-validate: {msg}", file=sys.stderr)
        return EXIT_USAGE
    except json.JSONDecodeError as e:
        msg = f"invalid JSON: {e}"
        if args.json:
            print(json.dumps({"status": "ERROR", "message": msg}))
        else:
            print(f"drp-validate: {msg}", file=sys.stderr)
        return EXIT_USAGE
    except OSError as e:
        msg = f"cannot read {args.path}: {e}"
        if args.json:
            print(json.dumps({"status": "ERROR", "message": msg}))
        else:
            print(f"drp-validate: {msg}", file=sys.stderr)
        return EXIT_USAGE

    result = validate(data)

    if result.ok:
        if args.json:
            print(json.dumps({
                "status": "OK",
                "record_count": result.record_count,
                "errors": [],
            }))
        else:
            print(f"OK: {result.record_count} record(s) validated")
        return EXIT_OK

    if args.json:
        print(json.dumps({
            "status": "FAIL",
            "record_count": result.record_count,
            "errors": [e.to_dict() for e in result.errors],
        }))
    else:
        for err in result.errors:
            print(err.format())
        print(f"FAIL: {len(result.errors)} error(s)")
    return EXIT_INVALID


if __name__ == "__main__":
    sys.exit(_main())
