# WA public court evidence workflow

This helper is for **evidentiary capture of lawfully obtained public court-list material**. It does not scrape portals, log in to services, bypass controls, enumerate private records, or guess missing legal details.

## What it records

- source file path, SHA-256 and byte size
- public source URL as provenance metadata
- exact displayed court-list name
- identity-match confidence:
  - `EXACT`
  - `INITIALS_MATCH`
  - `PARTIAL_INITIALS_MATCH`
  - `SURNAME_ONLY`
  - `NO_MATCH`
- date, court, courtroom and time when actually shown
- hearing type, matter number and outcome only when explicitly present
- UTC evidence-capture timestamp

A masked initials match is deliberately **not** treated as exact identification.

## Create an evidence record

First save the public listing page or other lawful source locally. Then run:

```bash
python scripts/wa_court_evidence.py record \
  --source-file evidence/court-list-2026-09-21.html \
  --source-url "https://www.example.wa.gov.au/public-court-list" \
  --expected-name "Alex Jordan Taylor Smith" \
  --listed-name "SMITH, A** J** T**" \
  --date "2026-09-21" \
  --court "Example Magistrates Court" \
  --courtroom "Court 4" \
  --time "10:00" \
  --output evidence/2026-09-21.json
```

If the source does not publish a hearing type, charge, matter number, outcome or adjournment, leave that field unset. The tool writes `null`; it never fills gaps by inference.

## Compare a later capture

```bash
python scripts/wa_court_evidence.py diff \
  evidence/2026-09-21.json \
  evidence/2026-10-05.json
```

This outputs only changed fields, which is useful for identifying a new date, courtroom, explicit adjournment or published outcome.

## Evidence handling

For defensible records:

1. Keep the original capture unchanged.
2. Record the public URL and access time.
3. Preserve the SHA-256 emitted by this tool.
4. Store each subsequent capture separately rather than overwriting the prior file.
5. Treat masked-name matches as corroborative, not definitive identity proof.
6. Prefer official WA court or government sources over aggregators.
7. Do not infer charges, pleas, outcomes or attendance mode when the source does not display them.

## Test

```bash
python -m pytest tests/test_wa_court_evidence.py -q
```
