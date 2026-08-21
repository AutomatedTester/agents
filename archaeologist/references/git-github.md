# Git & GitHub excavation recipes

Read this when digging into a git repository or GitHub project. Everything
here is read-only.

## Table of contents

1. [Git: finding when and why code changed](#git-when-why)
2. [Git: surviving renames and rewrites](#git-renames)
3. [Git: reverts, merges, and abandoned work](#git-reverts)
4. [Git: recovering deleted code](#git-deleted)
5. [GitHub: closed PR and issue mining with `gh`](#gh-mining)
6. [GitHub: timeline events and cross-references](#gh-timeline)
7. [Interpreting what you find](#interpretation)

<a name="git-when-why"></a>
## 1. Git: finding when and why code changed

**Pickaxe (`-S`)** — find every commit that added or removed a string. The
single most useful archaeology tool. Use it to find where a function,
constant, config key, or magic number entered and left the codebase:

```bash
git log -S 'retry_count' --oneline --date=short --format='%h %ad %an %s'
git log -S 'retry_count' -p -- src/net/        # with diffs, scoped to a path
```

**Regex pickaxe (`-G`)** — like `-S` but matches changed *lines* against a
regex; catches modifications, not just add/remove of the exact string:

```bash
git log -G 'timeout\s*=' --oneline -- config/
```

**Birth and death of a file or path:**

```bash
git log --reverse --oneline -- path/to/thing | head -3   # oldest first: birth
git log --diff-filter=D --oneline -- 'path/**'           # deletions under path
```

**Blame through time.** Current blame shows the last touch, which is often a
formatting sweep. Walk backwards past uninteresting commits:

```bash
git blame -w -C -C -C -L 40,60 file.py          # ignore whitespace, follow copies
git blame <suspect-commit>^ -- file.py -L 40,60  # blame BEFORE that commit
```

`-C -C -C` detects code moved between files — essential for finding the true
origin of copy-pasted or extracted code.

**Message archaeology.** Search commit messages themselves for vocabulary,
ticket keys, and names:

```bash
git log --all --grep='PROJ-441' --format='%h %ad %an %s' --date=short
git log --all -i --grep='quiescen' --format='%h %ad %s'
```

`--all` matters: rationale often lives on merged-then-deleted branches whose
commits are still reachable from merge commits.

<a name="git-renames"></a>
## 2. Git: surviving renames and rewrites

```bash
git log --follow --oneline -- new/path/file.py   # history across renames
git log --find-renames=40% --diff-filter=R --summary  # list rename events
```

If history looks suspiciously short, suspect: (a) a rename without
`--follow`, (b) a squash-merge workflow (the real history lived in a deleted
branch — go to the PR, see §5), or (c) a repo migration (look for an
"initial import" mega-commit; the pre-history lives in an older repo —
ask the user or check the README/wiki for the ancestor).

<a name="git-reverts"></a>
## 3. Git: reverts, merges, and abandoned work

Reverts are pivot-point markers. Find them and then find what they killed:

```bash
git log --grep='^Revert' --format='%h %ad %s' --date=short
git show <revert-sha> --format='%B' -s          # body names the reverted sha
```

For each revert, ask: how long did the original survive? Hours = broke the
build (mechanical). Weeks = worked but was rejected (political/architectural —
there is a discussion somewhere; find it).

**Merge forensics.** First-parent history shows the project's official
storyline; the second parent holds the feature branch's private history:

```bash
git log --first-parent --oneline               # the mainline narrative
git log --merges --format='%h %ad %s' --date=short -- path/
git log <merge-sha>^1..<merge-sha>^2 --oneline  # commits the merge brought in
```

**Dormancy detection.** A path whose commit histogram goes dense → silent is
a candidate dead end or a candidate "it just works now." Distinguish by
checking whether issues/PRs referencing it also went silent (dead end) or
continued (stable).

<a name="git-deleted"></a>
## 4. Git: recovering deleted code

```bash
git log --all --oneline -- path/that/no/longer/exists   # find last commit touching it
git show <sha>:path/that/no/longer/exists                # read the dead file
git log -S 'distinctive_string' --all                    # find deleted code by content
```

<a name="gh-mining"></a>
## 5. GitHub: closed PR and issue mining with `gh`

Closed items are the archive; always include them. Core searches:

```bash
gh pr list --state all --search 'quiescence' --json number,title,state,closedAt,author --limit 100
gh issue list --state all --search 'label:regression sort:created-asc' --json number,title,closedAt --limit 100
gh search prs --repo OWNER/REPO 'BiDi in:comments' --json number,title,url --limit 50
```

Full excavation of a single PR — description, review threads, and commits:

```bash
gh pr view 1234 --json title,body,author,createdAt,mergedAt,closedAt,reviews,comments
gh api repos/OWNER/REPO/pulls/1234/comments --paginate   # inline review comments (the design arguments)
gh pr view 1234 --json commits -q '.commits[].messageHeadline'
```

Inline review comments (`/pulls/N/comments`) are distinct from conversation
comments (`/issues/N/comments`) — fetch both; the inline ones carry the
line-level disagreements.

**Linking commits to PRs** (essential in squash-merge repos where the commit
message is the only surviving pointer):

```bash
gh api "repos/OWNER/REPO/commits/<sha>/pulls" -q '.[].number'
```

<a name="gh-timeline"></a>
## 6. GitHub: timeline events and cross-references

The timeline API records label changes, cross-references, closes, and
reopens — the administrative fossil record:

```bash
gh api repos/OWNER/REPO/issues/482/timeline --paginate \
  -q '.[] | {event, actor: .actor.login, created_at, source: .source.issue.number?}'
```

`cross-referenced` events reveal every issue/PR that ever mentioned this one,
including from other repos — this is how you walk the reference graph
outward. `closed` events carry the closing commit sha when closed by a
commit.

For bulk work, GraphQL is cheaper — `gh api graphql` with
`timelineItems(itemTypes: [CROSS_REFERENCED_EVENT])` on the issue object.

<a name="interpretation"></a>
## 7. Interpreting what you find

- **Commit message style is stratigraphy.** A shift from terse messages to
  conventional-commits, or the appearance of ticket keys, marks a process
  change — usually a new lead, a new tool, or a post-incident policy.
- **Timestamps carry timezone and cadence signals.** A burst of late-night
  commits before a date that later appears in a release tag = deadline crunch;
  corroborate in Slack/meeting notes before asserting it.
- **Bot noise.** Dependabot/renovate/CI commits can dominate histograms;
  filter with `--author` exclusions or `--invert-grep --grep='^chore(deps)'`
  before reading trends.
- **Who reviewed matters as much as who wrote.** A reviewer who repeatedly
  blocks a direction, then disappears from the reviewer list right before
  that direction lands, is a story — check whether they left the team
  (contributor era analysis) or were routed around (Slack).
