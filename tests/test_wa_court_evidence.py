import argparse
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "wa_court_evidence.py"
SPEC = importlib.util.spec_from_file_location("wa_court_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_exact_identity_match():
    result = MODULE.classify_identity("Alex Jordan Smith", "Alex Jordan Smith")
    assert result["confidence"] == "EXACT"


def test_masked_initials_identity_match():
    result = MODULE.classify_identity("Alex Jordan Taylor Smith", "SMITH, A** J** T**")
    assert result["confidence"] == "INITIALS_MATCH"


def test_namesake_is_not_attributed():
    result = MODULE.classify_identity("Alex Jordan Taylor Smith", "SMITH, N** G**")
    assert result["confidence"] == "NO_MATCH"


def test_build_record_hashes_source_and_preserves_missing_fields(tmp_path):
    source = tmp_path / "listing.txt"
    source.write_text("public court listing snapshot\n", encoding="utf-8")

    args = argparse.Namespace(
        source_file=str(source),
        source_url="https://example.gov.au/public-list",
        expected_name="Alex Jordan Taylor Smith",
        listed_name="SMITH, A** J** T**",
        date="2026-09-21",
        court="Example Magistrates Court",
        courtroom="Court 4",
        time="10:00",
        hearing_type=None,
        matter_number=None,
        outcome=None,
        notes=None,
    )

    record = MODULE.build_record(args)

    assert record["source"]["sha256"] == MODULE.sha256_file(source)
    assert record["identity"]["confidence"] == "INITIALS_MATCH"
    assert record["observation"]["hearing_type"] is None
    assert record["observation"]["matter_number"] is None
    assert record["handling"]["missing_fields_are_not_inferred"] is True


def test_diff_records_reports_only_changed_fields():
    before = {
        "identity": {"listed_name": "SMITH, A** J** T**", "confidence": "INITIALS_MATCH", "reason": "same"},
        "source": {"url": "https://example.gov.au/a", "sha256": "1", "size_bytes": 10},
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
