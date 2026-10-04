#!/usr/bin/env python3
"""Gather evidence about each test file from git history and CI results.

Reads the JSON produced by inventory.py and adds, per test file:
  - churn of the test itself (commits, last change) in the window
  - its likely subject code (name match + files that change in the same commits)
  - churn of that subject code, size of recent changes, and fix-like commits
  - CI results from JUnit XML (runs, failures, flaky, mean duration), if given

Usage:
    python evidence.py <repo> --inventory inv.json [--days 180]
                       [--junit 'reports/**/*.xml' ...] > evidence.json

Everything here is evidence for a human decision. Nothing is changed in the repo.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

FIX_RX = re.compile(r"\b(fix(es|ed)?|bug|regression|hotfix|revert|broken|incident)\b", re.I)
TEST_PATH_RX = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs|e2e|cypress|integration)(/|$)|"
    r"(^|/)test_[^/]+$|_test\.\w+$|\.(test|spec|cy)\.\w+$|(Test|Tests|IT)\.\w+$", re.I)
# Commits that touch everything (dependency bumps, formatting sweeps, bots) say
# nothing about a specific feature's risk, so they are left out of churn.
MASS_SUBJECT_RX = re.compile(
    r"\b(deps?|dependenc(y|ies)|bump|renovate|dependabot|lint|eslint|prettier|format(ting)?|"
    r"typo|license|copyright|lockfile|upgrade (to )?(node|react|typescript))\b", re.I)
BOT_AUTHOR_RX = re.compile(r"\[bot\]|renovate|dependabot|github-actions", re.I)
NOISE_RX = re.compile(r"(lock|\.lock|package\.json|\.md|\.snap|\.ya?ml|\.json)$", re.I)


def git(repo, *args):
    out = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def load_history(repo, days=None):
    """Return list of commits: {sha, date, subject, files: {path: lines_changed}}."""
    since = [f"--since={days} days ago"] if days else []
    raw = git(repo, "log", *since, "--no-merges", "--numstat",
              "--format=@@%H%x1f%cs%x1f%an%x1f%s")
    commits, cur = [], None
    for line in raw.splitlines():
        if line.startswith("@@"):
            sha, date, author, subject = line[2:].split("\x1f", 3)
            cur = {"sha": sha, "date": date, "author": author, "subject": subject, "files": {}}
            commits.append(cur)
        elif line.strip() and cur is not None:
            parts = line.split("\t")
            if len(parts) == 3:
                add, rem, path = parts
                n = (int(add) if add.isdigit() else 0) + (int(rem) if rem.isdigit() else 0)
                cur["files"][path] = n
    return commits


def is_mass_commit(c, max_files):
    return (len(c["files"]) > max_files or BOT_AUTHOR_RX.search(c["author"])
            or MASS_SUBJECT_RX.search(c["subject"]))


def stem_tokens(test_path):
    base = os.path.basename(test_path)
    base = re.sub(r"\.(test|spec|cy)(?=\.)", "", base)
    base = re.sub(r"^test_|_test(?=\.)|(Test|Tests|IT|Spec)(?=\.)", "", base)
    base = os.path.splitext(base)[0]
    base = re.sub(r"^(api|ui)[-_]", "", base, flags=re.I)
    tokens = [t for t in re.split(r"[-_.]", base.lower()) if len(t) > 3]
    # singularise naively so "transactions" matches "transaction"
    return {t[:-1] if t.endswith("s") else t for t in tokens}


def shared_prefix(a, b):
    n = 0
    for x, y in zip(a.split("/"), b.split("/")):
        if x != y:
            break
        n += 1
    return n


def parse_junit(patterns, repo):
    cases = defaultdict(lambda: {"runs": 0, "failures": 0, "skipped": 0, "time": 0.0, "passed": 0})
    files_seen = 0
    for pat in patterns:
        for path in glob.glob(pat, recursive=True):
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError:
                continue
            files_seen += 1
            for suite in root.iter("testsuite"):
                suite_file = suite.get("file")
                for tc in suite.iter("testcase"):
                    key_file = tc.get("file") or suite_file or tc.get("classname") or ""
                    key = (key_file, tc.get("name", ""))
                    c = cases[key]
                    c["runs"] += 1
                    try:
                        c["time"] += float(tc.get("time") or 0)
                    except ValueError:
                        pass
                    if tc.find("failure") is not None or tc.find("error") is not None:
                        c["failures"] += 1
                    elif tc.find("skipped") is not None:
                        c["skipped"] += 1
                    else:
                        c["passed"] += 1
    return cases, files_seen


def match_ci(test_file, cases):
    """Match JUnit cases to a test file by path; fall back to an exact classname match."""
    stem = os.path.splitext(os.path.basename(test_file))[0]
    stem = re.sub(r"\.(test|spec|cy)$", "", stem)
    module = os.path.splitext(test_file)[0].replace("/", ".")
    out = []
    for (key_file, name), c in cases.items():
        k = key_file.replace("\\", "/")
        if not k:
            continue
        if "/" in k or re.search(r"\.(py|[cm]?[jt]sx?|java|kt|rb|go|cs)$", k):
            if k.endswith(test_file) or test_file.endswith(k.lstrip("./")):
                out.append((name, c))
        elif k == module or k.endswith("." + stem) or k == stem:
            out.append((name, c))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--junit", nargs="*", default=[])
    ap.add_argument("--cochange-top", type=int, default=5)
    ap.add_argument("--max-files-per-commit", type=int, default=25,
                    help="commits touching more files than this are treated as sweeps and ignored")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    inv = json.load(open(args.inventory))
    from datetime import date, timedelta
    history = load_history(repo)  # everything in the clone, newest first
    last_seen = {}
    for c in history:
        if c["author"] and BOT_AUTHOR_RX.search(c["author"]):
            continue
        for f in c["files"]:
            last_seen.setdefault(f, c["date"])
    cutoff = (date.today() - timedelta(days=args.days)).isoformat()
    all_commits = [c for c in history if c["date"] >= cutoff]
    last_change = lambda _repo, path: last_seen.get(path)
    commits = [c for c in all_commits if not is_mass_commit(c, args.max_files_per_commit)]
    all_files = git(repo, "ls-files").splitlines()
    source_files = [f for f in all_files if not TEST_PATH_RX.search(f) and not NOISE_RX.search(f)]

    by_file = defaultdict(list)
    for c in commits:
        for f in c["files"]:
            by_file[f].append(c)

    cases, junit_files = parse_junit(args.junit, repo)

    results = []
    for rec in inv["files"]:
        tf = rec["file"]
        tokens = stem_tokens(tf)
        name_matches = [f for f in source_files
                        if tokens and any(t in os.path.basename(f).lower() for t in tokens)]
        # in a monorepo, prefer matches from the test's own package
        name_matches.sort(key=lambda f: -shared_prefix(f, tf))
        if name_matches:
            best = shared_prefix(name_matches[0], tf)
            if best >= 2:  # test lives inside a package: stay in it
                name_matches = [f for f in name_matches if shared_prefix(f, tf) >= best - 1]

        co = Counter()
        for c in by_file.get(tf, []):
            for f in c["files"]:
                if f != tf and f in source_files:
                    co[f] += 1
        cochanged = [f for f, _ in co.most_common(args.cochange_top)]
        subject = sorted(set(name_matches[:15]) | set(cochanged))

        subj_commits = {c["sha"]: c for f in subject for c in by_file.get(f, [])}
        subj_lines = sum(c["files"].get(f, 0) for c in subj_commits.values() for f in subject)
        fixes = [c for c in subj_commits.values() if FIX_RX.search(c["subject"])]
        subj_last = max((last_change(repo, f) or "" for f in subject), default="") or None

        ci = match_ci(tf, cases) if cases else []
        ci_summary = None
        if ci:
            runs = sum(c["runs"] for _, c in ci)
            fails = sum(c["failures"] for _, c in ci)
            flaky = [n for n, c in ci if c["failures"] and c["passed"]]
            total_time = sum(c["time"] for _, c in ci)
            ci_summary = {
                "cases": len(ci),
                "runs": runs,
                "failures": fails,
                "failure_rate": round(fails / runs, 3) if runs else None,
                "flaky_cases": flaky[:10],
                "flaky_count": len(flaky),
                "mean_file_seconds": round(total_time / max(1, max(c["runs"] for _, c in ci)), 2),
            }

        results.append({
            **rec,
            "test_churn": {"commits": len(by_file.get(tf, [])), "last_changed": last_change(repo, tf)},
            "subject": {
                "files": subject,
                "how_found": {"name_match": name_matches[:15], "co_changed": cochanged},
                "commits": len(subj_commits),
                "lines_changed": subj_lines,
                "fix_commits": len(fixes),
                "fix_examples": [f"{c['date']} {c['subject'][:90]}" for c in fixes[:3]],
                "last_changed": subj_last,
            },
            "ci": ci_summary,
        })

    json.dump({
        "repo": repo,
        "window_days": args.days,
        "commits_in_window": len(all_commits),
        "commits_ignored_as_sweeps": len(all_commits) - len(commits),
        "junit_files_read": junit_files,
        "files": results,
    }, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
