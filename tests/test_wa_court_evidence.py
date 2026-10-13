import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "wa_court_evidence.py"
SPEC = importlib.util.spec_from_file_location("wa_court_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def make_args(source, **overrides):
    values = {
        "source_file": str(source),
        "source_url": "https://example.gov.au/public-list",
        "captured_at": None,
        "expected_name": "Alex Jordan Taylor Smith",
        "listed_name": "SMITH, A** J** T**",
        "date": "2026-09-21",
        "court": "Example Magistrates Court",
        "courtroom": "Court 4",
        "time": "10:00",
        "hearing_type": None,
        "matter_number": None,
        "outcome": None,
        "notes": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_exact_identity_match():
    result = MODULE.classify_identity("Alex Jordan Smith", "Alex Jordan Smith")
    assert result["confidence"] == "EXACT"


def test_masked_initials_identity_match():
    result = MODULE.classify_identity("Alex Jordan Taylor Smith", "SMITH, A** J** T**")
    assert result["confidence"] == "INITIALS_MATCH"


def test_apostrophized_surname_is_canonicalized_consistently():
    exact = MODULE.classify_identity("Alex O'Connor", "Alex OConnor")
    masked = MODULE.classify_identity("Alex O'Connor", "O'CONNOR, A**")

    assert exact["confidence"] == "EXACT"
    assert masked["confidence"] == "INITIALS_MATCH"


def test_namesake_is_not_attributed():
    result = MODULE.classify_identity("Alex Jordan Taylor Smith", "SMITH, N** G**")
    assert result["confidence"] == "NO_MATCH"


def test_build_record_hashes_source_and_preserves_missing_fields(tmp_path):
    source = tmp_path / "listing.txt"
    source.write_text("public court listing snapshot\n", encoding="utf-8")

    record = MODULE.build_record(make_args(source))

    assert record["schema_version"] == 2
    assert record["source"]["sha256"] == MODULE.sha256_file(source)
    assert record["source"]["captured_at_utc"] is None
    assert record["identity"]["confidence"] == "INITIALS_MATCH"
    assert record["observation"]["hearing_type"] is None
    assert record["observation"]["matter_number"] is None
    assert record["handling"]["missing_fields_are_not_inferred"] is True
    assert record["handling"]["capture_time_is_explicit_or_null"] is True
    assert "generated_at_utc" in record


def test_capture_time_is_normalized_separately_from_generation_time(tmp_path):
    source = tmp_path / "listing.txt"
    source.write_text("public court listing snapshot\n", encoding="utf-8")

    record = MODULE.build_record(make_args(source, captured_at="2026-09-21T10:00:00+08:00"))

    assert record["source"]["captured_at_utc"] == "2026-09-21T02:00:00+00:00"
    assert record["generated_at_utc"] != record["source"]["captured_at_utc"]


def test_capture_time_requires_timezone(tmp_path):
    source = tmp_path / "listing.txt"
    source.write_text("public court listing snapshot\n", encoding="utf-8")

    with pytest.raises(ValueError, match="timezone"):
        MODULE.build_record(make_args(source, captured_at="2026-09-21T10:00:00"))


def test_diff_records_reports_only_changed_fields():
    before = {
        "identity": {"listed_name": "SMITH, A** J** T**", "confidence": "INITIALS_MATCH", "reason": "same"},
        "source": {
            "url": "https://example.gov.au/a",
            "captured_at_utc": "2026-09-21T02:00:00+00:00",
            "sha256": "1",
            "size_bytes": 10,
        },
        "observation": {
            "date": "2026-09-21",
            "court": "Example Magistrates Court",
            "courtroom": "Court 4",
            "time": "10:00",
            "hearing_type": None,
            "matter_number": None,
            "outcome": None,
            "notes": None,
        },
    }
    after = json.loads(json.dumps(before))
    after["observation"]["outcome"] = "Adjourned"
    after["observation"]["date"] = "2026-10-05"

    diff = MODULE.diff_records(before, after)

    assert diff["changed"] is True
    assert diff["change_count"] == 2
    assert diff["changes"]["observation.outcome"]["after"] == "Adjourned"
    assert diff["changes"]["observation.date"]["after"] == "2026-10-05"
