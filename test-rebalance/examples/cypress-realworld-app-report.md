# Test rebalance: cypress-realworld-app

2026-10-04 · window: full available history (438 commits, 243 ignored as dependency/formatting sweeps) · CI data: 10 runs of **synthetic** JUnit XML for three files, made up to exercise the flakiness checks. Treat every CI number below as illustrative.

## Summary

The suite is evenly spread: 59 browser tests, 44 API tests and 46 integration tests over the data layer. The biggest win is in the transaction feed E2E file, where most tests check which records come back, which the API suite can answer in a fraction of the time. The date-range picker is the one place to resist downgrading: its library was swapped in 2025 and that's exactly the change a component test with stubs won't catch.

| Level | Files | Tests |
| --- | --- | --- |
| e2e | 12 | 59 |
| api | 9 | 44 |
| integration | 8 | 46 |
| component | 5 | 10 |
| unit | 1 | 6 |

The heuristic first labelled the eight `src/__tests__` files as unit tests. They seed and query the real file-backed database through `backend/database`, so they are integration tests.

## Move down

### cypress/tests/ui/transaction-feeds.spec.ts (data-filtering tests) → api (confidence: medium)

- **Question it answers:** do the personal, public and contacts feeds return the right transactions for a given date range, amount range and relationship?
- **Evidence:** the filter tests assert on `response.body.results` from intercepted requests, not on what's rendered. 11 test-file commits, the highest of any UI test. Synthetic CI: 7.5% failure rate, flaky date-range case, 53 s per run.
- **Replacement:** extend `cypress/tests/api/api-transactions.spec.ts` with date-range, amount-range, "mine only" and "contacts only" cases using `cy.request`. No browser, no scrolling.
- **Keep:** one E2E test per feed that loads, paginates and applies one filter through the UI.

### cypress/tests/ui/user-settings.spec.ts ("display user setting form errors") → component (confidence: medium)

- **Question it answers:** does the settings form show validation errors and disable submit for bad input?
- **Evidence:** pure client-side validation; no request is made. Subject code (`UserSettingsForm.tsx`, `user-routes.ts`) has 1 non-sweep commit and no fix commits; last changed 2024-08-27.
- **Replacement:** a `cy.mount` test of `UserSettingsForm` alongside the existing component tests.
- **Keep:** the "updates first name, last name, email and phone number" test at E2E. It proves the PATCH round trip and the sidebar refresh.

## Move up

### src/components/TransactionDateRangeFilter.cy.tsx → keep an E2E check alongside it (confidence: medium)

- **Question it answers:** can a user pick a date range and have the feed respond?
- **Evidence:** 2 fix-tagged commits on the subject, including the 2025-08-22 migration from `react-infinite-calendar` to `react-calendar`. The other (2022) was a test-setup change, not a product bug, which the script can't tell apart. Synthetic CI flags the E2E date filter as the flakiest case.
- **Why the current level isn't enough:** a calendar library swap changes real interaction (focus, clicks, rendering) in ways a mounted component test with a fixed viewport often misses. That's the argument for keeping the one E2E date-filter test above rather than moving all of them to the API.

No other upgrade candidates. Checked: mocked boundaries (`cy.intercept` stubs appear only in `transaction-feeds.spec.ts`); integration tests over the data layer (0 commits on most subject files); fix commits near mocked code (none).

## Leave it alone

- `cypress/tests/ui-auth-providers/*.spec.ts` (Auth0, Cognito, Google, Okta): the busiest UI tests (Auth0 8 commits, Cognito 7, Okta 5), and their fix commits come from identity SDK upgrades (Amplify v5 → v6, an Okta flow fix). Testing the real provider handshake is the point. They already offer a programmatic-login variant, so the slow path only runs where it matters.
- `src/__tests__/*.test.ts`: integration tests over a real data layer with no churn. Cheap, stable, doing their job.
- `cypress/tests/ui/auth.spec.ts`: the core sign-up/login journey. Expensive (synthetic 45 s per run) but it's the smoke test everything else depends on.

## Worth a look (low confidence)

- `cypress/tests/ui/transaction-view.spec.ts`: subject code has 13 non-sweep commits, the most in the suite, but the test file itself changed once. Either the test is resilient or it's not checking what changed. Worth opening against recent diffs to `transaction-routes.ts`.
- `cypress/tests/demo/cypress-studio.spec.ts`: a demo file. Check it's excluded from CI runs.

## Why-this-level annotations

```
cypress/tests/ui/transaction-feeds.spec.ts: e2e for load, paginate and one filter per feed only. Filter correctness lives in api-transactions.spec.ts. Revisit if feed UI is redesigned.
cypress/tests/ui/user-settings.spec.ts: e2e for the update round trip only. Validation lives in UserSettingsForm.cy.tsx. Revisit if validation moves server-side.
cypress/tests/ui-auth-providers/*: e2e because the provider handshake is the risk. Revisit if auth moves behind a single gateway.
```

## Appendix: per-file evidence

| File | Level | Test commits | Subject commits | Fix commits | Failure rate | Mean s |
| --- | --- | --- | --- | --- | --- | --- |
| cypress/tests/ui/transaction-feeds.spec.ts | e2e | 7 | 9 | 1 | 7.5% (synthetic) | 53.0 (synthetic) |
| cypress/tests/ui/auth.spec.ts | e2e | 2 | 6 | 1 | 3.3% (synthetic) | 45.4 (synthetic) |
| cypress/tests/ui/transaction-view.spec.ts | e2e | 1 | 13 | 1 | – | – |
| cypress/tests/ui/user-settings.spec.ts | e2e | 1 | 1 | 0 | – | – |
| cypress/tests/ui-auth-providers/auth0.spec.ts | e2e | 8 | 12 | 1 | – | – |
| cypress/tests/ui-auth-providers/cognito.spec.ts | e2e | 7 | 13 | 2 | – | – |
| cypress/tests/ui-auth-providers/okta.spec.ts | e2e | 5 | 7 | 2 | – | – |
| cypress/tests/api/api-users.spec.ts | api | 3 | 5 | 1 | 0% (synthetic) | 1.0 (synthetic) |
| src/components/TransactionDateRangeFilter.cy.tsx | component | 6 | 3 | 2 | – | – |
| src/__tests__/transactions.test.ts | integration | 1 | 13 | 1 | – | – |
| src/__tests__/bankaccounts.test.ts | integration | 1 | 0 | 0 | – | – |
