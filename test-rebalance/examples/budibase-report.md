# Test rebalance: Budibase/budibase

2026-10-04 · window: 180 days (3,684 commits, 458 ignored as sweeps) · CI data: none

## Summary

Budibase has a strong, expensive server suite and no browser tests at all. The server side runs 2,640 API tests in-process against real CouchDB and MinIO containers. Some of those suites repeat across up to ten databases on every affected PR. The builder UI, by far the busiest code in the repo, has had no browser coverage since Cypress was removed in January 2023, and the API-level QA suite went in April 2024. The rebalance here is almost entirely upward.

| Level | Files | Tests |
| --- | --- | --- |
| e2e | 0 | 0 |
| api | 200 | 2,640 |
| integration | 40 | 441 |
| component | 59 | 377 |
| unit | 277 | 2,392 |

**Project helpers mapped before counting.**
- `TestConfiguration` serves the app in-process over supertest. The Jest global setup starts real CouchDB and MinIO containers, so `config.api.*` calls are API-level tests against real storage.
- `datasourceDescribe` runs a suite once per external database.

## Move up

### packages/builder → add a browser smoke layer (confidence: high)

- **Question it answers:** can someone build an app? Create a table, add a screen, bind a component to data, add an automation, publish.
- **Evidence:**

  | Package | Non-sweep commits (180 d) | Lines changed | Browser tests |
  | --- | --- | --- | --- |
  | builder | 1,341 | 99,320 | 0 |
  | server/src/sdk | 628 | 33,061 | 0 (2,283 API tests across server) |
  | frontend-core | 156 | 5,447 | 0 |
  | client | 111 | 2,514 | 0 |

  The builder has 547 unit and 362 component tests, but every one runs in isolation. Cypress was removed on 2023-01-31; the QA-core API suite was removed in April 2024.
- **Why the current level isn't enough:** the builder is a stateful editor that talks to the server constantly. With nearly 100,000 changed lines in six months, the seams between stores, components and API calls are where regressions hide, and only a browser on a real backend exercises them.
- **Suggested shape:** 10–15 Playwright journeys run on PRs that touch `builder`, `frontend-core` or `bbui`. Don't rebuild the old Cypress suite.

### packages/client (the published-app runtime) → add a browser check (confidence: medium)

- **Question it answers:** does a published app render and work for end users?
- **Evidence:** 111 commits and 2,514 lines in the window, covered by 8 component and 13 unit tests. This is the code end users run, not just builders.
- **Suggested shape:** publish a fixture app with a form, a table and a button action, then check it in a real browser. One or two tests, run with the builder smoke suite.

## Move down

No confident downgrade candidates. The obvious target, the API suite, protects the busiest server code (`sdk` 628 commits, `api` 504). Without CI timings there's no evidence about which of its 2,640 tests are slow or flaky. Rerun with JUnit output from a few CI runs to find them.

## Leave it alone

- **The datasource matrix** (20 spec files, 805 tests, up to ten databases per affected PR). It's expensive, but the SQL generation it protects lives in `server/src/sdk`, the second-busiest area in the repo. CI already limits it to affected packages. If cost becomes a problem, the next step is scope, not level: run Postgres and SQS on every PR and the full matrix on merge.
- **`backend-core`** (97 integration, 497 unit): low churn, sensible levels.

## Why-this-level annotations

```
builder smoke suite: e2e because the builder changed ~100k lines in 6 months with no browser coverage. Revisit if builder churn settles.
datasource matrix: api against each DB because SQL generation in server/src/sdk is high-churn. Revisit if sdk churn falls below integrations'.
```

## Appendix: by package (tests, main packages only)

| Package | api | integration | component | unit |
| --- | --- | --- | --- | --- |
| server | 2,283 | 291 | 0 | 771 |
| builder | 0 | 38 | 362 | 547 |
| backend-core | 0 | 97 | 0 | 497 |
| worker | 357 | 6 | 0 | 24 |
| pro | 0 | 9 | 0 | 167 |
| frontend-core | 0 | 0 | 7 | 30 |
| client | 0 | 0 | 8 | 13 |
| bbui | 0 | 0 | 0 | 18 |
