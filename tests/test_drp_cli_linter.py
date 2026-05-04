"""Tests for the DRP CLI (``drp_cli``) and lint engine (``linter``)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from drp_cli import (
    EXIT_INVALID,
    EXIT_LINT_FAIL,
    EXIT_OK,
    EXIT_USAGE,
    __version__,
    _expand_paths,
    _normalize_argv,
    _Style,
    _supports_color,
    main,
)
from linter import (
    ALL_SEVERITIES,
    SEVERITY_BEST_PRACTICE,
    SEVERITY_INFO,
    SEVERITY_STYLE,
    LintWarning,
    Rule,
    all_rules,
    lint_data,
    lint_record,
    register_rule,
)


# --------------------------------------------------------------------------- #
# Path helpers
# --------------------------------------------------------------------------- #
def test_expand_paths_with_single_file(tmp_path):
    file_path = tmp_path / "record.json"
    file_path.write_text("{}", encoding="utf-8")
    assert str(file_path) in _expand_paths([str(file_path)])


def test_expand_paths_with_glob(tmp_path):
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "b.json").write_text("{}", encoding="utf-8")
    assert len(_expand_paths([str(tmp_path / "*.json")])) == 2


def test_expand_paths_passes_through_unmatched_pattern(tmp_path):
    pattern = str(tmp_path / "nope-*.json")
    assert _expand_paths([pattern]) == [pattern]


def test_normalize_argv_inserts_validate_for_bare_path():
    assert _normalize_argv(["foo.json"]) == ["validate", "foo.json"]


def test_normalize_argv_preserves_subcommand_and_flags():
    assert _normalize_argv(["lint", "x"]) == ["lint", "x"]
    assert _normalize_argv(["--version"]) == ["--version"]
    assert _normalize_argv([]) == []


# --------------------------------------------------------------------------- #
# Rule registry
# --------------------------------------------------------------------------- #
def test_all_rules_have_expected_ids_and_severities():
    rules = all_rules()
    ids = {r.rule_id for r in rules}
    assert {"DRP001", "DRP002", "DRP003", "DRP004", "DRP005", "DRP006", "DRP007", "DRP008", "DRP009"} <= ids
    for r in rules:
        assert r.severity in ALL_SEVERITIES


def test_register_rule_rejects_unknown_severity():
    with pytest.raises(ValueError):
        @register_rule("ZZZZZZ", "nonsense", "x")
        def _r(_record):
            return []


def test_register_rule_is_idempotent_for_same_id():
    """Re-registering the same ID must not double-fire warnings (e.g. on test-time re-imports)."""
    initial = len(all_rules())

    @register_rule("DRP001", SEVERITY_STYLE, "duplicate")
    def _again(_record):
        return [("record_id", "duplicate")]

    assert len(all_rules()) == initial


# --------------------------------------------------------------------------- #
# Individual rules
# --------------------------------------------------------------------------- #
def test_drp001_record_id_format():
    assert any(w.rule_id == "DRP001" for w in lint_record({"record_id": "wrong-id"}))
    assert any(w.rule_id == "DRP001" for w in lint_record({"record_id": "DEC-0001"}))
    assert not any(w.rule_id == "DRP001" for w in lint_record({"record_id": "dec-0001"}))


def test_drp002_rationale_for_complete_decisions():
    triggers = lint_record({"record_id": "dec-0001", "status": "complete"})
    assert any(w.rule_id == "DRP002" for w in triggers)
    silent = lint_record(
        {"record_id": "dec-0001", "status": "complete", "rationale": "because"}
    )
    assert not any(w.rule_id == "DRP002" for w in silent)


def test_drp002_does_not_fire_for_non_complete_status():
    silent = lint_record({"record_id": "dec-0001", "status": "draft"})
    assert not any(w.rule_id == "DRP002" for w in silent)


def test_drp003_short_context_warns():
    short = lint_record({"record_id": "dec-0001", "context": "too short"})
    assert any(w.rule_id == "DRP003" for w in short)
    long = lint_record({"record_id": "dec-0001", "context": "x" * 50})
    assert not any(w.rule_id == "DRP003" for w in long)


def test_drp004_short_rationale_warns():
    warns = lint_record({"record_id": "dec-0001", "rationale": "k"})
    assert any(w.rule_id == "DRP004" for w in warns)
    silent = lint_record({"record_id": "dec-0001", "rationale": "x" * 50})
    assert not any(w.rule_id == "DRP004" for w in silent)


def test_drp005_single_option_warns():
    warns = lint_record({"record_id": "dec-0001", "options": ["only one"]})
    assert any(w.rule_id == "DRP005" for w in warns)
    silent = lint_record({"record_id": "dec-0001", "options": ["a", "b"]})
    assert not any(w.rule_id == "DRP005" for w in silent)


def test_drp005_zero_options_does_not_warn():
    """Empty options is a validator-level error, not a lint concern."""
    silent = lint_record({"record_id": "dec-0001", "options": []})
    assert not any(w.rule_id == "DRP005" for w in silent)


def test_drp006_missing_or_empty_tags_warns():
    assert any(w.rule_id == "DRP006" for w in lint_record({"record_id": "dec-0001"}))
    assert any(w.rule_id == "DRP006" for w in lint_record({"record_id": "dec-0001", "tags": []}))
    assert not any(w.rule_id == "DRP006" for w in lint_record({"record_id": "dec-0001", "tags": ["x"]}))


def test_drp007_metadata_author_warns():
    assert any(w.rule_id == "DRP007" for w in lint_record({"record_id": "dec-0001"}))
    assert any(
        w.rule_id == "DRP007"
        for w in lint_record({"record_id": "dec-0001", "metadata": {"author": ""}})
    )
    assert not any(
        w.rule_id == "DRP007"
        for w in lint_record({"record_id": "dec-0001", "metadata": {"author": "alice"}})
    )


def test_drp008_future_timestamp_warns():
    future = (
        (datetime.now(timezone.utc) + timedelta(days=365))
        .isoformat()
        .replace("+00:00", "Z")
    )
    assert any(
        w.rule_id == "DRP008"
        for w in lint_record({"record_id": "dec-0001", "timestamp": future})
    )


def test_drp008_past_timestamp_silent():
    past = "2020-01-01T00:00:00Z"
    assert not any(
        w.rule_id == "DRP008"
        for w in lint_record({"record_id": "dec-0001", "timestamp": past})
    )


def test_drp008_invalid_timestamp_silent():
    """Validator owns ISO format checks; the linter must not duplicate them."""
    assert not any(
        w.rule_id == "DRP008"
        for w in lint_record({"record_id": "dec-0001", "timestamp": "not-a-date"})
    )


def test_drp009_supersedes_status_consistency():
    bad = lint_record(
        {
            "record_id": "dec-0001",
            "supersedes_record_id": "dec-0000",
            "status": "draft",
        }
    )
    assert any(w.rule_id == "DRP009" for w in bad)
    good = lint_record(
        {
            "record_id": "dec-0001",
            "supersedes_record_id": "dec-0000",
            "status": "superseded",
        }
    )
    assert not any(w.rule_id == "DRP009" for w in good)


# --------------------------------------------------------------------------- #
# Filtering
# --------------------------------------------------------------------------- #
def test_severity_filter_drops_lower_severities():
    record = {"record_id": "dec-0001"}
    info = lint_record(record, min_severity=SEVERITY_INFO)
    high = lint_record(record, min_severity=SEVERITY_BEST_PRACTICE)
    assert len(high) <= len(info)
    for w in high:
        assert w.severity == SEVERITY_BEST_PRACTICE


def test_enabled_rules_restricts_to_listed_ids():
    record = {"record_id": "wrong-id"}
    only = lint_record(record, enabled_rules={"DRP001"})
    assert only and all(w.rule_id == "DRP001" for w in only)


def test_disabled_rules_skips_listed_ids():
    record = {"record_id": "wrong-id"}
    none = lint_record(record, disabled_rules={"DRP001"})
    assert not any(w.rule_id == "DRP001" for w in none)


# --------------------------------------------------------------------------- #
# lint_data
# --------------------------------------------------------------------------- #
def test_lint_data_returns_record_index_for_batches():
    data = [{"record_id": "wrong"}, {"record_id": "dec-0001"}]
    warns = lint_data(data)
    by_index = {(w.record_index, w.rule_id) for w in warns}
    assert (0, "DRP001") in by_index
    assert (1, "DRP001") not in by_index


def test_lint_data_handles_non_dict_inputs():
    assert lint_data(None) == []
    assert lint_data("string") == []
    assert lint_data(42) == []


def test_lint_data_skips_non_dict_records_in_batches():
    out = lint_data([{"record_id": "wrong"}, "not a record", 7])
    assert all(isinstance(w, LintWarning) for w in out)


def test_lint_warning_format_includes_rule_severity_and_field():
    w = LintWarning(
        rule_id="DRP001",
        message="x",
        field="record_id",
        severity=SEVERITY_STYLE,
        record_id="dec-0001",
    )
    s = w.format()
    assert "[DRP001]" in s and "[style]" in s and "dec-0001" in s and "record_id" in s


def test_lint_warning_format_uses_index_when_no_id():
    w = LintWarning(
        rule_id="DRP001",
        message="x",
        field="record_id",
        severity=SEVERITY_STYLE,
        record_index=3,
    )
    assert "[3]" in w.format()


# --------------------------------------------------------------------------- #
# Style helper
# --------------------------------------------------------------------------- #
def test_style_disabled_passes_through_text():
    s = _Style(enabled=False)
    assert s.green("ok") == "ok"
    assert s.red("err") == "err"


def test_style_enabled_wraps_with_ansi():
    s = _Style(enabled=True)
    assert s.green("ok").startswith("\033[")
    assert s.green("ok").endswith("\033[0m")


def test_supports_color_respects_no_color_env(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    assert _supports_color() is False


def test_supports_color_respects_force_color_env(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert _supports_color() is True


# --------------------------------------------------------------------------- #
# CLI: validate
# --------------------------------------------------------------------------- #
def test_cli_validate_examples_returns_ok(capsys):
    rc = main(["validate", "examples/minimal_valid.json", "--format", "json", "--no-color"])
    capsys.readouterr()
    assert rc == EXIT_OK


def test_cli_validate_invalid_fixture_returns_invalid(capsys):
    rc = main(["validate", "fixtures/invalid/duplicate_id.json", "--format", "json", "--no-color"])
    capsys.readouterr()
    assert rc == EXIT_INVALID


def test_cli_bare_path_defaults_to_validate(capsys):
    rc = main(["examples/minimal_valid.json", "--no-color"])
    capsys.readouterr()
    assert rc == EXIT_OK


def test_cli_validate_json_output_has_expected_top_level_keys(capsys):
    main(["validate", "examples/minimal_valid.json", "--format", "json", "--no-color"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "validate" in payload
    assert payload["validate"]["status"] == "OK"


def test_cli_validate_with_lint_emits_both_sections(capsys):
    main([
        "validate", "examples/minimal_valid.json",
        "--lint", "--format", "json", "--no-color",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert "validate" in payload and "lint" in payload


def test_cli_validate_quiet_omits_passing_lines(capsys):
    main(["validate", "examples/minimal_valid.json", "--quiet", "--no-color"])
    out = capsys.readouterr().out
    assert "minimal_valid.json: ok" not in out
    assert "summary" in out


# --------------------------------------------------------------------------- #
# CLI: lint
# --------------------------------------------------------------------------- #
def test_cli_lint_fail_on_warn_returns_lint_fail(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"record_id": "bad", "decision": "x"}), encoding="utf-8")
    rc = main(["lint", str(path), "--fail-on-warn", "--no-color"])
    capsys.readouterr()
    assert rc == EXIT_LINT_FAIL


def test_cli_lint_clean_record_with_fail_on_warn_returns_ok(tmp_path, capsys):
    path = tmp_path / "ok.json"
    payload = {
        "record_id": "dec-0099",
        "tags": ["x"],
        "metadata": {"author": "alice"},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    rc = main(["lint", str(path), "--fail-on-warn", "--no-color"])
    capsys.readouterr()
    assert rc == EXIT_OK


def test_cli_lint_disable_rule_silences_it(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"record_id": "bad"}), encoding="utf-8")
    rc = main(["lint", str(path), "--disable-rule", "DRP001", "--no-color"])
    out = capsys.readouterr().out
    assert "DRP001" not in out
    # All other rules may still fire, but exit code stays OK without --fail-on-warn.
    assert rc == EXIT_OK


def test_cli_lint_unknown_rule_warns_and_runs(tmp_path, capsys):
    path = tmp_path / "ok.json"
    path.write_text(json.dumps({"record_id": "dec-0001"}), encoding="utf-8")
    rc = main(["lint", str(path), "--rule", "DRPXXXX", "--no-color"])
    err = capsys.readouterr().err
    assert "unknown rule" in err
    assert rc == EXIT_OK


def test_cli_lint_min_severity_filter(tmp_path, capsys):
    path = tmp_path / "rec.json"
    path.write_text(json.dumps({"record_id": "dec-0001"}), encoding="utf-8")
    main(["lint", str(path), "--min-severity", "best_practice", "--format", "json", "--no-color"])
    payload = json.loads(capsys.readouterr().out)
    severities = {w["severity"] for f in payload["files"] for w in f["warnings"]}
    assert severities <= {"best_practice"}


# --------------------------------------------------------------------------- #
# CLI: rules
# --------------------------------------------------------------------------- #
def test_cli_rules_human(capsys):
    rc = main(["rules", "--no-color"])
    out = capsys.readouterr().out
    assert "DRP001" in out
    assert rc == EXIT_OK


def test_cli_rules_json(capsys):
    rc = main(["rules", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert any(r["rule_id"] == "DRP001" for r in payload)
    assert rc == EXIT_OK


# --------------------------------------------------------------------------- #
# CLI: error paths
# --------------------------------------------------------------------------- #
def test_cli_missing_file_returns_usage_error(tmp_path, capsys):
    rc = main(["validate", str(tmp_path / "nope.json"), "--no-color"])
    err = capsys.readouterr().err
    assert rc == EXIT_USAGE
    assert "input not found" in err


def test_cli_missing_required_paths_returns_usage_error(capsys):
    rc = main(["validate"])
    capsys.readouterr()
    assert rc == EXIT_USAGE


def test_cli_invalid_json_marks_file_as_failing(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    rc = main(["validate", str(bad), "--format", "json", "--no-color"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["validate"]["status"] == "FAIL"
    assert rc == EXIT_INVALID


def test_cli_no_color_strips_ansi(tmp_path, capsys):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"record_id": "bad"}), encoding="utf-8")
    main(["lint", str(path), "--no-color"])
    out = capsys.readouterr().out
    assert "\033[" not in out


def test_cli_help_returns_ok(capsys):
    rc = main(["--help"])
    out = capsys.readouterr().out
    assert "drp-validate" in out
    assert rc == EXIT_OK


def test_cli_version_returns_ok(capsys):
    rc = main(["--version"])
    out = capsys.readouterr().out
    assert __version__ in out
    assert rc == EXIT_OK


def test_cli_some_missing_some_present_processes_present(tmp_path, capsys):
    good = tmp_path / "ok.json"
    good.write_text(json.dumps({"record_id": "dec-0001"}), encoding="utf-8")
    rc = main(["lint", str(good), str(tmp_path / "missing.json"), "--no-color"])
    err = capsys.readouterr().err
    assert "skipping unreadable" in err
    assert rc == EXIT_OK


# --------------------------------------------------------------------------- #
# Console-script entry point
# --------------------------------------------------------------------------- #
def test_module_entry_help_via_subprocess():
    proc = subprocess.run(
        [sys.executable, "drp_cli.py", "--help"],
        capture_output=True, text=True,
    )
    assert proc.returncode == EXIT_OK
    assert "drp-validate" in proc.stdout


def test_module_entry_validate_via_subprocess():
    proc = subprocess.run(
        [sys.executable, "drp_cli.py", "validate", "examples/minimal_valid.json", "--no-color"],
        capture_output=True, text=True,
    )
    assert proc.returncode == EXIT_OK
