#!/usr/bin/env bash
# Stop 时运行项目自检；退出码 2 将失败信息回喂给 Claude。
# 仅源码或构建配置变更触发，成功戳记按当前工作区内容失效。
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
input=$(cat)
jq -e '.stop_hook_active == true' <<<"$input" >/dev/null 2>&1 && exit 0

needs_check=0
while IFS= read -r -d '' entry; do
  path=${entry:3}
  if [[ $path =~ \.(kt|kts|xml|toml|properties|json|pro)$ || $path =~ (^|/)gradlew?$ ]]; then
    needs_check=1
  fi
  if [[ ${entry:0:2} == *R* || ${entry:0:2} == *C* ]]; then
    IFS= read -r -d '' old_path || break
    if [[ $old_path =~ \.(kt|kts|xml|toml|properties|json|pro)$ || $old_path =~ (^|/)gradlew?$ ]]; then
      needs_check=1
    fi
  fi
done < <(git status --porcelain=v1 -z --untracked-files=all)
[ "$needs_check" -eq 0 ] && exit 0

fingerprint=$(
  set -o pipefail
  {
    git diff --binary HEAD || exit 2
    while IFS= read -r -d '' path; do
      printf '%s\0' "$path"
      hash=$(LC_ALL=C shasum < "$path") || exit 2
      printf '%s\n' "${hash%% *}"
    done < <(git ls-files --others --exclude-standard -z)
  } | LC_ALL=C shasum | awk '{print $1}'
) || exit 2
stamp=.claude/.self-check-passed
[ -f "$stamp" ] && [ "$(cat "$stamp")" = "$fingerprint" ] && exit 0

log=$(mktemp) || exit 2
if ./gradlew --console=plain :konsistTest:test detekt lint test spotlessCheck :app:dependencyGuard >"$log" 2>&1; then
  printf '%s\n' "$fingerprint" >"$stamp"
  rm -f "$log"
  exit 0
fi

echo "项目自检门禁失败：架构/detekt/lint 问题请修实现，绝不修改 Konsist 断言、detekt 配置或加 lint 抑制。" >&2
echo "spotlessCheck 失败请运行 spotlessApply；dependencyGuard 失败须确认依赖差异有意引入后再更新基线。" >&2
tail -n 60 "$log" >&2
rm -f "$log"
exit 2
