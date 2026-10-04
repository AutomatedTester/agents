#!/usr/bin/env python3
"""Roll evidence up by area of the codebase.

For each source directory (to a chosen depth), report how much it changed in the
window and how many tests, by level, cover it (using each test's subject files
from evidence.py). This is the view that shows a heavily changing area with no
coverage above unit level, or a quiet area covered by many expensive tests.

With --incidents, also counts production incidents per area, so a quiet-looking
area that keeps breaking in production (or a busy one that never does) stands out.
The CSV needs a header row with `date` (YYYY-MM-DD) and `path` (a repo file or
directory the incident traces to). Optional: `severity` (sev1-sev4), `detected_by`
(alert, synthetic, customer, test, other) and `minutes_to_detect`. Rows with a
blank path are counted as unmapped and reported, not guessed. The full format and
how to map incidents to paths is in references/incidents-format.md.

Usage:
    python areas.py <repo> --evidence evidence.json [--depth 3] [--top 25]
                    [--prefix packages/ --prefix src/] [--incidents incidents.csv]
Prints a markdown table; --json prints JSON instead.
"""
import argparse
import csv
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import evidence as ev  # noqa: E402

LEVELS = ["e2e", "api", "integration", "component", "unit"]
SERIOUS = {"sev1", "sev2"}
SEVERITY = {
    "1": "sev1", "sev1": "sev1", "p1": "sev1", "critical": "sev1",
    "2": "sev2", "sev2": "sev2", "p2": "sev2", "high": "sev2", "major": "sev2",
    "3": "sev3", "sev3": "sev3", "p3": "sev3", "medium": "sev3", "moderate": "sev3",
    "4": "sev4", "sev4": "sev4", "p4": "sev4", "low": "sev4", "minor": "sev4",
}


def load_incidents(path, cutoff):
    """Return (rows, notes). rows: dicts with path, serious, detected_by, minutes.

    Incidents before cutoff are dropped. Anything that can't be used as given
    (blank path, bad date, unknown severity) is noted rather than silently ignored.
    """
    rows, unmapped, bad_dates, unknown_sev = [], 0, 0, Counter()
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            d = row.get("date", "")
            try:
                date.fromisoformat(d)
            except ValueError:
                bad_dates += 1
                continue
            if d < cutoff:
                continue
            if not row.get("path"):
                unmapped += 1
                continue
            sev = row.get("severity", "")
            norm = SEVERITY.get(sev.lower())
            if sev and norm is None:
                unknown_sev[sev] += 1
            try:
                minutes = float(row["minutes_to_detect"]) if row.get("minutes_to_detect") else None
            except ValueError:
                minutes = None
            rows.append({"path": row["path"].strip("/"), "serious": norm in SERIOUS,
                         "detected_by": row.get("detected_by", "").lower(),
                         "minutes": minutes})
    return rows, {"unmapped": unmapped, "bad_dates": bad_dates,
                  "unknown_severity": dict(unknown_sev)}


def covers(area, path):
    """An incident path counts toward an area if one contains the other."""
    if area == "(repo root)":
        return "/" not in path
    return (path == area or path.startswith(area + "/")
            or area.startswith(path + "/"))


def print_incident_notes(incidents, notes):
    """Say what the incident data couldn't tell us, so gaps aren't read as zeros."""
    print(f"\nIncident data: {len(incidents)} usable rows in the window.")
    if notes["unmapped"]:
        print(f"- {notes['unmapped']} incident(s) had no path and are not in the table above.")
    if notes["bad_dates"]:
        print(f"- {notes['bad_dates']} row(s) skipped: date is not YYYY-MM-DD.")
    for sev, n in notes["unknown_severity"].items():
        print(f"- {n} incident(s) with unrecognised severity {sev!r} counted as not serious.")
    mins = sorted(i["minutes"] for i in incidents if i["minutes"] is not None)
    if mins:
        print(f"- Minutes to detect: median {statistics.median(mins):g}, max {mins[-1]:g} "
              f"({len(mins)} incidents with data).")
    else:
        print("- No minutes_to_detect data, so detection speed is unknown.")


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

    incidents, notes = (load_incidents(args.incidents, cutoff)
                        if args.incidents else (None, None))

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
            hits = [i for i in incidents if covers(a, i["path"])]
            rows[-1]["incidents"] = len(hits)
            rows[-1]["serious"] = sum(i["serious"] for i in hits)
            rows[-1]["by_customer"] = sum(i["detected_by"] == "customer" for i in hits)
    rows.sort(key=lambda r: (-r["commits"], -sum(r[l] for l in LEVELS)))
    rows = rows[: args.top]

    if args.json:
        json.dump(rows, sys.stdout, indent=2)
        print()
        return
    inc = incidents is not None
    print(f"| Area | Commits ({days} d) | Lines | " + " | ".join(LEVELS) +
          (" | Incidents | Serious | Found by users" if inc else "") + " |")
    print("| --- | --- | --- | " + " | ".join("---" for _ in LEVELS) +
          (" | --- | --- | ---" if inc else "") + " |")
    for r in rows:
        print(f"| {r['area']} | {r['commits']} | {r['lines']} | " +
              " | ".join(str(r[l]) for l in LEVELS) +
              (f" | {r['incidents']} | {r['serious']} | {r['by_customer']}" if inc else "") + " |")
    print("\nTest counts are tests whose subject files fall in the area; a test can count "
          "toward several areas.")
    if inc:
        print("Incidents are production incidents in the window whose path falls in the "
              "area (a parent directory counts too); Serious is sev1/sev2; Found by users is "
              "incidents with detected_by=customer.")
        print_incident_notes(incidents, notes)


if __name__ == "__main__":
    main()
