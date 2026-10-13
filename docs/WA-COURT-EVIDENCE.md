# WA public court evidence workflow

This helper is for **evidentiary capture of lawfully obtained public court-list material**. It does not scrape portals, log in to services, bypass controls, enumerate private records, or guess missing legal details.

## What it records

- source file path, SHA-256 and byte size
- public source URL as provenance metadata
- source capture/access time when explicitly supplied
- separate UTC record-generation time
- exact displayed court-list name
- identity-match confidence:
  - `EXACT`
  - `INITIALS_MATCH`
  - `PARTIAL_INITIALS_MATCH`
  - `SURNAME_ONLY`
  - `NO_MATCH`
- date, court, courtroom and time when actually shown
- hearing type, matter number and outcome only when explicitly present

A masked initials match is deliberately **not** treated as exact identification. Punctuation inside a name component is canonicalized consistently, so forms such as `O'Connor` and `OConnor` compare on the same basis without weakening namesake controls.

## Create an evidence record

First save the public listing page or other lawful source locally. Then run:

```bash
python scripts/wa_court_evidence.py record \
  --source-file evidence/court-list-2026-09-21.html \
  --source-url "https://www.example.wa.gov.au/public-court-list" \
  --captured-at "2026-09-21T10:00:00+08:00" \
  --expected-name "Alex Jordan Taylor Smith" \
  --listed-name "SMITH, A** J** T**" \
  --date "2026-09-21" \
  --court "Example Magistrates Court" \
  --courtroom "Court 4" \
  --time "10:00" \
  --output evidence/2026-09-21.json
```

`--captured-at` must be an ISO 8601 timestamp with a timezone offset (or `Z`). If the original capture/access time is unknown, omit it: the evidence record stores `captured_at_utc: null` rather than substituting the later processing time. `generated_at_utc` records when the JSON evidence record itself was created.

If the source does not publish a hearing type, charge, matter number, outcome or adjournment, leave that field unset. The tool writes `null`; it never fills gaps by inference.

## Compare a later capture

```bash
python scripts/wa_court_evidence.py diff \
  evidence/2026-09-21.json \
  evidence/2026-10-05.json
```

This outputs only changed fields, including an explicitly changed capture timestamp, date, courtroom, hearing type, matter number or published outcome.

## Evidence handling

For defensible records:

1. Keep the original capture unchanged.
2. Record the public URL and the actual capture/access time when known.
3. Never substitute record-generation time for an unknown capture time.
4. Preserve the SHA-256 emitted by this tool.
5. Store each subsequent capture separately rather than overwriting the prior file.
6. Treat masked-name matches as corroborative, not definitive identity proof.
7. Prefer official WA court or government sources over aggregators.
8. Do not infer charges, pleas, outcomes or attendance mode when the source does not display them.

## Test

```bash
python -m pytest tests/test_wa_court_evidence.py -q
```

The main GitHub Actions build also runs this test module on Python 3.13.
