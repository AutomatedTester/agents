# Incident file format

For `areas.py --incidents`. This page is for whoever produces the file: a person,
or an agent reading an observability tool, incident tracker or error monitor.
The consumer is `scripts/areas.py`; it only reads the CSV, it never calls your
tools.

## Schema

One row per incident (or per distinct error cluster worth counting once).

| Column | Required | Values |
| --- | --- | --- |
| `date` | yes | `YYYY-MM-DD`, when it started. Rows in any other format are skipped and reported |
| `path` | yes | Repo-relative file or directory the incident traces to, e.g. `src/payments/` or `packages/auth/src/session.ts`. Leave **blank** if you can't tell |
| `severity` | no | `sev1`-`sev4`. Normalise your tool's scale (see below) |
| `detected_by` | no | `alert`, `synthetic`, `customer`, `test` or `other` |
| `minutes_to_detect` | no | Minutes from start of impact to first detection, a number |

```csv
date,path,severity,detected_by,minutes_to_detect
2026-08-14,src/payments/,sev1,customer,95
2026-08-30,src/payments/refunds.ts,sev2,alert,6
2026-09-09,packages/auth/,sev3,synthetic,3
2026-09-12,,sev2,customer,40
```

The last row is how to record an incident you can't place. It is counted and
reported as unmapped, which is better than a wrong path.

## Mapping an incident to a path

This is the hard part and the one that most affects the report. In rough order
of reliability:

1. **Stack trace or error location** in the failing code, taken from the error
   monitor. Use the first frame in repo code, not in a library or framework.
2. **The fix.** The commit or PR that resolved the incident. Use the directory
   it changed most.
3. **The causing change.** The deploy or PR just before impact began. Weaker:
   a deploy can trigger an incident elsewhere.
4. **Service ownership.** The service name mapped to its directory through
   CODEOWNERS or a service catalogue. Coarse, but fine at directory level.

Use a directory rather than a file when the evidence only supports that. Never
pick a path just to fill the column; blank is correct when you don't know.
Infrastructure incidents (cloud outage, expired certificate, capacity) usually
don't trace to application code: leave `path` blank rather than blaming the
nearest service.

## Normalising severity

| Your tool says | Write |
| --- | --- |
| P1, SEV1, critical, 1 | `sev1` |
| P2, SEV2, high, major, 2 | `sev2` |
| P3, SEV3, medium, moderate, 3 | `sev3` |
| P4, SEV4, low, minor, 4 | `sev4` |

Anything else is reported as an unrecognised severity and counted as not serious.
Map it yourself if you know what it means.

## What the columns are for

- `path` and `date` give incidents per area, to set beside test coverage.
- `severity` separates a recurring annoyance from an outage. `areas.py` counts
  sev1 and sev2 as serious.
- `detected_by` and `minutes_to_detect` are what make a **downgrade** safe or not.
  Incidents found by customers, or found slowly, mean production monitoring is
  not covering that area, so the tests are doing that job. Fast alert or
  synthetic detection means a cheap regression test may be enough.

## Be honest about gaps

State what the file does not cover: the date range exported, which incident
sources were included, and how many incidents could not be mapped. A short file
means either a healthy system or a thin export, and the skill cannot tell which
without this.
