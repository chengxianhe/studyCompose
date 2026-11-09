#!/usr/bin/env bash
# One validation entry point for humans, agents and CI. No success cache.
set -euo pipefail
repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"
mode=${1:-android}
case "$mode" in
  android|platform|all|workflow) ;;
  *) echo "Usage: scripts/verify.sh [android|platform|all|workflow]" >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then
  echo "Unexpected arguments; validation gates cannot be overridden." >&2
  exit 2
fi

mkdir -p .verification
run_dir=$(mktemp -d "$repo_root/.verification/${mode}.XXXXXX")
printf '%s\n' "$mode" > "$run_dir/mode.txt"
before=$(python3 scripts/workspace_fingerprint.py)
printf '%s\n' "$before" > "$run_dir/fingerprint-before.txt"
git rev-parse HEAD > "$run_dir/head.txt"
git status --short --untracked-files=all > "$run_dir/status.txt"
echo "Verification: $mode; evidence: $run_dir"

validate() {
  git diff --check HEAD
  python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v
  if [ "$mode" = android ] || [ "$mode" = all ]; then
    ./gradlew --console=plain :konsistTest:test detekt lint test spotlessCheck :app:dependencyGuard assembleDebug
  fi
  if [ "$mode" = platform ] || [ "$mode" = all ]; then
    python3 -c 'import json; json.load(open(".mcp.json"))'
    (
      cd platform
      uv sync --locked
      uv run ruff check .
      uv run mypy --strict src tests
      uv run pytest
      uv run python -c 'import govplatform.mcp_server.server'
    )
  fi
}

# A subshell with errexit preserves failures inside validate, including pipelines.
set +e
(set -e; validate) 2>&1 | tee "$run_dir/output.log"
result=$?
set -e
after=$(python3 scripts/workspace_fingerprint.py)
printf '%s\n' "$after" > "$run_dir/fingerprint-after.txt"
if [ "$before" != "$after" ]; then
  echo "Workspace changed during verification; rerun against the final content." >&2
  result=1
fi
printf '%s\n' "$result" > "$run_dir/exit-code.txt"
echo "Verification exit: $result; evidence: $run_dir"
exit "$result"
