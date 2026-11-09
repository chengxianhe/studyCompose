#!/usr/bin/env bash
# Optional Claude adapter. The repository script and CI own the actual gates.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
input=$(cat)
if jq -e '.stop_hook_active == true' <<<"$input" >/dev/null 2>&1; then
  exit 0
fi
if [ -z "$(git status --porcelain --untracked-files=all)" ]; then
  exit 0
fi
# Include Python, scripts and CI changes too; never reuse an old success stamp.
if bash scripts/verify.sh all; then
  exit 0
fi
echo "自检未通过。请查看 .verification/ 日志；修实现，不放宽门禁。" >&2
exit 2
