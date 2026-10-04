---
name: test-rebalance
description: Audit a test suite and recommend which tests should move between levels (end-to-end, API, integration, component, unit) based on how risk, change rate and flakiness have shifted over time. Use this whenever the user asks to review, rebalance, audit or right-size their tests or test pyramid, asks which E2E tests could be API or integration tests (or the reverse), complains that CI is slow or flaky and wants to know what to cut or move, or asks whether their mocks are still trustworthy. Produces a written report with evidence; it never edits or deletes tests.
---

# Test rebalance

A test's level is a decision made at a point in time, not a permanent label. This
skill checks whether those decisions still hold and recommends moves in both
directions: down the stack where a feature has settled and the cost no longer
buys much, and up the stack where risk has returned and mocks may have gone stale.

**Never modify, delete or move test files.** The output is a report for a human
to act on. If the user then asks for a specific move, treat it as a separate task.

## Workflow

### 1. Scope

Find out, briefly, before running anything (skip what the user already said):
- Which repo or directory, and anything to exclude (generated tests, vendored code).
- Where CI results live, if anywhere. JUnit XML from several recent runs is
  ideal; one run gives timing but no flakiness.
- Any business context: critical journeys, recent incidents, features about to
  be rebuilt. This is the one input the code cannot provide.

If they have no CI data, proceed anyway and say the report has no flakiness or
timing evidence.

### 2. Inventory

```bash
python <skill_dir>/scripts/inventory.py <repo> [--exclude dir ...] > /tmp/rebalance-inv.json
```

Classifies each test file as e2e, api, integration, component or unit from its
imports and calls, with the matched signals. Then **spot-check**: open a few files
per level, and every file whose reasons say "inferred" or "note: path suggests".
Correct the level in your working notes where the heuristic is wrong.

**Check the project's own test helpers.** Large codebases wrap their boundaries
in helpers whose names mislead: a `createMockServer` that boots the whole app on
a real database is an integration test, not a mocked unit test. If one level is
suspiciously large, grep the test files for the most common helper calls, read
the helper's source, and rerun with `--treat`:

```bash
python <skill_dir>/scripts/inventory.py <repo> \
    --treat 'createMockServer|createApp=in_process_app' \
    --treat 'createMockDatabase=real_dependency' > /tmp/rebalance-inv.json
```

`--treat` also applies to subclasses: map a base class like `DbTestCase` once and
every test class that inherits from it, however deep, picks it up. For pytest,
fixtures are injected by name, so map the fixture names themselves
(`test_repository|django_db=real_dependency`) and the client fixture's calls
(`client\.(get|post)=http`).

Level conventions: HTTP driven in-process (supertest, DRF `APIClient`, Symfony
or Flask test clients) counts as **api**, because it tests the HTTP contract.
Browser tests that stub the backend (`page.route`, HAR replay, `cy.intercept`
fixtures) are still **e2e** but are reported as partially mocked; treat their
fixtures as mocked boundaries in step 4.

Name the helpers you mapped in the report so readers can check them. Test files
that import a data layer, an app factory or a service client are often integration
tests in disguise; tests in an `e2e` folder are sometimes pure API calls.

### 3. Evidence

```bash
python <skill_dir>/scripts/evidence.py <repo> --inventory /tmp/rebalance-inv.json \
    --days 180 [--junit 'path/to/reports/**/*.xml'] > /tmp/rebalance-ev.json
```

Adds per file: churn of the test, its likely subject code (by name and by
co-change), churn and fix commits on that subject, and CI failure rate, flaky
cases and mean duration. Dependency bumps, formatting sweeps and bot commits are
excluded so they don't drown the signal.

Treat `subject.files` as a guess. For any test you are about to recommend moving,
check its subject files make sense and open the test to see what it asserts.

Use `--days 365` for slow-moving projects; shorten it for fast ones. With a
shallow clone, a "last changed" date equal to the oldest commit in the clone means
"on or before"; say so in the report.

### 3b. Areas (large repos)

```bash
python <skill_dir>/scripts/areas.py <repo> --evidence /tmp/rebalance-ev.json \
    --depth 3 [--prefix packages/]
```

Churn per source directory alongside the tests, by level, that cover it. Read
it for the two shapes that matter most: a busy area with nothing above
unit/component level (upgrade), and a quiet area covered by many browser tests
(downgrade). Confirm per-area numbers with `git log` before quoting them, and
look at CI config to see which levels actually run on pull requests.

### 4. Judge

Read `references/signals.md` and weigh each test against it. For every
candidate, open the test and answer:
- What question does this test answer?
- Does answering it need this level's boundary (a real browser, real HTTP, a
  real database)?
- What has changed since it was written: the code, the boundary, the risk?

Group related files (all the OAuth provider tests, say) when they share a story.

### 5. Report

Write the report as markdown using `references/report-template.md`. Rules:
- Lead with the current shape of the suite (counts by level) and the 3–5 moves
  with the biggest payoff.
- Every recommendation names the evidence behind it with numbers: commits, fix
  commits, failure rate, seconds. No evidence, no recommendation.
- Recommendations go both ways. If you found no upgrade candidates, say what
  you checked.
- Say what a replacement test would assert and which boundary it mocks.
- Include a "leave it alone" section for tests that look expensive but are
  in the right place, so nobody "optimises" a critical smoke test away.
- End with suggested one-line "why this level" annotations for the moved tests,
  so the next review has a recorded reason to check against.

Keep it short enough to read in ten minutes. Put per-file detail in a table at
the end, not in prose.
