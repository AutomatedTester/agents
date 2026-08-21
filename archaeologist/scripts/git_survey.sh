#!/usr/bin/env bash
# git_survey.sh — fast aerial survey of a git repo (or a path within it).
# Read-only. Produces compact summaries suitable for a constrained context.
#
# Usage: git_survey.sh <repo-dir> [path-within-repo]
set -eu   # no pipefail: pipelines ending in `head` would die on SIGPIPE

REPO="${1:?usage: git_survey.sh <repo-dir> [path]}"
SUBPATH="${2:-.}"
cd "$REPO"

PATHARG=()
[ "$SUBPATH" != "." ] && PATHARG=(-- "$SUBPATH")

section() { printf '\n== %s ==\n' "$1"; }

section "Site boundaries"
FIRST=$(git log --reverse --format='%ad %h %s' --date=short "${PATHARG[@]}" | head -1)
LAST=$(git log -1 --format='%ad %h %s' --date=short "${PATHARG[@]}")
COUNT=$(git rev-list --count HEAD "${PATHARG[@]}")
echo "scope:   ${SUBPATH}"
echo "first:   ${FIRST}"
echo "last:    ${LAST}"
echo "commits: ${COUNT}"

section "Activity by quarter (commit counts)"
git log --format='%ad' --date=format:'%Y-%m' "${PATHARG[@]}" \
  | sed 's/-\(0[1-3]\)$/-Q1/;s/-\(0[4-6]\)$/-Q2/;s/-\(0[7-9]\)$/-Q3/;s/-\(1[0-2]\)$/-Q4/' \
  | sort | uniq -c | awk '{printf "%s %5d %s\n",$2,$1,substr("##################################################",1,($1>50)?50:$1)}'

section "Contributor eras (first/last commit, count) — top 15"
git log --format='%an|%ad' --date=short "${PATHARG[@]}" \
  | awk -F'|' '{c[$1]++; if(!(f[$1])) ; if($2<f[$1] || f[$1]=="") f[$1]=$2; if($2>l[$1]) l[$1]=$2}
               END{for(a in c) printf "%6d  %s → %s  %s\n", c[a], f[a], l[a], a}' \
  | sort -rn | head -15

section "Hotspot files (most-changed) — top 15"
git log --format='' --name-only "${PATHARG[@]}" | grep -v '^$' | sort | uniq -c | sort -rn | head -15

section "Reverts"
git log --grep='^Revert' --format='%h %ad %s' --date=short "${PATHARG[@]}" | head -20
git log --grep='^Revert' --oneline "${PATHARG[@]}" | wc -l | xargs printf 'total reverts: %s\n'

section "Merge density (merges per quarter) — squash-merge repos show ~0"
git log --merges --format='%ad' --date=format:'%Y-%m' "${PATHARG[@]}" \
  | sed 's/-\(0[1-3]\)$/-Q1/;s/-\(0[4-6]\)$/-Q2/;s/-\(0[7-9]\)$/-Q3/;s/-\(1[0-2]\)$/-Q4/' \
  | sort | uniq -c | tail -12

section "Ticket-key vocabulary in commit messages (top 10 project keys)"
git log --format='%s %b' "${PATHARG[@]}" | grep -oE '[A-Z][A-Z0-9]{1,9}-[0-9]+' \
  | sed 's/-[0-9]*$//' | sort | uniq -c | sort -rn | head -10 || echo "(none found)"

section "Deleted paths (last 20 deletions in scope)"
git log --diff-filter=D --format='%ad %h' --date=short --name-only "${PATHARG[@]}" \
  | awk 'NF==2{d=$0} NF==1{print d"  "$0}' | head -20 || true

printf '\nSurvey complete. Suggested trenches: dense quarters, hotspot files, and any revert clusters above.\n'
