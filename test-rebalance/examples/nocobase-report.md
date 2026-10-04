# Test rebalance: nocobase/nocobase

2026-10-04 · window: 180 days (1,640 commits, 475 ignored as dependency/formatting sweeps) · CI data: none (see "Worth a look")

## Summary

NocoBase has a large, healthy lower stack (7,461 unit, 3,585 integration and 2,990 component tests) and 1,038 browser tests. The browser tests all point at the old frontend. The new one, `client-v2` and the flow engine, has had more change than anything else in the repo and has no browser coverage at all. That's the move that matters. On the other side, over 400 browser tests repeat the same settings-menu journey once per field type, on code that has barely changed in six months.

| Level | Files | Tests |
| --- | --- | --- |
| e2e | 319 | 1,038 |
| api | 14 | 113 |
| integration | 505 | 3,585 |
| component | 405 | 2,990 |
| unit | 1,006 | 7,461 |

**Project helpers mapped before counting.** The first pass put 1,417 files in "unit". NocoBase's helpers have misleading names:

- `createMockServer`, `createMockCluster` and `createApp` boot the full application on a real SQLite or Postgres database and drive it over supertest. Mapped to integration.
- `createMockDatabase` is a real database. Mapped to integration.
- `@nocobase/test/e2e` is a Playwright wrapper whose tests call `mockPage(...).goto()`. Mapped to e2e.
- `@nocobase/test/client` re-exports Testing Library. Mapped to component.

## Move up

### packages/core/client-v2, core/flow-engine, plugin-flow-engine → add a thin e2e layer (confidence: high, pending one check)

- **Question it answers:** does the new frontend actually work in a browser: pages render, blocks can be added and configured, settings survive a reload?
- **Evidence:** this is the most active code in the repo and it is being adopted fast:

  | Package | Source commits (180 d) | Lines changed | E2E tests |
  | --- | --- | --- | --- |
  | core/client-v2 | 180 | 17,908 | 0 |
  | core/flow-engine | 72 | 6,084 | 0 |
  | plugin-flow-engine | 41 | 17,236 | 0 |
  | core/client (v1, for comparison) | 126 | 9,463 | 268 |

  93 plugins import `client-v2` and 110 import `flow-engine`. No E2E file references either, and the shared E2E templates in `packages/core/test/src/e2e` build v1 schemas.
- **Why the current level isn't enough:** `client-v2` has 1,009 component and 867 unit tests, which is good, but every one mounts pieces in isolation. A rebuild is exactly when the seams between those pieces break: routing, data loading, plugin registration and persistence. Only a browser on a real backend sees those.
- **Suggested shape:** 10–20 smoke tests, not a port of the v1 suite. One per core journey: log in, open a v2 page, add each main block type, configure one field, save, reload, check. Run them on pull requests that touch these three packages.
- **The check:** v2 browser coverage may live in a private or commercial repo. If it does, this becomes "make it visible to the open-source contributors who are changing this code".

## Move down

### plugin-data-source-main field-settings tests → component (confidence: medium)

- **Question it answers:** for each field type, do the schema-settings menu options (pattern, default value, validation rules, title, required) behave correctly?
- **Evidence:**
  - The package has 106 E2E files and 423 tests, the largest E2E block in the repo.
  - Most of them run the same shared helpers once per field type: `testPattern` in 36 files, `testDefaultValue` in 23 and `testSetValidationRules` in 11.
  - The package itself had 6 source commits in 180 days. The v1 field and schema-settings code those menus come from had 3.
  - None of the 106 test files changed in the window.
- **Replacement:** move the per-type checks to component tests that mount the field's settings menu with Testing Library (`@nocobase/test/client`, already used in 136 files) and assert on the resulting schema. That's the same question, answered in milliseconds without a backend.
- **Keep:** one E2E test per field family (text, number, date/time, relation, choice) that creates a field, sets a pattern and default value, saves, and reads it back on a real record.

## Leave it alone

- `packages/core/database`: 643 integration tests on a real database, with 22 source commits in the window. This is the right level for an ORM layer, and the tests are cheap enough to run everywhere.
- `plugin-workflow` (128 E2E tests): 92 source commits and a core business feature. The browser tests protect configuration flows that span the UI and the execution engine.
- `plugin-acl` (30 E2E, 155 integration): permissions are high-impact when wrong. The E2E layer is already thin, so keep it.

## Worth a look (low confidence)

- **The E2E suite may not be running.** All 319 E2E files are unchanged in 180 days, while `core/client` had 126 source commits. E2E runs only from `manual-e2e.yml` (manual trigger), never on pull requests. Either these are very resilient tests or nobody is running them often. The GitHub Actions run history would settle it; the API was rate-limited from here.
- **plugin-ai:** 134 source commits and 24,282 lines changed, with 84 integration and 0 E2E tests. Mocking the model provider is correct, but check whether anything exercises a real prompt-to-UI round trip.
- **core/cli:** 81 commits and 35,296 lines changed, covered by 882 tests that all classify as unit. Check whether anything runs the real CLI against a real app.
- **No CI data was supplied,** so there are no flakiness or timing numbers. Fix-commit counts weren't usable either: NocoBase uses `fix:` prefixes on about 85% of commits, so they don't separate risky code from normal work.

## Why-this-level annotations

```
client-v2 smoke suite: e2e because v2 is being rebuilt and is adopted by 90+ plugins. Revisit when v2 source churn drops below v1's.
plugin-data-source-main field settings: component for per-type menu behaviour; e2e for one field per family only. Revisit if settings menus are rebuilt on client-v2.
core/database: integration on a real database because the ORM is the boundary. Revisit only if a new dialect is added.
```

## Appendix: by package (top 15 by test count)

| Package | e2e | api | integration | component | unit | Source commits (180 d) |
| --- | --- | --- | --- | --- | --- | --- |
| core/client-v2 | 0 | 0 | 12 | 1,009 | 867 | 180 |
| core/flow-engine | 0 | 0 | 61 | 527 | 1,051 | 72 |
| core/client | 268 | 0 | 54 | 154 | 974 | 126 |
| plugin-flow-engine | 0 | 0 | 358 | 0 | 1,026 | 41 |
| plugin-workflow | 128 | 0 | 384 | 223 | 194 | 92 |
| core/cli | 0 | 0 | 0 | 0 | 882 | 81 |
| core/database | 0 | 0 | 643 | 0 | 39 | 22 |
| plugin-data-source-main | 423 | 0 | 199 | 0 | 2 | 6 |
| plugin-ai | 0 | 0 | 84 | 135 | 352 | 134 |
| plugin-file-manager | 3 | 0 | 87 | 55 | 101 | – |
| core/utils | 0 | 0 | 0 | 0 | 234 | – |
| plugin-ui-layout | 0 | 0 | 39 | 161 | 23 | – |
| core/server | 0 | 34 | 110 | 0 | 64 | 36 |
| plugin-acl | 30 | 0 | 155 | 6 | 4 | 11 |
| plugin-backups | 4 | 0 | 37 | 34 | 95 | – |

Counts are tests, not files. "–" means not measured.
