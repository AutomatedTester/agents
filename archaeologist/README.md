# The Archaeologist — agent + skill

A forensic project historian for Claude Code. Reconstructs what happened and
why from commit logs, open/closed issues and PRs, review threads, Jira,
Confluence, Slack, meeting notes, and story cards — at any point in a
project's life, including long after it finished. Strictly read-only.

Two artifacts, designed as a pair:

| Artifact | What it is | Why |
|---|---|---|
| `agents/archaeologist.md` | Claude Code sub-agent | Context isolation: digs are read-heavy; raw material stays in the sub-agent's context, only the synthesized report returns |
| `archaeologist/` (or `archaeologist.skill`) | Skill folder | Carries the methodology, source-mining reference guides, survey/mining scripts, and the three report templates |

## Install

**Skill** — either save the `.skill` file via the Save skill button in
Claude, or copy the folder:

```bash
# user-level (all projects)
cp -r archaeologist ~/.claude/skills/

# or project-level
cp -r archaeologist <repo>/.claude/skills/
```

**Agent:**

```bash
# user-level
mkdir -p ~/.claude/agents && cp agents/archaeologist.md ~/.claude/agents/

# or project-level
mkdir -p <repo>/.claude/agents && cp agents/archaeologist.md <repo>/.claude/agents/
```

Make the scripts executable after copying:

```bash
chmod +x ~/.claude/skills/archaeologist/scripts/*.sh
```

## Requirements

- `git`, `bash`, `jq` for the scripts; `gh` (authenticated) for GitHub mining
- Jira/Confluence and Slack layers use those MCP connectors when present;
  the dig degrades gracefully and records unreachable sources as gaps

## Use

Invoke explicitly:

```
> Use the archaeologist to work out why the auth module has two token formats.
> @archaeologist — reconstruct the history of the BiDi quiescence work and produce a decision log.
```

Or let it trigger automatically — the agent description advertises itself for
"why is this like this?", "what happened to X?", post-mortems, timelines, and
decision histories.

Output formats (composable): narrative report, timeline, and retro-fitted
decision log (RDR entries). Every report ends with an evidence register,
gaps in the record, and open questions.

## Tuning

- **Model**: the agent pins `model: sonnet` for cost; change to `opus` for
  gnarly digs (deep "why was this architecture abandoned" questions across
  many sources).
- **Tools**: the agent's tool list is deliberately read-only (`Read, Grep,
  Glob, Bash, WebFetch`). The read-only rule is also enforced in its prompt;
  keep both if you edit.
- **MCP tools**: if you name your Atlassian/Slack MCP tools in the agent's
  `tools:` list, list only the read/search tools, never the write ones.
