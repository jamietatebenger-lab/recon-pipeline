#!/usr/bin/env python3
"""Create and compare auditable evidence records from public court-list captures.

This utility deliberately does not scrape court portals, bypass access controls,
authenticate to services, or infer missing legal details. It works from a local
file that the operator has lawfully obtained from a public source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _letters(value: str) -> str:
    return re.sub(r"[^A-Z]", "", value.upper())


def _name_tokens(value: str) -> list[str]:
    """Canonicalize whitespace-delimited name parts consistently.

    Punctuation inside a name part is removed rather than treated as a separator,
    so O'Connor and OCONNOR canonicalize to the same token.
    """

    return [token for token in (_letters(part) for part in value.split()) if token]


def _normalise_full_name(value: str) -> str:
    return " ".join(_name_tokens(value))


def _expected_parts(full_name: str) -> tuple[str, str]:
    words = _name_tokens(full_name)
    if not words:
        return "", ""
    surname = words[-1]
    initials = "".join(word[0] for word in words[:-1])
    return surname, initials


def _listed_parts(listed_name: str) -> tuple[str, str]:
    value = listed_name.strip().upper()
    if "," in value:
        surname_raw, given_raw = value.split(",", 1)
        surname = _letters(surname_raw)
        tokens = re.findall(r"[A-Z][A-Z*.'-]*", given_raw)
    else:
        words = value.split()
        if not words:
            return "", ""
        surname = _letters(words[-1])
        tokens = words[:-1]

    initials = "".join(_letters(token)[:1] for token in tokens if _letters(token))
    return surname, initials


def classify_identity(expected_full_name: str, listed_name: str) -> dict[str, Any]:
    """Grade a public listing without claiming more identity certainty than shown."""

    expected_norm = _normalise_full_name(expected_full_name)
    listed_norm = _normalise_full_name(listed_name)

    if expected_norm and expected_norm == listed_norm:
        return {
            "confidence": "EXACT",
            "reason": "The public listing displays the same full name.",
        }

    expected_surname, expected_initials = _expected_parts(expected_full_name)
    listed_surname, listed_initials = _listed_parts(listed_name)

    if expected_surname and listed_surname == expected_surname:
        if listed_initials and listed_initials == expected_initials:
            return {
                "confidence": "INITIALS_MATCH",
                "reason": "Surname and all displayed given-name initials match; full identity remains masked.",
            }
        if listed_initials and expected_initials.startswith(listed_initials):
            return {
                "confidence": "PARTIAL_INITIALS_MATCH",
                "reason": "Surname and displayed initial prefix match, but the listing does not expose the full name.",
            }
        if not listed_initials:
            return {
                "confidence": "SURNAME_ONLY",
                "reason": "Only the surname can be matched; this is insufficient for attribution.",
            }

    return {
        "confidence": "NO_MATCH",
        "reason": "The displayed surname/initial pattern does not match the expected name.",
    }


def _parse_capture_time(value: str | None) -> str | None:
    """Validate and normalize an optional source-capture timestamp.

    A timezone offset is required so evidence records are unambiguous. "Z" is
    accepted as UTC. Unknown capture times remain null instead of being guessed.
    """

    if value is None:
        return None

    candidate = value.strip()
    if not candidate:
        return None

    parsed_value = candidate[:-1] + "+00:00" if candidate.endswith(("Z", "z")) else candidate
    try:
        parsed = datetime.fromisoformat(parsed_value)
    except ValueError as exc:
        raise ValueError("--captured-at must be an ISO 8601 timestamp with a timezone") from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--captured-at must include a timezone offset or Z")

    return parsed.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class CourtObservation:
    date: str | None = None
    court: str | None = None
    courtroom: str | None = None
    time: str | None = None
    hearing_type: str | None = None
    matter_number: str | None = None
    outcome: str | None = None
    notes: str | None = None


def build_record(args: argparse.Namespace) -> dict[str, Any]:
    source_path = Path(args.source_file).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"source file does not exist: {source_path}")

    identity = classify_identity(args.expected_name, args.listed_name)
    captured_at_utc = _parse_capture_time(getattr(args, "captured_at", None))
    observation = CourtObservation(
        date=args.date,
        court=args.court,
        courtroom=args.courtroom,
        time=args.time,
        hearing_type=args.hearing_type,
        matter_number=args.matter_number,
        outcome=args.outcome,
        notes=args.notes,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "file": str(source_path),
            "url": args.source_url,
            "captured_at_utc": captured_at_utc,
            "sha256": sha256_file(source_path),
            "size_bytes": source_path.stat().st_size,
        },
        "identity": {
            "expected_name": args.expected_name,
            "listed_name": args.listed_name,
            **identity,
        },
        "observation": asdict(observation),
        "handling": {
            "public_source_only": True,
            "missing_fields_are_not_inferred": True,
            "capture_time_is_explicit_or_null": True,
        },
    }


def diff_records(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes: dict[str, dict[str, Any]] = {}

    def compare(prefix: str, left: dict[str, Any], right: dict[str, Any], keys: list[str]) -> None:
        for key in keys:
            old = left.get(key)
            new = right.get(key)
            if old != new:
                changes[f"{prefix}.{key}"] = {"before": old, "after": new}

    compare(
        "observation",
        before.get("observation", {}),
        after.get("observation", {}),
        ["date", "court", "courtroom", "time", "hearing_type", "matter_number", "outcome", "notes"],
    )
    compare(
        "identity",
        before.get("identity", {}),
        after.get("identity", {}),
        ["listed_name", "confidence", "reason"],
    )
    compare(
        "source",
        before.get("source", {}),
        after.get("source", {}),
        ["url", "captured_at_utc", "sha256", "size_bytes"],
    )

    return {
        "changed": bool(changes),
        "change_count": len(changes),
        "changes": changes,
    }


def _load_json(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(payload: dict[str, Any], output: str | None) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record and diff public court-list evidence without scraping or inference."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record", help="Create one evidence record from a local public-source capture.")
    record.add_argument("--source-file", required=True, help="Local HTML/PDF/text capture obtained lawfully.")
    record.add_argument("--source-url", help="Public source URL recorded as provenance metadata.")
    record.add_argument(
        "--captured-at",
        help="ISO 8601 time the source was actually captured/accessed, including timezone; unknown stays null.",
    )
    record.add_argument("--expected-name", required=True, help="Reference full name used only for match grading.")
    record.add_argument("--listed-name", required=True, help="Name exactly as displayed by the public listing.")
    record.add_argument("--date")
    record.add_argument("--court")
    record.add_argument("--courtroom")
    record.add_argument("--time")
    record.add_argument("--hearing-type")
    record.add_argument("--matter-number")
    record.add_argument("--outcome")
    record.add_argument("--notes")
    record.add_argument("--output", help="Write JSON evidence to this path instead of stdout.")

    diff = subparsers.add_parser("diff", help="Compare two evidence records and show only verified field changes.")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.add_argument("--output")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "record":
        try:
            payload = build_record(args)
        except ValueError as exc:
            parser.error(str(exc))
        _write_json(payload, args.output)
        return 0

    if args.command == "diff":
        _write_json(diff_records(_load_json(args.before), _load_json(args.after)), args.output)
        return 0

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
