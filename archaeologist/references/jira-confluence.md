# Jira & Confluence excavation recipes

Read this when the project used Atlassian tools. Access is via the Atlassian
MCP connector (Rovo) when available, or the `jira`/`confluence` CLIs or REST
API if the session has credentials. All operations are read-only: search,
fetch issue, fetch page, fetch comments. Never edit, transition, or comment
during a dig.

## Why this layer matters

Jira captures **planning-stage intent** — what the team believed before the
code existed — and Confluence captures **decision-stage intent** — proposals,
design docs, and meeting minutes. Comparing these against what actually
shipped (git/GitHub layer) is where the best findings live: the gap between
plan and outcome is the story.

## Jira mining

**Establish the key vocabulary first.** Find the project key(s) and any epic
or component names related to the question, then use them as grep targets in
the git/GitHub layer too.

Useful JQL patterns (via MCP search tool or API):

```
project = PROJ AND text ~ "quiescence" ORDER BY created ASC
project = PROJ AND status changed to Done during (2024-01-01, 2024-06-30)
project = PROJ AND resolution = "Won't Do" AND text ~ "auth" ORDER BY resolved DESC
issuekey in linkedIssues(PROJ-441)
```

High-value targets, in order:

1. **"Won't Do" / "Won't Fix" resolutions** — the graveyard of abandoned
   intent. The resolution comment (when present) is often the only written
   burial notice a dead end ever gets.
2. **Tickets with long comment threads** — sort candidates by comment count;
   arguments happen in comments, not descriptions.
3. **The link graph** — walk `blocks` / `is blocked by` / `relates to` /
   `duplicates` links outward from any central ticket. Duplicate-closures
   reveal how many times an idea was independently raised (a pressure gauge).
4. **Status-change history** — a ticket that ping-ponged between In Progress
   and Blocked marks an external dependency or a disagreement; the changelog
   timestamps let you line it up against Slack and commits.

**Epic drift.** Compare an epic's original description against its final
child-ticket set. Scope that was added late, or children moved to another
epic, mark pivot points.

## Confluence mining

CQL patterns:

```
siteSearch ~ "quiescence" AND type = page ORDER BY created ASC
type = page AND title ~ "RFC" AND space = ENG
type = page AND label = "meeting-notes" AND created >= "2024-01-01"
```

High-value targets:

1. **Design docs / RFCs / proposals** — read the **page history and inline
   comments**, not just the final text. The diff between draft versions shows
   which ideas were negotiated away, and inline comments name who objected.
2. **Meeting minutes** — search for the feature vocabulary and people's
   names. Minutes give you dates for verbal decisions that have no other
   written record.
3. **Orphaned pages** — a detailed design doc that no shipped code matches is
   a dead end fossil; hunt for the moment it diverged from reality.
4. **Page metadata** — creator, last-modifier, and watcher lists identify who
   owned an area even when the git history is dominated by someone else
   (spec-writer vs implementer split).

## Stitching Atlassian findings into the timeline

Every Jira changelog entry, comment, and Confluence version has a timestamp.
Normalize everything to UTC dates and merge into the master chronology from
Phase 3 of SKILL.md. When a Jira ticket and its implementing PR disagree on
rationale, cite both and flag the contradiction — do not silently pick one.
