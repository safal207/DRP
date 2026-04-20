"""Tests for scripts/run_benchmark.py.

The benchmark runner is not part of the protocol: it wraps the public
validator API to summarize outcomes over the auditability pack. These
tests check the runner's CLI contract (exit codes, JSON shape) and its
category-expectation matching. They do not re-test validator behavior,
which lives in test_validator.py and test_invariants.py.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")

# Make scripts/ importable so we can call main() in-process.
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import run_benchmark  # noqa: E402


PACK = os.path.join(ROOT, "benchmark", "drp_auditability_pack")


# ---- smoke: runner on the real pack ------------------------------------ #

def test_runner_smoke_on_real_pack(capsys):
    rc = run_benchmark.main([])
    out = capsys.readouterr().out
    assert rc == run_benchmark.EXIT_OK
    assert "SUMMARY: all categories matched" in out


def test_runner_json_output_shape(capsys):
    rc = run_benchmark.main(["--json"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert rc == run_benchmark.EXIT_OK
    assert payload["pack"] == "drp_auditability_pack"
    assert payload["all_matched"] is True
    names = [c["name"] for c in payload["categories"]]
    assert names == ["valid", "invalid", "ambiguous", "comparison"]
    for cat in payload["categories"]:
        assert cat["matches_expectation"] is True
        assert len(cat["files"]) > 0
        for f in cat["files"]:
            assert "path" in f
            assert "ok" in f
            assert "error_count" in f
            # non-verbose: no per-file error messages
            assert "errors" not in f


def test_runner_verbose_adds_error_messages(capsys):
    rc = run_benchmark.main(["--json", "--verbose"])
    payload = json.loads(capsys.readouterr().out.strip())
    assert rc == run_benchmark.EXIT_OK
    invalid_cat = next(c for c in payload["categories"] if c["name"] == "invalid")
    for f in invalid_cat["files"]:
        assert "errors" in f
        assert len(f["errors"]) >= 1


# ---- bad --pack argument ----------------------------------------------- #

def test_runner_errors_on_nonexistent_pack(capsys):
    rc = run_benchmark.main(["--pack", "/no/such/pack"])
    err = capsys.readouterr().err
    assert rc == run_benchmark.EXIT_USAGE
    assert "does not exist" in err


def test_runner_errors_on_pack_that_is_a_file(tmp_path, capsys):
    f = tmp_path / "not_a_dir.json"
    f.write_text("[]")
    rc = run_benchmark.main(["--pack", str(f)])
    err = capsys.readouterr().err
    assert rc == run_benchmark.EXIT_USAGE
    assert "not a directory" in err


# ---- expectation matching --------------------------------------------- #

def test_runner_flags_mismatch_when_valid_fixture_is_broken(tmp_path, capsys):
    """
    Build a synthetic pack where valid/ contains a fixture that does
    not validate; the runner must report mismatch and exit 1.
    """
    pack = tmp_path / "pack"
    (pack / "valid").mkdir(parents=True)
    (pack / "invalid").mkdir()
    (pack / "ambiguous").mkdir()
    (pack / "comparison").mkdir()

    # A record missing the required 'options' field: should not validate.
    bad = [{
        "record_id": "r1",
        "timestamp": "2026-04-14T10:00:00Z",
        "context": "test",
        "decision": "test",
        "status": "complete",
    }]
    (pack / "valid" / "broken.json").write_text(json.dumps(bad))

    rc = run_benchmark.main(["--pack", str(pack)])
    out = capsys.readouterr().out
    assert rc == run_benchmark.EXIT_MISMATCH
    assert "MISMATCH" in out


def test_runner_flags_mismatch_when_invalid_fixture_validates(tmp_path, capsys):
    """
    Inverse: invalid/ contains a fixture that actually validates; the
    runner must report mismatch.
    """
    pack = tmp_path / "pack"
    (pack / "valid").mkdir(parents=True)
    (pack / "invalid").mkdir()
    (pack / "ambiguous").mkdir()
    (pack / "comparison").mkdir()

    good = [{
        "record_id": "r1",
        "timestamp": "2026-04-14T10:00:00Z",
        "context": "a well-formed record living in the invalid/ bucket by mistake",
        "decision": "noop",
        "options": ["a", "b"],
        "status": "complete",
    }]
    (pack / "invalid" / "actually_valid.json").write_text(json.dumps(good))

    rc = run_benchmark.main(["--pack", str(pack)])
    out = capsys.readouterr().out
    assert rc == run_benchmark.EXIT_MISMATCH
    assert "MISMATCH" in out


def test_runner_warns_on_unknown_category_directory(tmp_path, capsys):
    pack = tmp_path / "pack"
    (pack / "valid").mkdir(parents=True)
    (pack / "invalid").mkdir()
    (pack / "ambiguous").mkdir()
    (pack / "comparison").mkdir()
    (pack / "valld").mkdir()  # typo

    rc = run_benchmark.main(["--pack", str(pack)])
    err = capsys.readouterr().err
    # No fixtures present, so expectations are trivially met (all_matched).
    assert rc == run_benchmark.EXIT_OK
    assert "unknown category directory" in err
    assert "valld" in err


# ---- subprocess smoke (runner works as a real script) ------------------ #

def test_runner_script_runs_end_to_end():
    script = os.path.join(SCRIPTS, "run_benchmark.py")
    result = subprocess.run(
        [sys.executable, script, "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout.strip())
    assert payload["all_matched"] is True
