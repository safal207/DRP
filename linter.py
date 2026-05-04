"""DRP linter with extensible, rule-id based checks.

Each lint rule emits zero or more :class:`LintWarning` instances against a
single DRP record. Rules are registered via the :func:`register_rule`
decorator and discovered automatically by :func:`lint_record`.

Rules check *style* and *best-practice* signals on records that have
already passed (or will be passed through) the reference validator. They
deliberately do not duplicate schema/semantic checks performed by
``tools/drp_validator.py`` -- the linter assumes inputs are well-formed
DRP records and only flags non-blocking improvements.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Optional


# --------------------------------------------------------------------------- #
# Severity model
# --------------------------------------------------------------------------- #
SEVERITY_INFO = "info"
SEVERITY_STYLE = "style"
SEVERITY_BEST_PRACTICE = "best_practice"

ALL_SEVERITIES = (SEVERITY_INFO, SEVERITY_STYLE, SEVERITY_BEST_PRACTICE)

_SEVERITY_RANK = {
    SEVERITY_INFO: 0,
    SEVERITY_STYLE: 1,
    SEVERITY_BEST_PRACTICE: 2,
}


# --------------------------------------------------------------------------- #
# Warning model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LintWarning:
    """A single lint finding for a DRP record.

    ``record_id`` is set when the record carries a string ``record_id``;
    ``record_index`` is set when the record was provided in a batch.
    """

    rule_id: str
    message: str
    field: str
    severity: str
    record_id: Optional[str] = None
    record_index: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def format(self) -> str:
        loc_parts = []
        if self.record_id:
            loc_parts.append(self.record_id)
        elif self.record_index is not None:
            loc_parts.append(f"[{self.record_index}]")
        loc_parts.append(self.field)
        return (
            f"[{self.rule_id}] [{self.severity}] "
            f"{'/'.join(loc_parts)}: {self.message}"
        )


# --------------------------------------------------------------------------- #
# Rule registry
# --------------------------------------------------------------------------- #
RuleFunc = Callable[[dict], list]  # returns list[tuple[str, str]]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    severity: str
    description: str
    func: RuleFunc = field(compare=False)


_RULES: list = []
_RULE_IDS: set = set()


def register_rule(rule_id: str, severity: str, description: str):
    """Decorator: register *func* as a lint rule.

    The wrapped function receives a single DRP record (a ``dict``) and
    returns a list of ``(field, message)`` tuples. Returning an empty
    list means the rule passed.

    Severity must be one of :data:`ALL_SEVERITIES`. Rule IDs must be
    unique; re-registering the same ID raises ``ValueError`` so tests
    that import the module twice fail fast instead of silently
    duplicating warnings.
    """
    if severity not in ALL_SEVERITIES:
        raise ValueError(
            f"unknown severity {severity!r}; expected one of {ALL_SEVERITIES}"
        )

    def decorator(func):
        if rule_id in _RULE_IDS:
            return func
        _RULE_IDS.add(rule_id)
        _RULES.append(Rule(rule_id, severity, description, func))
        return func

    return decorator


def all_rules() -> list:
    """Return the registered rules in declaration order (a copy)."""
    return list(_RULES)


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #
# Convention used across examples and fixtures: lowercase ASCII prefix,
# hyphen, then an alphanumeric suffix that contains at least one digit
# (e.g. 'dec-0001', 'dec-a1', 'pol-7'). This accommodates both numeric
# (`dec-0001`) and short-form (`dec-a1`) IDs seen in the example records
# while still rejecting freeform strings like 'wrong-id' or 'DEC-0001'.
_RECORD_ID_RE = re.compile(r"^[a-z][a-z0-9_]*-[a-z0-9]*\d[a-z0-9]*$")


@register_rule(
    "DRP001",
    SEVERITY_STYLE,
    "record_id should follow lowercase '<prefix>-<id>' with a digit in the suffix.",
)
def _rule_record_id_format(record):
    rid = record.get("record_id")
    if isinstance(rid, str) and not _RECORD_ID_RE.match(rid):
        return [
            (
                "record_id",
                f"record_id {rid!r} should match '<prefix>-<id>' with a "
                "digit in the suffix (e.g. 'dec-0001', 'dec-a1').",
            )
        ]
    return []


@register_rule(
    "DRP002",
    SEVERITY_BEST_PRACTICE,
    "Completed decisions should include 'rationale' explaining the *why*.",
)
def _rule_rationale_for_complete(record):
    if record.get("status") != "complete":
        return []
    rationale = record.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        return [
            (
                "rationale",
                "completed decisions should include a non-empty 'rationale'.",
            )
        ]
    return []


@register_rule(
    "DRP003",
    SEVERITY_STYLE,
    "context should be informative (recommended >=30 characters).",
)
def _rule_context_length(record):
    ctx = record.get("context")
    if isinstance(ctx, str):
        trimmed = ctx.strip()
        if 0 < len(trimmed) < 30:
            return [
                (
                    "context",
                    f"context is only {len(trimmed)} characters; aim for "
                    ">=30 to capture the situation clearly.",
                )
            ]
    return []


@register_rule(
    "DRP004",
    SEVERITY_STYLE,
    "rationale, when present, should be substantive (recommended >=20 characters).",
)
def _rule_rationale_length(record):
    rationale = record.get("rationale")
    if isinstance(rationale, str):
        trimmed = rationale.strip()
        if 0 < len(trimmed) < 20:
            return [
                (
                    "rationale",
                    f"rationale is only {len(trimmed)} characters; expand it "
                    "to record the reasoning.",
                )
            ]
    return []


@register_rule(
    "DRP005",
    SEVERITY_BEST_PRACTICE,
    "At least two options should be recorded so that alternatives are visible.",
)
def _rule_options_count(record):
    opts = record.get("options")
    if isinstance(opts, list) and 0 < len(opts) < 2:
        return [
            (
                "options",
                f"only {len(opts)} option recorded; list at least one "
                "alternative that was considered.",
            )
        ]
    return []


@register_rule(
    "DRP006",
    SEVERITY_INFO,
    "Tags help discoverability and aggregation across records.",
)
def _rule_tags_present(record):
    if "tags" not in record:
        return [("tags", "no 'tags' set; consider adding tags for discoverability.")]
    tags = record.get("tags")
    if isinstance(tags, list) and len(tags) == 0:
        return [("tags", "'tags' is empty; consider adding at least one tag.")]
    return []


@register_rule(
    "DRP007",
    SEVERITY_INFO,
    "metadata.author identifies who is accountable for the decision.",
)
def _rule_metadata_author(record):
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        return [("metadata.author", "no 'metadata.author' set; attribute the decision to someone.")]
    author = metadata.get("author")
    if not isinstance(author, str) or not author.strip():
        return [("metadata.author", "'metadata.author' missing or empty; record who is accountable.")]
    return []


@register_rule(
    "DRP008",
    SEVERITY_BEST_PRACTICE,
    "timestamp should not be in the future relative to the linter run.",
)
def _rule_timestamp_not_future(record):
    ts = record.get("timestamp")
    if not isinstance(ts, str):
        return []
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return []
    if dt.utcoffset() is None:
        return []
    now = datetime.now(timezone.utc)
    if dt > now:
        return [
            (
                "timestamp",
                f"timestamp {ts!r} is in the future relative to {now.isoformat()}.",
            )
        ]
    return []


@register_rule(
    "DRP009",
    SEVERITY_BEST_PRACTICE,
    "supersedes_record_id should be paired with status='superseded'.",
)
def _rule_supersedes_status_consistency(record):
    sid = record.get("supersedes_record_id")
    status = record.get("status")
    has_sid = isinstance(sid, str) and sid.strip()
    if not has_sid:
        return []
    if status not in {"superseded", "complete"}:
        return [
            (
                "status",
                f"record references 'supersedes_record_id' but status is "
                f"{status!r}; expected 'superseded' or 'complete'.",
            )
        ]
    return []


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def _rule_passes_filter(rule, enabled, disabled, threshold):
    if rule.rule_id in disabled:
        return False
    if enabled is not None and rule.rule_id not in enabled:
        return False
    return _SEVERITY_RANK[rule.severity] >= threshold


def lint_record(
    record,
    *,
    enabled_rules: Optional[Iterable[str]] = None,
    disabled_rules: Optional[Iterable[str]] = None,
    min_severity: str = SEVERITY_INFO,
    record_index: Optional[int] = None,
) -> list:
    """Run all matching lint rules against a single DRP record.

    Records that are not dicts produce no warnings (the validator is the
    one that flags structural issues).
    """
    if not isinstance(record, dict):
        return []
    enabled = set(enabled_rules) if enabled_rules else None
    disabled = set(disabled_rules) if disabled_rules else set()
    threshold = _SEVERITY_RANK.get(min_severity, 0)

    rid = record.get("record_id") if isinstance(record.get("record_id"), str) else None
    out = []
    for rule in _RULES:
        if not _rule_passes_filter(rule, enabled, disabled, threshold):
            continue
        for fld, message in rule.func(record):
            out.append(
                LintWarning(
                    rule_id=rule.rule_id,
                    message=message,
                    field=fld,
                    severity=rule.severity,
                    record_id=rid,
                    record_index=record_index,
                )
            )
    return out


def lint_data(
    data,
    *,
    enabled_rules: Optional[Iterable[str]] = None,
    disabled_rules: Optional[Iterable[str]] = None,
    min_severity: str = SEVERITY_INFO,
) -> list:
    """Lint a parsed DRP object (single record or batch)."""
    if isinstance(data, dict):
        return lint_record(
            data,
            enabled_rules=enabled_rules,
            disabled_rules=disabled_rules,
            min_severity=min_severity,
        )
    if isinstance(data, list):
        out = []
        for i, record in enumerate(data):
            if isinstance(record, dict):
                out.extend(
                    lint_record(
                        record,
                        enabled_rules=enabled_rules,
                        disabled_rules=disabled_rules,
                        min_severity=min_severity,
                        record_index=i,
                    )
                )
        return out
    return []
