"""End-to-end tests for the reference validator."""

import copy
import json
import os

import pytest

from drp_validator import validate, validate_file


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "fixtures")
EXAMPLES = os.path.join(ROOT, "examples")


def _base() -> dict:
    return {
        "record_id": "t-1",
        "timestamp": "2026-04-17T10:00:00Z",
        "context": "A context.",
        "decision": "A decision.",
        "options": ["opt"],
        "status": "complete",
    }


# --------------------------------------------------------------------------- #
# Positive cases
# --------------------------------------------------------------------------- #

def test_valid_single_record():
    assert validate(_base()).ok


def test_valid_batch():
    rec1 = _base()
    rec2 = _base()
    rec2["record_id"] = "t-2"
    rec2["timestamp"] = "2026-04-17T11:00:00Z"
    result = validate([rec1, rec2])
    assert result.ok, [e.format() for e in result.errors]


def test_valid_graph_fixture():
    result = validate_file(os.path.join(FIXTURES, "valid", "graph.json"))
    assert result.ok, [e.format() for e in result.errors]


def test_valid_basic_fixture():
    result = validate_file(os.path.join(FIXTURES, "valid", "basic.json"))
    assert result.ok, [e.format() for e in result.errors]


def test_examples_all_valid():
    for name in (
        "minimal_valid.json",
        "complete_record.json",
        "causal_chain.json",
        "superseded_chain.json",
    ):
        path = os.path.join(EXAMPLES, name)
        result = validate_file(path)
        assert result.ok, f"{name}: {[e.format() for e in result.errors]}"


# --------------------------------------------------------------------------- #
# Invariant-targeted negative tests
# --------------------------------------------------------------------------- #

def _expect_fail(data, layer=None, field=None, needle=None):
    result = validate(data)
    assert not result.ok, "expected validation to fail"
    if layer is not None:
        assert any(e.layer == layer for e in result.errors), (
            f"expected a {layer} error, got: {[e.format() for e in result.errors]}"
        )
    if field is not None:
        assert any(e.field == field for e in result.errors), (
            f"expected an error on field {field}, got: "
            f"{[e.format() for e in result.errors]}"
        )
    if needle is not None:
        blob = " | ".join(e.format() for e in result.errors)
        assert needle in blob, f"expected '{needle}' in: {blob}"


def test_duplicate_ids():
    result = validate_file(os.path.join(FIXTURES, "invalid", "duplicate_id.json"))
    assert not result.ok
    assert any(e.layer == "graph" and e.field == "record_id" for e in result.errors)


def test_orphan_parent():
    result = validate_file(
        os.path.join(FIXTURES, "invalid", "orphan_reference.json")
    )
    assert not result.ok
    assert any("parent reference" in e.message for e in result.errors)


def test_orphan_child():
    r1 = _base()
    r1["record_id"] = "o-1"
    r1["child_record_ids"] = ["does-not-exist"]
    _expect_fail([r1], layer="graph", needle="child reference")


def test_broken_bidirectional_links():
    result = validate_file(
        os.path.join(FIXTURES, "invalid", "broken_bidirectional_links.json")
    )
    assert not result.ok
    assert any("does not list" in e.message for e in result.errors)


def test_invalid_timestamp():
    result = validate_file(os.path.join(FIXTURES, "invalid", "bad_timestamp.json"))
    assert not result.ok
    assert any(e.field == "timestamp" for e in result.errors)


def test_empty_context():
    result = validate_file(os.path.join(FIXTURES, "invalid", "empty_context.json"))
    assert not result.ok
    assert any(e.field == "context" for e in result.errors)


def test_empty_decision():
    result = validate_file(os.path.join(FIXTURES, "invalid", "empty_decision.json"))
    assert not result.ok
    assert any(e.field == "decision" for e in result.errors)


def test_empty_options():
    result = validate_file(os.path.join(FIXTURES, "invalid", "empty_options.json"))
    assert not result.ok
    assert any(e.field == "options" for e in result.errors)


def test_impact_true_rejected():
    r = _base()
    r["impact"] = True
    _expect_fail(r, layer="schema", field="impact")


def test_impact_false_rejected():
    r = _base()
    r["impact"] = False
    _expect_fail(r, layer="schema", field="impact")


def test_impact_out_of_range_rejected():
    r = _base()
    r["impact"] = 2
    _expect_fail(r, layer="schema", field="impact")


def test_impact_valid_values():
    for v in (-1, 0, 1, None):
        r = _base()
        r["impact"] = v
        assert validate(r).ok, f"impact={v!r} should validate"


def test_superseded_without_supersedes_record_id():
    result = validate_file(
        os.path.join(FIXTURES, "invalid", "broken_superseded.json")
    )
    assert not result.ok
    assert any(e.field == "supersedes_record_id" for e in result.errors)


def test_superseded_with_unknown_supersedes_record_id():
    r = _base()
    r["status"] = "superseded"
    r["supersedes_record_id"] = "ghost"
    _expect_fail(r, layer="graph", needle="supersedes reference 'ghost'")


def test_superseded_valid_with_resolved_reference():
    r1 = _base()
    r1["record_id"] = "old"
    r1["timestamp"] = "2026-04-01T10:00:00Z"
    r2 = _base()
    r2["record_id"] = "new"
    r2["timestamp"] = "2026-04-17T10:00:00Z"
    r2["status"] = "superseded"
    r2["supersedes_record_id"] = "old"
    assert validate([r1, r2]).ok


def test_parent_after_child_timestamp():
    result = validate_file(
        os.path.join(FIXTURES, "invalid", "parent_after_child_timestamp.json")
    )
    assert not result.ok
    assert any("later than child" in e.message for e in result.errors)


def test_self_supersession_rejected():
    r = _base()
    r["status"] = "superseded"
    r["supersedes_record_id"] = r["record_id"]
    _expect_fail(r, layer="semantic", needle="must not supersede itself")


def test_self_parent_rejected():
    r = _base()
    r["parent_record_ids"] = [r["record_id"]]
    _expect_fail(r, layer="semantic", field="parent_record_ids")


def test_unknown_top_level_field_rejected():
    r = _base()
    r["extra_field"] = "nope"
    _expect_fail(r, layer="schema", needle="unknown top-level field")


def test_missing_required_field_rejected():
    r = _base()
    del r["decision"]
    _expect_fail(r, layer="schema", field="decision", needle="required")


def test_superseding_earlier_than_superseded_rejected():
    r1 = _base()
    r1["record_id"] = "old"
    r1["timestamp"] = "2026-04-17T12:00:00Z"
    r2 = _base()
    r2["record_id"] = "new"
    r2["timestamp"] = "2026-04-17T10:00:00Z"
    r2["status"] = "superseded"
    r2["supersedes_record_id"] = "old"
    _expect_fail([r1, r2], layer="graph", needle="earlier than superseded")


# --------------------------------------------------------------------------- #
# Edge cases (audit follow-up)
# --------------------------------------------------------------------------- #

def test_cycle_with_equal_timestamps_rejected():
    """G6: the acyclicity check must catch cycles even when G4 is satisfied
    vacuously because all edges have equal timestamps."""
    ts = "2026-04-17T10:00:00Z"
    a = _base()
    a["record_id"] = "a"
    a["timestamp"] = ts
    a["parent_record_ids"] = ["b"]
    a["child_record_ids"] = ["b"]
    b = _base()
    b["record_id"] = "b"
    b["timestamp"] = ts
    b["parent_record_ids"] = ["a"]
    b["child_record_ids"] = ["a"]
    _expect_fail([a, b], layer="graph", needle="cycle detected")


def test_duplicate_parent_ids_rejected():
    r1 = _base()
    r1["record_id"] = "p"
    r1["timestamp"] = "2026-04-17T10:00:00Z"
    r1["child_record_ids"] = ["c"]
    r2 = _base()
    r2["record_id"] = "c"
    r2["timestamp"] = "2026-04-17T11:00:00Z"
    r2["parent_record_ids"] = ["p", "p"]
    _expect_fail(
        [r1, r2],
        layer="schema",
        field="parent_record_ids",
        needle="duplicate entry",
    )


def test_duplicate_child_ids_rejected():
    r1 = _base()
    r1["record_id"] = "p"
    r1["timestamp"] = "2026-04-17T10:00:00Z"
    r1["child_record_ids"] = ["c", "c"]
    r2 = _base()
    r2["record_id"] = "c"
    r2["timestamp"] = "2026-04-17T11:00:00Z"
    r2["parent_record_ids"] = ["p"]
    _expect_fail(
        [r1, r2],
        layer="schema",
        field="child_record_ids",
        needle="duplicate entry",
    )


@pytest.mark.parametrize("field_name", ["record_id", "context", "decision"])
def test_whitespace_only_strings_rejected(field_name):
    r = _base()
    r[field_name] = "   "
    _expect_fail(r, layer="semantic", field=field_name)


def test_minus_zero_offset_rejected():
    """Spec §3: -00:00 is not an accepted UTC offset."""
    r = _base()
    r["timestamp"] = "2026-04-17T10:00:00-00:00"
    _expect_fail(r, layer="semantic", field="timestamp")


def test_plus_zero_offset_accepted():
    r = _base()
    r["timestamp"] = "2026-04-17T10:00:00+00:00"
    assert validate(r).ok


def test_non_utc_offset_rejected():
    r = _base()
    r["timestamp"] = "2026-04-17T10:00:00+02:00"
    _expect_fail(r, layer="semantic", field="timestamp")


def test_supersedes_on_non_superseded_status_allowed():
    """S6: supersedes_record_id may be present on a non-superseded record."""
    r1 = _base()
    r1["record_id"] = "old"
    r1["timestamp"] = "2026-04-17T10:00:00Z"
    r2 = _base()
    r2["record_id"] = "draft-candidate"
    r2["timestamp"] = "2026-04-17T11:00:00Z"
    r2["status"] = "draft"
    r2["supersedes_record_id"] = "old"
    assert validate([r1, r2]).ok


def test_two_records_supersede_same_ancestor_allowed():
    """S7: DRP permits multiple candidate successors of the same ancestor."""
    old = _base()
    old["record_id"] = "old"
    old["timestamp"] = "2026-04-17T10:00:00Z"
    a = _base()
    a["record_id"] = "succ-a"
    a["timestamp"] = "2026-04-17T11:00:00Z"
    a["status"] = "superseded"
    a["supersedes_record_id"] = "old"
    b = _base()
    b["record_id"] = "succ-b"
    b["timestamp"] = "2026-04-17T12:00:00Z"
    b["status"] = "superseded"
    b["supersedes_record_id"] = "old"
    assert validate([old, a, b]).ok


def test_batch_size_limit_enforced(monkeypatch):
    import drp_validator
    monkeypatch.setattr(drp_validator, "MAX_BATCH_SIZE", 2)
    batch = [_base() for _ in range(3)]
    for i, r in enumerate(batch):
        r["record_id"] = f"r-{i}"
    result = drp_validator.validate(batch)
    assert not result.ok
    assert any("batch size" in e.message for e in result.errors)


def test_oversize_string_rejected(monkeypatch):
    import drp_validator
    monkeypatch.setattr(drp_validator, "MAX_STRING_LENGTH", 16)
    r = _base()
    r["context"] = "x" * 64
    result = drp_validator.validate(r)
    assert not result.ok
    assert any(e.field == "context" and "exceeds limit" in e.message
               for e in result.errors)


def test_oversize_array_rejected(monkeypatch):
    import drp_validator
    monkeypatch.setattr(drp_validator, "MAX_ARRAY_LENGTH", 3)
    r = _base()
    r["options"] = ["a", "b", "c", "d"]
    result = drp_validator.validate(r)
    assert not result.ok
    assert any(e.field == "options" and "exceeds limit" in e.message
               for e in result.errors)


def test_cli_stderr_routing_json(tmp_path, capsys):
    """CLI-level errors go to stderr in --json mode as well as text mode."""
    import drp_validator
    missing = str(tmp_path / "nope.json")
    rc = drp_validator._main([missing, "--json"])
    captured = capsys.readouterr()
    assert rc == drp_validator.EXIT_USAGE
    assert captured.out == ""
    assert '"status": "ERROR"' in captured.err


def test_cli_validation_output_goes_to_stdout(tmp_path, capsys):
    import drp_validator
    p = tmp_path / "rec.json"
    p.write_text(json.dumps(_base()))
    rc = drp_validator._main([str(p), "--json"])
    captured = capsys.readouterr()
    assert rc == drp_validator.EXIT_OK
    assert '"status": "OK"' in captured.out
    assert captured.err == ""


def test_env_int_warning_on_non_integer(monkeypatch, capsys):
    import drp_validator
    monkeypatch.setenv("DRP_MAX_BATCH_SIZE", "not_a_number")
    # Force re-evaluation of the limit (in real code, it's evaluated at import)
    # We'll call _env_int directly instead.
    val = drp_validator._env_int("DRP_MAX_BATCH_SIZE", 42)
    assert val == 42
    captured = capsys.readouterr()
    assert "warning" in captured.err.lower()
    assert "not_a_number" in captured.err


def test_env_int_warning_on_non_positive(monkeypatch, capsys):
    import drp_validator
    val = drp_validator._env_int("DRP_MAX_BATCH_SIZE", 42)
    monkeypatch.setenv("DRP_MAX_BATCH_SIZE", "0")
    val = drp_validator._env_int("DRP_MAX_BATCH_SIZE", 42)
    assert val == 42
    captured = capsys.readouterr()
    assert "warning" in captured.err.lower()
    assert "not positive" in captured.err.lower()
