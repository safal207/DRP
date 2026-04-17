"""Focused tests that each invariant from docs/SPEC.md is enforced.

These tests are intentionally granular: one invariant per test, using
the smallest possible input that isolates it.
"""

import copy
import os

from drp_validator import validate, validate_file

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "fixtures")


def _base() -> dict:
    return {
        "record_id": "inv-1",
        "timestamp": "2026-04-17T10:00:00Z",
        "context": "ctx",
        "decision": "dec",
        "options": ["a"],
        "status": "complete",
    }


# ---- §5 field-level invariants ------------------------------------------- #

def test_inv_record_id_nonempty_trimmed():
    r = _base()
    r["record_id"] = "   "
    result = validate(r)
    assert any(e.field == "record_id" for e in result.errors)


def test_inv_context_nonempty_trimmed():
    r = _base()
    r["context"] = ""
    result = validate(r)
    assert any(e.field == "context" for e in result.errors)


def test_inv_decision_nonempty_trimmed():
    r = _base()
    r["decision"] = "  \t "
    result = validate(r)
    assert any(e.field == "decision" for e in result.errors)


def test_inv_options_nonempty():
    r = _base()
    r["options"] = []
    result = validate(r)
    assert any(e.field == "options" for e in result.errors)


def test_inv_options_element_must_be_string():
    r = _base()
    r["options"] = [123]
    result = validate(r)
    assert any(e.field == "options[0]" for e in result.errors)


def test_inv_options_element_nonempty_trimmed():
    r = _base()
    r["options"] = ["  "]
    result = validate(r)
    assert any(e.field == "options[0]" for e in result.errors)


def test_inv_timestamp_must_be_iso_utc():
    r = _base()
    r["timestamp"] = "not-a-date"
    result = validate(r)
    assert any(e.field == "timestamp" for e in result.errors)


def test_inv_timestamp_offset_non_utc_rejected():
    r = _base()
    r["timestamp"] = "2026-04-17T10:00:00+02:00"
    result = validate(r)
    assert any(e.field == "timestamp" for e in result.errors)


def test_inv_status_enum():
    r = _base()
    r["status"] = "active"
    result = validate(r)
    assert any(e.field == "status" for e in result.errors)


def test_inv_impact_enum_rejects_42():
    r = _base()
    r["impact"] = 42
    assert any(e.field == "impact" for e in validate(r).errors)


def test_inv_impact_rejects_true():
    r = _base()
    r["impact"] = True
    assert any(e.field == "impact" for e in validate(r).errors)


def test_inv_impact_rejects_false():
    r = _base()
    r["impact"] = False
    assert any(e.field == "impact" for e in validate(r).errors)


def test_inv_impact_accepts_allowed_values():
    for v in (-1, 0, 1, None):
        r = _base()
        r["impact"] = v
        assert validate(r).ok


# ---- §7 graph invariants ------------------------------------------------- #

def test_inv_record_id_unique_in_batch():
    r1, r2 = _base(), _base()
    r2["timestamp"] = "2026-04-17T11:00:00Z"
    result = validate([r1, r2])
    assert any(
        e.layer == "graph" and e.field == "record_id" for e in result.errors
    )


def test_inv_parent_must_resolve():
    r = _base()
    r["parent_record_ids"] = ["nope"]
    result = validate(r)
    assert any(e.field == "parent_record_ids" for e in result.errors)


def test_inv_child_must_resolve():
    r = _base()
    r["child_record_ids"] = ["nope"]
    result = validate(r)
    assert any(e.field == "child_record_ids" for e in result.errors)


def test_inv_bidirectional_parent_missing_on_parent():
    parent = _base()
    parent["record_id"] = "p"
    parent["timestamp"] = "2026-04-01T10:00:00Z"
    child = _base()
    child["record_id"] = "c"
    child["timestamp"] = "2026-04-02T10:00:00Z"
    child["parent_record_ids"] = ["p"]
    # parent omits child_record_ids, so the link is one-sided.
    result = validate([parent, child])
    assert not result.ok
    assert any("does not list" in e.message for e in result.errors)


def test_inv_bidirectional_child_missing_on_child():
    parent = _base()
    parent["record_id"] = "p"
    parent["timestamp"] = "2026-04-01T10:00:00Z"
    parent["child_record_ids"] = ["c"]
    child = _base()
    child["record_id"] = "c"
    child["timestamp"] = "2026-04-02T10:00:00Z"
    # child omits parent_record_ids.
    result = validate([parent, child])
    assert not result.ok
    assert any("does not list" in e.message for e in result.errors)


def test_inv_parent_timestamp_not_later_than_child():
    parent = _base()
    parent["record_id"] = "p"
    parent["timestamp"] = "2026-05-01T10:00:00Z"
    parent["child_record_ids"] = ["c"]
    child = _base()
    child["record_id"] = "c"
    child["timestamp"] = "2026-04-01T10:00:00Z"
    child["parent_record_ids"] = ["p"]
    result = validate([parent, child])
    assert not result.ok
    assert any("later than child" in e.message for e in result.errors)


def test_inv_no_self_parent():
    r = _base()
    r["parent_record_ids"] = [r["record_id"]]
    result = validate(r)
    assert any(
        e.layer == "semantic" and e.field == "parent_record_ids"
        for e in result.errors
    )


def test_inv_no_self_child():
    r = _base()
    r["child_record_ids"] = [r["record_id"]]
    result = validate(r)
    assert any(
        e.layer == "semantic" and e.field == "child_record_ids"
        for e in result.errors
    )


# ---- §8 supersession invariants ----------------------------------------- #

def test_inv_superseded_requires_supersedes_record_id():
    r = _base()
    r["status"] = "superseded"
    result = validate(r)
    assert any(
        e.layer == "semantic" and e.field == "supersedes_record_id"
        for e in result.errors
    )


def test_inv_supersedes_reference_must_resolve():
    r = _base()
    r["status"] = "superseded"
    r["supersedes_record_id"] = "ghost"
    result = validate(r)
    assert any(
        e.layer == "graph" and e.field == "supersedes_record_id"
        for e in result.errors
    )


def test_inv_supersedes_self_rejected():
    r = _base()
    r["status"] = "superseded"
    r["supersedes_record_id"] = r["record_id"]
    result = validate(r)
    assert any("must not supersede itself" in e.message for e in result.errors)


def test_inv_supersedes_timestamp_ordering():
    old = _base()
    old["record_id"] = "old"
    old["timestamp"] = "2026-04-17T12:00:00Z"
    new = _base()
    new["record_id"] = "new"
    new["timestamp"] = "2026-04-17T09:00:00Z"
    new["status"] = "superseded"
    new["supersedes_record_id"] = "old"
    result = validate([old, new])
    assert not result.ok
    assert any("earlier than superseded" in e.message for e in result.errors)


# ---- §7 G6 acyclicity ---------------------------------------------------- #

def test_inv_two_node_cycle_with_equal_timestamps_rejected():
    """The critical case: G4 (timestamp ordering) cannot catch a cycle where
    both nodes share the same timestamp. G6 must catch it via DFS."""
    result = validate_file(
        os.path.join(FIXTURES, "invalid", "cyclic_graph.json")
    )
    assert not result.ok
    assert any("cycle detected" in e.message for e in result.errors)


def test_inv_two_node_cycle_inline():
    """Same two-node cycle constructed inline, independent of fixtures."""
    ts = "2026-04-17T10:00:00Z"
    a = {
        "record_id": "a",
        "timestamp": ts,
        "context": "ctx",
        "decision": "dec",
        "options": ["x"],
        "status": "complete",
        "parent_record_ids": ["b"],
        "child_record_ids": ["b"],
    }
    b = {
        "record_id": "b",
        "timestamp": ts,
        "context": "ctx",
        "decision": "dec",
        "options": ["x"],
        "status": "complete",
        "parent_record_ids": ["a"],
        "child_record_ids": ["a"],
    }
    result = validate([a, b])
    assert not result.ok
    assert any("cycle detected" in e.message for e in result.errors)


def test_inv_three_node_cycle_rejected():
    """A longer cycle: A->B->C->A. All timestamps are equal so G4 (parent <=
    child) is satisfied by every edge, meaning only G6 catches the cycle."""
    t1 = "2026-04-01T10:00:00Z"
    t2 = "2026-04-01T10:00:00Z"  # equal, so G4 allows C->A
    t3 = "2026-04-01T10:00:00Z"
    a = {
        "record_id": "ca",
        "timestamp": t1,
        "context": "c", "decision": "d", "options": ["x"],
        "status": "complete",
        "parent_record_ids": ["cc"],
        "child_record_ids": ["cb"],
    }
    b = {
        "record_id": "cb",
        "timestamp": t2,
        "context": "c", "decision": "d", "options": ["x"],
        "status": "complete",
        "parent_record_ids": ["ca"],
        "child_record_ids": ["cc"],
    }
    c = {
        "record_id": "cc",
        "timestamp": t3,
        "context": "c", "decision": "d", "options": ["x"],
        "status": "complete",
        "parent_record_ids": ["cb"],
        "child_record_ids": ["ca"],
    }
    result = validate([a, b, c])
    assert not result.ok
    assert any("cycle detected" in e.message for e in result.errors)


def test_inv_acyclic_graph_passes():
    """Linear chain A->B->C is acyclic and should pass."""
    a = {
        "record_id": "la",
        "timestamp": "2026-04-01T10:00:00Z",
        "context": "c", "decision": "d", "options": ["x"],
        "status": "complete",
        "child_record_ids": ["lb"],
    }
    b = {
        "record_id": "lb",
        "timestamp": "2026-04-02T10:00:00Z",
        "context": "c", "decision": "d", "options": ["x"],
        "status": "complete",
        "parent_record_ids": ["la"],
        "child_record_ids": ["lc"],
    }
    c = {
        "record_id": "lc",
        "timestamp": "2026-04-03T10:00:00Z",
        "context": "c", "decision": "d", "options": ["x"],
        "status": "complete",
        "parent_record_ids": ["lb"],
    }
    result = validate([a, b, c])
    assert result.ok, [e.format() for e in result.errors]
