"""Tests that the JSON Schema file itself is well-formed and covers the
documented fields."""

import json
import os

import pytest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "schema", "drp.schema.json")


@pytest.fixture(scope="module")
def schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_schema_loads(schema):
    assert isinstance(schema, dict)
    assert schema.get("type") == "object"


def test_schema_declares_required_fields(schema):
    required = set(schema.get("required", []))
    assert required == {
        "record_id",
        "timestamp",
        "context",
        "decision",
        "options",
        "status",
    }


def test_schema_disallows_additional_properties(schema):
    assert schema.get("additionalProperties") is False


def test_schema_status_enum(schema):
    enum = schema["properties"]["status"]["enum"]
    assert set(enum) == {
        "draft",
        "proposed",
        "complete",
        "superseded",
        "rejected",
    }


def test_schema_impact_enum(schema):
    enum = schema["properties"]["impact"]["enum"]
    assert enum == [-1, 0, 1, None]


def test_schema_impact_rejects_booleans_by_type(schema):
    types = schema["properties"]["impact"]["type"]
    assert "boolean" not in types
    assert set(types) == {"integer", "null"}


def test_schema_options_minimum_items(schema):
    assert schema["properties"]["options"]["minItems"] == 1


def test_schema_arrays_require_string_items(schema):
    for name in (
        "options",
        "parent_record_ids",
        "child_record_ids",
        "tags",
    ):
        items = schema["properties"][name]["items"]
        assert items["type"] == "string"
        assert items.get("minLength", 0) >= 1
