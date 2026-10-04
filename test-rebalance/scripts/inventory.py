#!/usr/bin/env python3
"""Find test files in a repo and classify each by the boundaries it crosses.

Output is JSON on stdout: one record per test file with a guessed level
(e2e, api, integration, component, unit, unknown), the evidence for that guess,
and an approximate test count.

The classification is a heuristic based on imports and calls. It is a starting
point for the reviewer, not a verdict. Every record carries the matched signals
so a human (or Claude) can check the reasoning.

Usage:
    python inventory.py <repo_path> [--exclude DIR ...]
"""
import argparse
import json
import os
import re
import sys

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "out", "target",
    ".venv", "venv", "env", "__pycache__", ".tox", ".next", "coverage",
    "bazel-bin", "bazel-out", "bazel-testlogs",
}

TEST_FILE_PATTERNS = [
    re.compile(r"^test_.+\.py$"),
    re.compile(r".+_test\.py$"),
    re.compile(r".+\.(test|spec)\.[cm]?[jt]sx?$"),
    re.compile(r".+\.cy\.[jt]sx?$"),
    re.compile(r".+(Test|Tests|IT|Spec)\.(java|kt|cs|php)$"),
    re.compile(r".+_spec\.rb$"),
    re.compile(r".+_test\.go$"),
    re.compile(r".+\.feature$"),
]

# Ordered from "widest boundary" to "narrowest". Each entry is (signal name, regex).
SIGNALS = {
    "browser": [
        ("selenium", r"\bselenium\b|webdriver\.(Chrome|Firefox|Edge|Safari|Remote)|from selenium|org\.openqa\.selenium"),
        ("webdriverio", r"@wdio/|\bbrowser\.url\(|\bbrowser\.\$|\bawait \$\$?\(['\"`]"),
        ("playwright", r"@playwright/test|playwright\.sync_api|playwright\.async_api|\bpage\.goto\(|async \(\{[^}]*\bpage\b[^}]*\}\)"),
        ("cypress", r"\bcy\.(visit|get|contains|request|intercept|mount)\("),
        ("puppeteer", r"\bpuppeteer\b"),
        ("nightwatch", r"\bnightwatch\b"),
        ("php-webdriver/panther", r"Facebook\\WebDriver|Symfony\\Component\\Panther"),
        ("capybara", r"\bvisit\s+[a-z_]+_path|\bCapybara\b"),
    ],
    "component": [
        ("cy.mount", r"\bcy\.mount\("),
        ("testing-library", r"@testing-library/(react|vue|svelte|angular|dom)"),
        ("enzyme", r"\benzyme\b"),
        ("vue-test-utils", r"@vue/test-utils"),
    ],
    "http": [
        ("cy.request", r"\bcy\.request\("),
        ("supertest", r"\bsupertest\b"),
        ("requests", r"^\s*import requests|^\s*from requests\b"),
        ("httpx", r"\bhttpx\b"),
        ("rest-assured", r"\bRestAssured\b|io\.restassured"),
        ("axios/fetch", r"\baxios\.(get|post|put|delete|patch)\(|\bfetch\(['\"`]https?://"),
        ("playwright-request", r"\brequest\.(get|post|put|delete|patch)\(|APIRequestContext"),
        ("guzzle", r"GuzzleHttp\\Client|new\s+\\?GuzzleHttp"),
        ("net/http", r"\bhttptest\.NewServer|http\.(Get|Post)\("),
    ],
    "in_process_app": [
        ("flask/django/fastapi client", r"\.test_client\(|\bTestClient\(|django\.test\.Client|APIClient\("),
        ("spring mockmvc", r"\bMockMvc\b|@SpringBootTest|@WebMvcTest"),
    ],
    "real_dependency": [
        ("testcontainers", r"\btestcontainers\b|Testcontainers"),
        ("database", r"\bsqlalchemy\b.*create_engine|\bpsycopg|\bpymysql|\bknex\b|\bprisma\b|@DataJpaTest"),
        ("docker-compose", r"docker[-_]compose"),
    ],
    "data_layer": [
        ("imports data layer", r"(from|import|require\()\s*['\"][^'\"]*(database|/db['\"/]|repositor|/dao|persistence|/models/orm)[^'\"]*['\"]"),
        ("python data layer import", r"^\s*from\s+[\w.]*\b(db|database|repository|repositories|dao)\b[\w.]*\s+import"),
        ("seeds data", r"\bseed(Database|Db|_database|_db)\s*\(|\bloaddata\b|fixtures\.load"),
    ],
    "mock": [
        ("unittest.mock", r"unittest\.mock|\bmock\.patch|\bMagicMock\b|\bmocker\."),
        ("jest/vitest mock", r"\b(jest|vi)\.(mock|fn|spyOn)\("),
        ("sinon", r"\bsinon\b"),
        ("nock", r"\bnock\b"),
        ("msw", r"\bmsw\b|setupServer\("),
        ("responses/respx", r"@responses\.activate|\brespx\b"),
        ("cy.intercept stub", r"\bcy\.intercept\([^)]*,\s*\{|\bcy\.intercept\([^)]*fixture"),
        ("playwright route stub", r"\bpage\.route\(|\broute\.fulfill\("),
        ("wiremock", r"\bWireMock\b"),
        ("mockito", r"\bMockito\b|@Mock\b|@MockBean\b"),
        ("phpunit/mockery mock", r"->createMock\(|->getMockBuilder\(|->prophesize\(|\bMockery::"),
        ("gomock/testify mock", r"\bgomock\b|testify/mock"),
    ],
}

TEST_COUNT = re.compile(
    r"^\s*(def test_\w+|async def test_\w+|it\(|it\.only\(|test\(|test\.only\("
    r"|@Test\b|public function test\w+\(|func Test\w+\(|Scenario:|Scenario Outline:|\s*it ['\"])",
    re.MULTILINE,
)

PATH_HINTS = [
    ("e2e", re.compile(r"(^|/)_*(e2e|end-to-end|ui-tests?|acceptance|cypress/tests/ui)_*(/|$)", re.I)),
    ("api", re.compile(r"(^|/)(api|api-tests?|cypress/tests/api)(/|$)", re.I)),
    ("integration", re.compile(r"(^|/)(integration|it|int-tests?)(/|$)", re.I)),
    ("unit", re.compile(r"(^|/)(unit|unit-tests?)(/|$)", re.I)),
    ("component", re.compile(r"(^|/)(component|components)(/|$)|\.cy\.tsx?$", re.I)),
]


def is_test_file(name, rel_path):
    if any(p.match(name) for p in TEST_FILE_PATTERNS):
        return True
    return False


CLASS_RX = [
    re.compile(r"\bclass\s+(\w+)(?:<[^>]*>)?\s+extends\s+\\?([\w\\.]+)"),   # PHP, Java, Kotlin-ish, TS
    re.compile(r"^\s*class\s+(\w+)\(([\w., ]+)\)\s*:", re.M),             # Python
]


def build_class_graph(paths):
    """Map class name -> list of parent class names, from every file given."""
    graph = {}
    for full in paths:
        try:
            text = open(full, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for rx in CLASS_RX:
            for child, parents in rx.findall(text):
                for parent in re.split(r"[,\s]+", parents):
                    parent = parent.strip().split("\\")[-1].split(".")[-1]
                    if parent:
                        graph.setdefault(child, []).append(parent)
    return graph


def ancestors(cls, graph, seen=None):
    seen = seen or set()
    for parent in graph.get(cls, []):
        if parent not in seen:
            seen.add(parent)
            ancestors(parent, graph, seen)
    return seen


def inherited_signals(text, graph, treats):
    """Apply --treat rules to the classes a test file's classes inherit from."""
    found = {}
    for rx in CLASS_RX:
        for child, _ in rx.findall(text):
            for anc in ancestors(child, graph):
                for pattern, group in treats:
                    if re.fullmatch(pattern, anc):
                        found.setdefault(group, []).append(f"inherits {anc}")
    return found


def find_signals(text):
    found = {}
    for group, patterns in SIGNALS.items():
        hits = [label for label, rx in patterns if re.search(rx, text, re.MULTILINE)]
        if hits:
            found[group] = hits
    return found


def classify(signals, rel_path):
    hint = next((lvl for lvl, rx in PATH_HINTS if rx.search(rel_path)), None)
    reasons = []

    browser = signals.get("browser", [])
    # cy.request alone is an HTTP test even though it runs inside Cypress.
    browser_real = [b for b in browser if b != "cypress"] or (
        ["cypress"] if re.search(r"cypress", rel_path, re.I) and "component" not in signals and hint != "api" else []
    )
    if "component" in signals and not browser_real:
        level = "component"
        reasons.append("renders components in isolation: " + ", ".join(signals["component"]))
    elif browser_real and hint != "api":
        level = "e2e"
        reasons.append("drives a browser: " + ", ".join(browser_real or browser))
    elif "http" in signals or hint == "api":
        level = "api"
        reasons.append("talks HTTP to a running service: " + ", ".join(signals.get("http", ["path hint"])))
    elif "in_process_app" in signals or "real_dependency" in signals:
        level = "integration"
        reasons.append("exercises app wiring or real dependencies: " + ", ".join(
            signals.get("in_process_app", []) + signals.get("real_dependency", [])))
    elif "data_layer" in signals and not signals.get("mock"):
        level = "integration"
        reasons.append("uses the real data layer (inferred from imports, verify): " + ", ".join(signals["data_layer"]))
    elif hint:
        level = hint
        reasons.append(f"path suggests {hint}")
    elif "mock" in signals:
        level = "unit"
        reasons.append("isolated with mocks: " + ", ".join(signals["mock"]))
    else:
        level = "unit"
        reasons.append("no external boundary detected")

    mocked = signals.get("mock", [])
    if mocked and level in ("e2e", "api", "integration"):
        reasons.append("partially mocked: " + ", ".join(mocked))
    if hint and hint != level:
        reasons.append(f"note: path suggests {hint}, code suggests {level}")
    return level, reasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--exclude", nargs="*", default=[])
    ap.add_argument("--treat", action="append", default=[], metavar="REGEX=GROUP",
                    help="project-specific helper, e.g. 'createMockServer=in_process_app'. "
                         "GROUP is one of: " + ", ".join(SIGNALS))
    args = ap.parse_args()
    treats = []
    for spec in args.treat:
        rx, _, group = spec.rpartition("=")
        if group not in SIGNALS or not rx:
            sys.exit(f"bad --treat {spec!r}; expected REGEX=GROUP with GROUP in {list(SIGNALS)}")
        treats.append(("(?:" + rx + ")", group))
        # project helpers go first so they win over generic name-based guesses
        SIGNALS[group].insert(0, (f"project helper /{rx}/", r"\b(" + rx + r")\b"))

    repo = os.path.abspath(args.repo)
    skip = SKIP_DIRS | set(args.exclude)
    # First pass: every source-ish file, for the class hierarchy.
    code_files = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        code_files += [os.path.join(root, n) for n in files
                       if n.endswith((".php", ".py", ".java", ".kt", ".ts", ".tsx", ".cs"))
                       and ("test" in root.lower() or "test" in n.lower() or "spec" in n.lower())]
    graph = build_class_graph(code_files) if treats else {}

    records = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, repo)
            if not is_test_file(name, rel):
                continue
            try:
                with open(full, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            signals = find_signals(text)
            for group, hits in inherited_signals(text, graph, treats).items():
                signals.setdefault(group, [])
                signals[group] += sorted(set(hits) - set(signals[group]))
            level, reasons = classify(signals, rel)
            records.append({
                "file": rel,
                "level": level,
                "reasons": reasons,
                "signals": signals,
                "test_count": len(TEST_COUNT.findall(text)),
                "lines": text.count("\n") + 1,
            })

    records.sort(key=lambda r: r["file"])
    summary = {}
    for r in records:
        s = summary.setdefault(r["level"], {"files": 0, "tests": 0})
        s["files"] += 1
        s["tests"] += r["test_count"]
    json.dump({"repo": repo, "treat": args.treat, "summary": summary, "files": records}, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
