# agents
A repo of my agents I use regularly

| Directory | What it is | Contains |
| --- | --- | --- |
| `archaeologist/` | Reconstructs project history and the reasoning behind decisions from commits, issues, PRs, tickets and chat | Agent (`archaeologist.md`) and skill (`SKILL.md`, with `references/`, `scripts/`, `assets/`) |
| `witness/` | Captures the human context behind decisions as consensual, reviewed witness statements | Agent (`witness.md`) and a packaged skill (`witness.skill`) |
| `webdriver-spec/` | WebDriver BiDi specification researcher (agent name: `bidi-spec`) | Agent (`bidi-spec.md`) |
| `test-rebalance/` | Audits a test suite and recommends which tests should move between levels of the pyramid | Skill (`SKILL.md`, with `scripts/`, `references/`, `examples/`) |

## Installing

- **Agents** (the `.md` files with agent frontmatter): copy the file into `~/.claude/agents/`.
- **Skills** (directories containing `SKILL.md`): copy the whole directory into `~/.claude/skills/`, since the skill refers to its own `scripts/` and `references/`.
- **`witness.skill`**: a packaged skill archive; install it through your skill installer rather than copying it.

See each directory's README (where there is one) for details.
