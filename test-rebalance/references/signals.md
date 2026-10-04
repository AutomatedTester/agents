# Rebalancing signals

A test's level is a bet: the cost of running it at that level against the
confidence it buys. These signals say when the bet has changed. Weigh them
together. No single signal decides a move.

Levels, widest to narrowest: **e2e** (real browser, real stack) → **api** (HTTP
against a running service) → **integration** (several real units together, some
boundaries mocked or in-process) → **component** (UI in isolation) → **unit**.

## Downgrade signals (move a test down the stack)

| Signal | Evidence to look for | Weight |
| --- | --- | --- |
| Feature has stabilised | Subject code has few non-sweep commits in the window, no fix commits, last real change months ago | Strong |
| Browser isn't what's being tested | Assertions are on totals, records, API responses or state, not on rendering, layout, focus or navigation | Strong |
| A stable contract exists | Versioned API, OpenAPI/schema files, contract tests (Pact etc.), or an API-level test that already covers the same calls | Medium |
| Slow or flaky for reasons outside the team's control | CI flaky cases, timeouts, third-party sandboxes, email/SMS, OAuth providers | Strong |
| Journey is duplicated | Several e2e files repeat the same login/navigation before reaching the part they care about | Medium |
| High cost per test | Mean file time much higher than siblings at the same level | Supporting only |

A downgrade keeps the question the test asks. Say what the replacement test
asserts and which boundary gets mocked or bypassed. Recommend keeping at least
one thin e2e smoke path through any business-critical journey.

## Upgrade signals (move a test up the stack)

| Signal | Evidence to look for | Weight |
| --- | --- | --- |
| Feature is being rebuilt | Large `lines_changed` on subject code in the window, new framework imports, renamed or moved components | Strong |
| Mocked boundary is lying | Fix commits touching code on the far side of a mock this test uses; mock fixtures much older than the code they stand in for | Strong |
| Business risk went up | User says so (new key customer, payments, compliance, a recent incident). Ask if unknown | Strong, user-supplied |
| Browser behaviour matters again | Accessibility work, cross-browser bugs, new browser versions, rendering or focus fixes in history | Medium |
| Stubs older than the API they stand in for | Fixtures, HAR recordings or `cy.intercept` bodies last changed long before recent commits to the matching serializer or endpoint; fields added or removed since. Check whether the fixture is missing a field the API now returns | Strong if the UI reads the drifted field, medium otherwise |
| No coverage above a churning area | Subject code churns heavily but only unit or component tests touch it | Medium |

## Scope, not level

Sometimes the expensive part isn't the level but the breadth: the same API suite
run against ten databases or five browsers on every PR. If the code that varies
by target is quiet, suggest a scope change (one or two targets per PR, the full
matrix on merge) rather than a level change. If it's busy, leave it.

## Leave it alone

Say so explicitly when a test is in the right place. Common cases: a thin e2e
smoke test of a critical journey; a flaky test whose flakiness is the product's
fault (fix the bug, not the level); tests where evidence is missing. Missing
evidence is never a reason to move a test.

## Confidence

- **High**: two or more strong signals agree and nothing contradicts them.
- **Medium**: one strong signal, or several supporting ones.
- A cheap check that guards a stub (a fixture/serializer contract test) is often
  a better "upgrade" than moving the test itself to a real backend.
- **Low**: inferred classification, thin history, or no CI data. List these
  separately as "worth a look", never as recommendations.
