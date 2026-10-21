"""Aggregate SlopCodeBench-style code-quality metrics from detekt XML reports.

Usage:
    python3 measure.py [REPO_DIR]            # run detekt in REPO_DIR (default: cwd) and print JSON
    python3 measure.py --history REV [REV..] # measure each revision in a temporary git worktree

Only the standard library is used. See README.md for metric definitions and caveats.
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

EROSION_CC = 10  # SlopCodeBench: functions with CC > 10 count toward structural erosion
CLONE_WINDOW = 6  # consecutive normalized lines treated as one clone unit

HERE = Path(__file__).resolve().parent
METRICS_CFG = HERE / "detekt-metrics.yml"

INIT_SCRIPT = """
gradle.afterProject { p ->
    p.plugins.withId("io.gitlab.arturbosch.detekt") {
        def ext = p.extensions.getByName("detekt")
        ext.config.setFrom(p.files(System.getenv("METRICS_CFG")))
        ext.ignoreFailures = true
        p.tasks.matching { it.name == "detekt" }.configureEach { t ->
            t.reports.xml.required.set(true)
        }
    }
}
"""

CC_RE = re.compile(r"complexity: (\d+)\)")
LEN_RE = re.compile(r"is too long \((\d+)\)")
FUNC_RE = re.compile(r"The function (\S+)")
EXCLUDED_NAME = re.compile(r"Preview\.kt$")


MEASURED_ROOTS = {"app", "feature", "core", "domain", "data"}


def is_measured(rel_path: str) -> bool:
    """Production app code only: no tests, previews, build output, build-logic or the architecture tests."""
    parts = Path(rel_path).parts
    if not parts or parts[0] not in MEASURED_ROOTS:
        return False
    if "src" not in parts or "main" not in parts[parts.index("src") + 1 :]:
        return False
    if "build" in parts:
        return False
    return EXCLUDED_NAME.search(rel_path) is None


def parse_reports(xml_files: list[Path], repo: Path) -> list[dict]:
    """Join CyclomaticComplexMethod and LongMethod findings into one record per function."""
    funcs: dict[tuple, dict] = {}
    for report in xml_files:
        for file_el in ET.parse(report).getroot().iter("file"):
            path = file_el.get("name", "")
            try:
                rel = str(Path(path).resolve().relative_to(repo.resolve()))
            except ValueError:
                continue
            if not is_measured(rel):
                continue
            for err in file_el.iter("error"):
                source = err.get("source", "")
                message = err.get("message", "")
                name = FUNC_RE.match(message)
                if name is None:
                    continue
                key = (path, err.get("line"), name.group(1))
                rec = funcs.setdefault(key, {"file": path, "name": name.group(1)})
                if source == "detekt.CyclomaticComplexMethod" and (m := CC_RE.search(message)):
                    rec["cc"] = int(m.group(1))
                elif source == "detekt.LongMethod" and (m := LEN_RE.search(message)):
                    rec["sloc"] = int(m.group(1))
    return [f for f in funcs.values() if "cc" in f and "sloc" in f]


def erosion_metrics(funcs: list[dict]) -> dict:
    """Erosion = share of total complexity mass (CC * sqrt(SLOC)) held by functions with CC > 10."""
    masses = [(f["cc"] * math.sqrt(f["sloc"]), f["cc"]) for f in funcs]
    total = sum(m for m, _ in masses)
    eroded = sum(m for m, cc in masses if cc > EROSION_CC)
    return {
        "functions": len(funcs),
        "total_function_sloc": sum(f["sloc"] for f in funcs),
        "max_cc": max((f["cc"] for f in funcs), default=0),
        "functions_cc_gt_10": sum(1 for _, cc in masses if cc > EROSION_CC),
        "erosion": round(eroded / total, 4) if total else 0.0,
    }


def normalize(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def clone_ratio(kotlin_files: list[Path]) -> dict:
    """Rough stand-in for the paper's verbosity: share of lines inside repeated 6-line windows.

    NOT comparable with the paper's number (that one uses 137 AST-grep rules plus structural clones).
    """
    total_lines = 0
    seen: dict[tuple, int] = {}
    windows: list[tuple[Path, int, tuple]] = []
    for path in kotlin_files:
        lines = [normalize(x) for x in path.read_text(encoding="utf-8").splitlines()]
        lines = [x for x in lines if x and not x.startswith(("import ", "package ", "//", "*", "/*"))]
        total_lines += len(lines)
        for i in range(len(lines) - CLONE_WINDOW + 1):
            win = tuple(lines[i : i + CLONE_WINDOW])
            seen[win] = seen.get(win, 0) + 1
            windows.append((path, i, win))
    covered: set[tuple[Path, int]] = set()
    for path, i, win in windows:
        if seen[win] > 1:
            covered.update((path, i + k) for k in range(CLONE_WINDOW))
    return {
        "code_lines": total_lines,
        "clone_lines": len(covered),
        "clone_ratio_approx": round(len(covered) / total_lines, 4) if total_lines else 0.0,
    }


def measured_kotlin_files(repo: Path) -> list[Path]:
    return sorted(p for p in repo.rglob("*.kt") if is_measured(str(p.relative_to(repo))))


def run_detekt(repo: Path) -> list[Path]:
    with tempfile.TemporaryDirectory() as tmp:
        init = Path(tmp) / "metrics-init.gradle"
        init.write_text(INIT_SCRIPT, encoding="utf-8")
        env = {**os.environ, "METRICS_CFG": str(METRICS_CFG)}
        for old in repo.rglob("build/reports/detekt/detekt.xml"):
            old.unlink()
        subprocess.run(
            ["./gradlew", "--init-script", str(init), "detekt", "--continue", "-q"],
            cwd=repo,
            env=env,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return sorted(repo.rglob("build/reports/detekt/detekt.xml"))


def measure(repo: Path) -> dict:
    reports = run_detekt(repo)
    if not reports:
        raise RuntimeError(f"no detekt reports produced in {repo}")
    funcs = parse_reports(reports, repo)
    return {**erosion_metrics(funcs), **clone_ratio(measured_kotlin_files(repo))}


def measure_history(repo: Path, revs: list[str]) -> list[dict]:
    results = []
    for rev in revs:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", rev], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()
        subject = subprocess.run(
            ["git", "log", "-1", "--format=%ad %s", "--date=short", sha],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "wt"
            subprocess.run(["git", "worktree", "add", "--detach", str(tree), sha], cwd=repo, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                try:
                    results.append({"rev": sha, "commit": subject, **measure(tree)})
                except RuntimeError as exc:
                    results.append({"rev": sha, "commit": subject, "error": str(exc)})
            finally:
                subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=repo, check=False,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="*", help="repo dir, or revisions with --history")
    parser.add_argument("--history", action="store_true", help="treat targets as git revisions")
    args = parser.parse_args()
    if args.history:
        out = measure_history(Path.cwd(), args.target)
    else:
        out = measure(Path(args.target[0]) if args.target else Path.cwd())
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
