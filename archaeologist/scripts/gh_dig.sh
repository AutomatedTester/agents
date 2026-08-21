#!/usr/bin/env bash
# gh_dig.sh — read-only GitHub excavation helpers built on the `gh` CLI.
# Requires: gh (authenticated), jq.
#
# Usage:
#   gh_dig.sh search  <owner/repo> "<query>"     # PRs+issues (all states) matching query
#   gh_dig.sh pr      <owner/repo> <number>      # full excavation of one PR
#   gh_dig.sh issue   <owner/repo> <number>      # issue + comments + timeline cross-refs
#   gh_dig.sh commit  <owner/repo> <sha>         # which PR(s) a commit landed through
set -euo pipefail

CMD="${1:?usage: gh_dig.sh <search|pr|issue|commit> <owner/repo> <arg>}"
REPO="${2:?missing owner/repo}"
ARG="${3:?missing query/number/sha}"

case "$CMD" in
  search)
    echo "== PRs (all states) matching: $ARG =="
    gh pr list -R "$REPO" --state all --search "$ARG" --limit 50 \
      --json number,title,state,author,createdAt,closedAt \
      --template '{{range .}}{{.number}}	{{.state}}	{{.createdAt}}	{{.author.login}}	{{.title}}
{{end}}'
    echo "== Issues (all states) matching: $ARG =="
    gh issue list -R "$REPO" --state all --search "$ARG" --limit 50 \
      --json number,title,state,createdAt,closedAt \
      --template '{{range .}}{{.number}}	{{.state}}	{{.createdAt}}	{{.title}}
{{end}}'
    ;;

  pr)
    echo "== PR #$ARG metadata =="
    gh pr view "$ARG" -R "$REPO" --json number,title,author,createdAt,mergedAt,closedAt,state,body \
      | jq -r '"#\(.number) [\(.state)] \(.title)\nauthor: \(.author.login)  created: \(.createdAt)  merged: \(.mergedAt // "-")\n\n--- description ---\n\(.body // "(empty)")"'
    echo; echo "== Reviews (verdicts) =="
    gh pr view "$ARG" -R "$REPO" --json reviews \
      | jq -r '.reviews[] | "\(.submittedAt)  \(.author.login)  \(.state)\n\(.body // "" | if .=="" then "" else "  "+. end)"'
    echo; echo "== Inline review comments (the design arguments) =="
    gh api "repos/$REPO/pulls/$ARG/comments" --paginate \
      | jq -r '.[] | "\(.created_at)  \(.user.login)  \(.path):\(.line // .original_line // "?")\n  \(.body | gsub("\r?\n"; "\n  "))"'
    echo; echo "== Conversation comments =="
    gh api "repos/$REPO/issues/$ARG/comments" --paginate \
      | jq -r '.[] | "\(.created_at)  \(.user.login)\n  \(.body | gsub("\r?\n"; "\n  "))"'
    echo; echo "== Commits in PR =="
    gh pr view "$ARG" -R "$REPO" --json commits \
      | jq -r '.commits[] | "\(.oid[0:9])  \(.messageHeadline)"'
    ;;

  issue)
    echo "== Issue #$ARG =="
    gh issue view "$ARG" -R "$REPO" --json number,title,author,createdAt,closedAt,state,labels,body \
      | jq -r '"#\(.number) [\(.state)] \(.title)\nauthor: \(.author.login)  created: \(.createdAt)  closed: \(.closedAt // "-")\nlabels: \([.labels[].name] | join(", "))\n\n--- body ---\n\(.body // "(empty)")"'
    echo; echo "== Comments =="
    gh api "repos/$REPO/issues/$ARG/comments" --paginate \
      | jq -r '.[] | "\(.created_at)  \(.user.login)\n  \(.body | gsub("\r?\n"; "\n  "))"'
    echo; echo "== Timeline: cross-references, closes, labels =="
    gh api "repos/$REPO/issues/$ARG/timeline" --paginate \
      | jq -r '.[] | select(.event=="cross-referenced" or .event=="closed" or .event=="labeled" or .event=="unlabeled" or .event=="reopened")
        | "\(.created_at // "?")  \(.event)  \(if .event=="cross-referenced" then "← #\(.source.issue.number) \(.source.issue.title)" elif .event=="labeled" or .event=="unlabeled" then .label.name else (.commit_id // "" | .[0:9]) end)"'
    ;;

  commit)
    echo "== PRs that carried commit $ARG =="
    gh api "repos/$REPO/commits/$ARG/pulls" \
      | jq -r '.[] | "#\(.number) [\(.state)] \(.title)  merged: \(.merged_at // "-")"'
    ;;

  *) echo "unknown command: $CMD" >&2; exit 1 ;;
esac
