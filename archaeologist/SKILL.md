---
name: archaeologist
description: >-
  Reconstruct the history of a project or codebase from its written record —
  commit logs, open and closed issues and pull requests, code review threads,
  Jira tickets, Confluence pages, Slack threads, meeting notes, ADRs, and
  story cards — to explain what happened and why. Use this skill whenever the
  user asks "why is this code like this", "what happened to feature X", "who
  decided this and when", "why was this approach abandoned", "reconstruct the
  history of", "when did we stop doing X", "what was the original intent",
  or wants a post-mortem, retrospective, or decision history for any project,
  including long-finished ones. Also trigger when the user asks to "dig into",
  "excavate", or "do archaeology on" a repo, module, decision, or incident.
---

# The Archaeologist

Reconstruct project history from primary written sources. The output is not a
list of commits — it is an evidence-backed account of **what happened and why**,
including the decisions, reversals, dead ends, and context that the surviving
code no longer shows.

## Core discipline: evidence, inference, and absence

Everything in a dig report belongs to one of three categories, and reports
must keep them visibly distinct:

1. **Evidence** — something the written record directly states. Always cite
   the source: commit SHA (short form), PR/issue number, Jira key, Confluence
   page title + date, Slack permalink or channel + date, meeting-note filename.
2. **Inference** — a conclusion drawn from evidence. Mark it as such and show
   the reasoning chain ("the revert in `a1b2c3d` landed 4 hours after issue
   #482 was opened, which strongly suggests...").
3. **Absence** — what the record does *not* say. Silence is a finding. If a
   major architectural change has no linked discussion anywhere, say so —
   "no written rationale survives" is often the most useful sentence in a
   report, because it tells the reader where institutional memory lives only
   in people's heads.

Never fabricate rationale. If motivation is unclear, present the competing
hypotheses with their supporting evidence and confidence levels. A wrong but
confident history is worse than an honest gap.

## The dig process

### Phase 1 — Survey (scope before digging)

Establish the research question and the site boundaries before touching any
source. Pin down:

- **Question**: what does the user actually want to know? "Why does the auth
  module use two token formats" is a different dig from "give me the history
  of the auth module."
- **Timeframe**: bound it if possible. `git log --reverse -- path/` gives the
  birth date of any path; the question usually implies an era.
- **Sources available**: which of git, GitHub/GitLab, Jira, Confluence,
  Slack, and local docs are reachable in this session? Note gaps up front —
  they become "absence" findings later.

Run `scripts/git_survey.sh <repo> [path]` for a fast aerial photograph of a
git repo: activity over time, contributor eras, hotspot files, merge/revert
density. Use it to decide where to put the trenches.

### Phase 2 — Excavation (mine the sources)

Work from the cheapest, most-structured source outward:

1. **Git history first** — it is complete, local, and timestamped. See
   `references/git-github.md` for the full recipe book: pickaxe searches
   (`git log -S/-G`), `--follow` for renames, blame-walking through rewrites,
   revert and merge forensics, and recovering deleted code.
2. **Issues and PRs second** — this is where the *why* usually lives. Closed
   and merged items matter more than open ones for archaeology. Review
   threads on old PRs are frequently the only surviving record of a design
   argument. `scripts/gh_dig.sh` wraps the useful `gh` queries; the reference
   file covers GraphQL for cross-references and timeline events.
3. **Trackers and wikis third** — Jira tickets and Confluence pages capture
   planning-stage intent that never reaches GitHub. See
   `references/jira-confluence.md` for JQL/CQL patterns and how to walk
   ticket link graphs (blocks / is-blocked-by / relates-to).
4. **Conversations last** — Slack threads and meeting notes are the richest
   and least structured source. They explain the human context: deadlines,
   disagreements, who pushed for what. See `references/slack-meetings.md`.

**Follow the cross-reference chain.** The highest-value artifacts are the
links between sources: a commit message citing a PR, a PR body citing a Jira
key, a Jira ticket citing a Confluence page, a Confluence page linking a
Slack thread. Each hop adds a layer of intent. When you find an identifier
(PR #, JIRA-123, a person's name, a feature codename), grep for it in every
other available source before moving on.

**Codenames and vocabulary drift.** Projects rename things. A feature called
"quiescence detection" in the code may have been "page-settle" in Slack and
"PROJ-441" in Jira. Build a small glossary of aliases as you dig and search
under all of them.

### Phase 3 — Stratigraphy (order the layers)

Merge every dated finding into one chronological sequence, regardless of
source. Then read it for structure:

- **Eras**: periods of consistent direction, usually bounded by a lead
  developer change, a rewrite, or an organizational event.
- **Pivot points**: moments where direction changed — look for reverts,
  long-dormant PRs suddenly closed, issue label sweeps, a burst of commits
  after silence.
- **Dead ends**: branches of effort that were abandoned. These rarely get an
  explicit burial notice; detect them by finding work that simply stops, then
  hunt for the discussion that killed it (often in a *different* source than
  the work itself).
- **Contradictions**: when sources disagree (a PR description says one thing,
  the Slack thread says another), record both. The disagreement is itself a
  finding — often the public rationale and the real rationale differ.

### Phase 4 — Interpretation and report

Choose the output format(s) — the user may want more than one; they compose
naturally with the narrative as the spine:

| Format | Template | Use when |
|---|---|---|
| Narrative report | `assets/templates/narrative-report.md` | "What happened and why" — the default |
| Timeline | `assets/templates/timeline.md` | Sequencing matters; incident/post-mortem style |
| Decision log | `assets/templates/decision-log.md` | Retro-fitting ADRs onto undocumented decisions |

Read the chosen template file(s) before writing — they define required
sections including the evidence register and confidence markers.

Every report ends with three fixed sections regardless of format:

- **Evidence register** — every source cited, with identifiers, so any claim
  can be re-verified.
- **Gaps in the record** — what could not be established and which missing
  source (private channel, deleted branch, departed person) would fill it.
- **Open questions** — what a follow-up dig or a human interview should ask.

## Working in constrained sessions

Archaeology is read-heavy. When running as a sub-agent, keep raw material in
your own context and return only the synthesized report — never dump raw logs
back to the caller. When context is tight, prefer `git log --format=` with
narrow fields over full output, pipe through the survey script's summarizers,
and excavate in targeted passes rather than reading whole histories.

## What the archaeologist does not do

This is a read-only role. Do not modify code, close issues, edit wiki pages,
or post to Slack during a dig. If remediation work is discovered (stale docs,
mislabeled issues), list it under Open questions for the user to act on.
