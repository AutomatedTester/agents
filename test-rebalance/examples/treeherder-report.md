# Test rebalance: mozilla/treeherder

2026-10-04 · window: 180 days (342 commits, 89 ignored as sweeps) · CI data: none · clone history starts 2023-06-29, so "last changed 2023-06-29" means "on or before"

## Summary

Treeherder is the leanest of the suites reviewed, and it has already made the kind of move this skill looks for. When the log viewer was rewritten in May 2026, browser tests arrived with it. In August the browser tests moved from Puppeteer to Playwright, still served from JSON fixtures rather than a live backend. That's a sound bet where the API behind them is quiet. It's a weaker one for Perfherder, where the API is the busiest in the repo and nothing checks that the fixtures still match it.

| Level | Files | Tests |
| --- | --- | --- |
| e2e (browser, API stubbed) | 3 | 19 |
| api | 33 | 331 |
| integration | 54 | 357 |
| component | 23 | 271 |
| unit | 65 | 864 |

**Project helpers mapped before counting.** pytest fixtures are injected by name, so the inventory can't see them from imports:
- `test_repository`, `failure_classifications`, `test_job` and the other data fixtures sit on the real Django test database. Mapped to integration.
- `client` is DRF's `APIClient`. Calls through it count as api.

## Move up

### Perfherder UI tests' fixtures and recordings → add an API-level contract check (confidence: medium)

- **Question it answers:** do the JSON fixtures the Perfherder UI tests stub with still look like what the API returns?
- **Evidence:**
  - Perf API code had 24 non-sweep commits in the window; `treeherder/perf` had 51. Fields were added to the perf serializers (alert severity, machine name, suggested culprit) and removed (seven PerfCompare statistics on 2026-09-17).
  - Perfherder UI code (`ui/perfherder`) had 43 commits. Its alerts, graphs and table tests stub the API with fixtures. Some were updated alongside recent features; others date from June 2023 or earlier, the start of the clone: `performance_signature_formatted`, `performance_tags`, `alert_summaries_common`, `alert_summary_very_big`.
  - The graphs-view browser test replays a HAR recording made in the Puppeteer era (June 2023 or earlier). The performance-summary endpoint it replays has since gained `machine_name` (August 2026), and the recording doesn't contain it. The graphs UI doesn't read that field yet, so nothing is broken, but that's exactly how a stub drifts.
  - Nothing ties a fixture or recording to the serializer that produces it.
- **What I didn't find:** an actual mismatch. The fields removed in September aren't in any UI fixture, and the alert-severity fixture changed the same day the field arrived. The team is keeping up by hand, and this check would make that automatic.
- **Suggested shape:** a small backend test that builds each fixture's object through the real serializer and asserts the fixture's keys still exist in the output. It's cheap, runs with the existing API tests, and turns a silent drift into a failing test. Re-recording the graphs-view HAR against a current backend is a one-off fix for the browser test.

## Move down

No candidates. The backend suite is mostly integration and API tests on a real database, which is the right level for Django ETL and API code. With no CI timing data, nothing points to tests that are expensive for what they protect.

## Leave it alone

- **The Jobs view and log viewer browser tests** (2 of the 3 files in `tests/ui/integration`). They stub the API, but the APIs behind them are quiet: `jobs.py` had no commits in the window, `push.py` one and `serializers.py` one. Stubbing is a good bet there.
- **The log viewer** (`ui/logviewer`, 7 commits but 2,093 lines). This was rewritten in May and got browser coverage in the same change, exactly the "move up when you rebuild" case.
- **`tests/webapp/api`**: 174 API-level tests on the busiest backend surface.

## Why-this-level annotations

```
tests/ui/integration (jobs, logviewer): browser with stubbed API because the jobs/push APIs are stable. Revisit if those serializers start changing.
Perfherder UI and graphs-view tests: stubbed, backed by a fixture/serializer contract test. Revisit if the contract test starts failing often; that's the signal to test against a real backend.
```
