#!/usr/bin/env python3
"""Roll evidence up by area of the codebase.

For each source directory (to a chosen depth), report how much it changed in the
window and how many tests, by level, cover it (using each test's subject files
from evidence.py). This is the view that shows a heavily changing area with no
coverage above unit level, or a quiet area covered by many expensive tests.

With --incidents, also counts production incidents per area, so a quiet-looking
area that keeps breaking in production (or a busy one that never does) stands out.
The CSV needs a header row with `date` (YYYY-MM-DD) and `path` (a repo file or
directory the incident traces to); `severity` is optional. Export from your
incident tracker or error monitor and map each incident to a path first.

Usage:
    python areas.py <repo> --evidence evidence.json [--depth 3] [--top 25]
                    [--prefix packages/ --prefix src/] [--incidents incidents.csv]
Prints a markdown table; --json prints JSON instead.
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import evidence as ev  # noqa: E402

LEVELS = ["e2e", "api", "integration", "component", "unit"]
SERIOUS = {"1", "2", "sev1", "sev2", "p1", "p2", "critical", "high", "major"}


def load_incidents(path, cutoff):
    """Return [(path, is_serious)] for incidents on or after cutoff."""
    out = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            if not row.get("path") or row.get("date", "") < cutoff:
                continue
            out.append((row["path"].strip("/"), row.get("severity", "").lower() in SERIOUS))
    return out


def covers(area, path):
    """An incident path counts toward an area if one contains the other."""
    if area == "(repo root)":
        return "/" not in path
    return (path == area or path.startswith(area + "/")
            or area.startswith(path + "/"))


def area_of(path, depth):
    parts = path.split("/")
    # keep "packages/foo/src/bar" style paths readable: skip "src"-like noise in the count
    out, i = [], 0
    while parts[i:] and len(out) < depth:
        out.append(parts[i])
        i += 1
    a = "/".join(out[:-1] if len(parts) <= len(out) else out)
    return a or "(repo root)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--prefix", action="append", default=[],
                    help="only report areas under these path prefixes")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--incidents",
                    help="CSV of production incidents (date, path[, severity])")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    evd = json.load(open(args.evidence))
    days = evd["window_days"]
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    commits = [c for c in ev.load_history(args.repo)
               if c["date"] >= cutoff and not ev.is_mass_commit(c, 25)]

    churn = defaultdict(lambda: {"commits": set(), "lines": 0})
    for c in commits:
        for f, n in c["files"].items():
            if ev.TEST_PATH_RX.search(f) or ev.NOISE_RX.search(f):
                continue
            a = area_of(f, args.depth)
            churn[a]["commits"].add(c["sha"])
            churn[a]["lines"] += n

    cover = defaultdict(Counter)
    for r in evd["files"]:
        areas = {area_of(f, args.depth) for f in r["subject"]["files"]}
        for a in areas:
            cover[a][r["level"]] += r["test_count"]

    incidents = load_incidents(args.incidents, cutoff) if args.incidents else None

    rows = []
    for a in set(churn) | set(cover):
        if args.prefix and not any(a.startswith(p) for p in args.prefix):
            continue
        rows.append({
            "area": a,
            "commits": len(churn[a]["commits"]) if a in churn else 0,
            "lines": churn[a]["lines"] if a in churn else 0,
            **{lvl: cover[a][lvl] for lvl in LEVELS},
        })
        if incidents is not None:
            hits = [serious for p, serious in incidents if covers(a, p)]
            rows[-1]["incidents"] = len(hits)
            rows[-1]["serious"] = sum(hits)
    rows.sort(key=lambda r: (-r["commits"], -sum(r[l] for l in LEVELS)))
    rows = rows[: args.top]

    if args.json:
        json.dump(rows, sys.stdout, indent=2)
        print()
        return
    inc = incidents is not None
    print(f"| Area | Commits ({days} d) | Lines | " + " | ".join(LEVELS) +
          (" | Incidents | Serious" if inc else "") + " |")
    print("| --- | --- | --- | " + " | ".join("---" for _ in LEVELS) +
          (" | --- | ---" if inc else "") + " |")
    for r in rows:
        print(f"| {r['area']} | {r['commits']} | {r['lines']} | " +
              " | ".join(str(r[l]) for l in LEVELS) +
              (f" | {r['incidents']} | {r['serious']}" if inc else "") + " |")
    print("\nTest counts are tests whose subject files fall in the area; a test can count "
          "toward several areas.")
    if inc:
        print("Incidents are production incidents in the window whose path falls in the "
              "area (a parent directory counts too); Serious is sev1/sev2/critical.")


if __name__ == "__main__":
    main()
