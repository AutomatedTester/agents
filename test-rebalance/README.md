# test-rebalance

An Agent Skill that audits a test suite and recommends which tests should move between levels (end-to-end, API, integration, component, unit) based on how the risk around them has changed.

A test that was rightly an E2E test a year ago might be better as an API or integration test today. A feature that's being rebuilt might need its mocked tests back in a real browser. This skill looks at your code, your git history and your CI results, and writes a report with the evidence for each move, in both directions.

It never edits, moves or deletes tests. You get a report; you decide.

Companion to the newsletter piece *Your test pyramid isn't a monument. It's a portfolio.*

## Install

Claude Code:

This skill lives in the [agents](https://github.com/AutomatedTester/agents) repo. Clone it and copy the `test-rebalance` directory into your skills folder:

```bash
git clone https://github.com/AutomatedTester/agents /tmp/agents
cp -r /tmp/agents/test-rebalance ~/.claude/skills/test-rebalance
```

Start a new Claude Code session, then ask something like:

> Rebalance the tests in this repo. CI reports are in `reports/junit/`.

It also works anywhere that supports Agent Skills, as long as Python 3 and git are available.

## What it does

1. **Inventory** (`scripts/inventory.py`): finds test files and classifies them by the boundaries they cross: browser drivers (Selenium, WebdriverIO, Playwright, Cypress, Puppeteer, Nightwatch), HTTP clients, in-process app clients, real data layers, and mocks.
2. **Evidence** (`scripts/evidence.py`): measures churn on each test and on the code it covers, counts fix commits, and reads JUnit XML for failure rate, flakiness and duration. Dependency bumps, formatting sweeps and bot commits are filtered out so they don't drown the signal.
3. **Areas** (`scripts/areas.py`): for large repos, rolls churn up by directory alongside the tests at each level that cover it, and production incidents too if you supply them.
4. **Judgement**: Claude reads the candidate tests and weighs them against `references/signals.md`.
5. **Report**: a short markdown report following `references/report-template.md`, with a "leave it alone" section and suggested "why this level" annotations.

Example reports:

- `examples/nocobase-report.md`: a run against [NocoBase](https://github.com/nocobase/nocobase), a 2,000+ file TypeScript monorepo, including the project-helper mapping it needed.
- `examples/budibase-report.md`: a busy builder UI with no browser tests since 2023, and a ten-database API matrix.
- `examples/glpi-report.md`: a healthy PHP suite where the one move is browser tests duplicating integration tests.
- `examples/treeherder-report.md`: a lean suite that already upgraded on a rewrite, with stubbed browser tests whose recordings predate API changes.
- `examples/cypress-realworld-app-report.md`: a run against [cypress-realworld-app](https://github.com/cypress-io/cypress-realworld-app).

## Getting the most from it

- **Give it CI history.** Several runs of JUnit XML let it spot flakiness. One run only gives timings.
- **Tell it about production.** What alerts, synthetic checks and rollbacks would catch a regression, and optionally a CSV of incidents for `areas.py --incidents` (format in `references/incidents-format.md`, which an observability agent can follow to produce it). Fast detection supports moving tests down; repeated incidents support moving them up.
- **Tell it what's risky.** Critical journeys, recent incidents and planned rewrites are the inputs code can't provide.
- **Record the reasons.** Paste the suggested annotations into your tests or PRs. Next time you run it, those reasons are what you check against.

## Limitations

- Classification is heuristic. Projects with their own test helpers or base classes need a `--treat` mapping (the skill looks for these, and mappings apply to subclasses), and anything marked "inferred" is worth a review.
- Languages: Python, JavaScript/TypeScript, Java/Kotlin, C#, Ruby, Go and PHP test naming conventions are recognised.
- Production evidence is user-supplied. The scripts read an incident CSV but don't connect to any monitoring tool, and mapping incidents to code paths is up to you.
- "Subject code" is found by file names and co-change, which is a guess.
- Fix detection reads commit messages, so it can't tell a product bug from a test-setup fix, and it says little in repos that prefix most commits with `fix:`.

## Licence

Apache-2.0
