"""Tests for CLI contract: exit codes, plain-text output, and --json mode."""

import io
import json
import os
import subprocess
import sys

import pytest

from drp_validator import (
    EXIT_INVALID,
    EXIT_OK,
    EXIT_USAGE,
    ValidationError,
    _main,
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, "examples")
FIXTURES = os.path.join(ROOT, "fixtures")


# ---- exit codes --------------------------------------------------------- #

def test_exit_ok_on_valid(capsys):
    rc = _main([os.path.join(EXAMPLES, "minimal_valid.json")])
    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert out.startswith("OK:")


def test_exit_invalid_on_invalid(capsys):
    rc = _main([os.path.join(FIXTURES, "invalid", "duplicate_id.json")])
    assert rc == EXIT_INVALID
    out = capsys.readouterr().out
    assert "FAIL:" in out


def test_exit_usage_on_missing_file(capsys):
    rc = _main(["/no/such/file.json"])
    assert rc == EXIT_USAGE


def test_exit_usage_on_malformed_json(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    rc = _main([str(bad)])
    assert rc == EXIT_USAGE


# ---- --json mode -------------------------------------------------------- #

def _run_main_json(args: list[str], capsys) -> tuple[int, dict]:
    rc = _main(args)
    out = capsys.readouterr().out.strip()
    return rc, json.loads(out)


def test_json_ok_output(capsys):
    rc, payload = _run_main_json(
        [os.path.join(EXAMPLES, "minimal_valid.json"), "--json"], capsys
    )
    assert rc == EXIT_OK
    assert payload["status"] == "OK"
    assert payload["record_count"] == 1
    assert payload["errors"] == []


def test_json_ok_output_batch(capsys):
    rc, payload = _run_main_json(
        [os.path.join(EXAMPLES, "causal_chain.json"), "--json"], capsys
    )
    assert rc == EXIT_OK
    assert payload["status"] == "OK"
    assert payload["record_count"] == 3


def test_json_fail_output(capsys):
    rc, payload = _run_main_json(
        [os.path.join(FIXTURES, "invalid", "duplicate_id.json"), "--json"],
        capsys,
    )
    assert rc == EXIT_INVALID
    assert payload["status"] == "FAIL"
    assert len(payload["errors"]) >= 1
    err = payload["errors"][0]
    assert err["layer"] == "graph"
    assert err["field"] == "record_id"
    assert err["record_id"] == "dup-1"
    assert "duplicate" in err["message"]


def test_json_fail_output_cycle(capsys):
    rc, payload = _run_main_json(
        [os.path.join(FIXTURES, "invalid", "cyclic_graph.json"), "--json"],
        capsys,
    )
    assert rc == EXIT_INVALID
    assert payload["status"] == "FAIL"
    assert any("cycle detected" in e["message"] for e in payload["errors"])


def test_json_error_on_missing_file(capsys):
    # CLI-level errors go to stderr, even in --json mode, so stdout stays
    # reserved for validation output (OK / FAIL payloads). See
    # docs/VALIDATION.md §4.
    rc = _main(["/no/such/file.json", "--json"])
    captured = capsys.readouterr()
    assert rc == EXIT_USAGE
    assert captured.out == ""
    payload = json.loads(captured.err.strip())
    assert payload["status"] == "ERROR"
    assert "file not found" in payload["message"]


def test_json_error_on_malformed_json(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    rc = _main([str(bad), "--json"])
    captured = capsys.readouterr()
    assert rc == EXIT_USAGE
    assert captured.out == ""
    payload = json.loads(captured.err.strip())
    assert payload["status"] == "ERROR"
    assert "invalid JSON" in payload["message"]


# ---- ValidationError.to_dict() ----------------------------------------- #

def test_validation_error_to_dict_shape():
    err = ValidationError(
        layer="graph", record_id="x", field="parent_record_ids",
        message="test",
    )
    d = err.to_dict()
    assert d == {
        "layer": "graph",
        "record_id": "x",
        "field": "parent_record_ids",
        "message": "test",
    }


# ---- CLI subprocess smoke test ----------------------------------------- #

def test_cli_script_runs_end_to_end():
    """Run scripts/drp-validate as a subprocess to confirm it works
    as a real executable, not just as an imported module."""
    script = os.path.join(ROOT, "scripts", "drp-validate")
    example = os.path.join(EXAMPLES, "minimal_valid.json")
    result = subprocess.run(
        [sys.executable, script, example, "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode == EXIT_OK
    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "OK"
