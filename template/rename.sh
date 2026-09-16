#!/usr/bin/env bash
# 把这个 template 目录里的示例包名/项目前缀，换成你新项目的实际值。
# 用法：
#   ./rename.sh <新包名，如 com.acme.myapp> <新项目前缀，如 acmeMyapp>
#
# 新项目前缀会被用在两处：rootProject.name（原样保留大小写）、
# build-logic 约定插件 ID 前缀（自动转小写，Gradle 插件 ID 约定小写）。
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "用法: $0 <新包名> <新项目前缀>" >&2
  echo "例如: $0 com.acme.myapp acmeMyapp" >&2
  exit 1
fi

NEW_PACKAGE="$1"
NEW_PROJECT_ID="$2"
NEW_PROJECT_ID_LOWER=$(echo "$NEW_PROJECT_ID" | tr '[:upper:]' '[:lower:]')

OLD_PACKAGE="com.study.cc"
OLD_PROJECT_NAME="studyCompose"
OLD_PLUGIN_PREFIX="studycompose"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "在文本文件里替换字符串..."
# 只处理文本文件，不碰 gradle-wrapper.jar 等二进制文件。
find . -type f \( \
  -name "*.kt" -o -name "*.kts" -o -name "*.md" -o -name "*.json" \
  -o -name "*.yml" -o -name "*.yaml" -o -name "*.sh" -o -name "*.properties" \
  \) -not -path "./rename.sh" -print0 |
  while IFS= read -r -d '' file; do
    perl -pi -e "s/\Q${OLD_PACKAGE}\E/${NEW_PACKAGE}/g" "$file"
    perl -pi -e "s/\Q${OLD_PROJECT_NAME}\E/${NEW_PROJECT_ID}/g" "$file"
    perl -pi -e "s/\Q${OLD_PLUGIN_PREFIX}\E/${NEW_PROJECT_ID_LOWER}/g" "$file"
  done

echo "搬移包名对应的目录结构..."
OLD_PACKAGE_PATH=$(echo "$OLD_PACKAGE" | tr '.' '/')
NEW_PACKAGE_PATH=$(echo "$NEW_PACKAGE" | tr '.' '/')

find . -type d -path "*/${OLD_PACKAGE_PATH}" | while IFS= read -r dir; do
  base="${dir%$OLD_PACKAGE_PATH}"
  target="${base}${NEW_PACKAGE_PATH}"
  mkdir -p "$(dirname "$target")"
  mv "$dir" "$target"
  # 清理搬空后残留的旧包名父目录（比如 com/study 在 com/study/cc 搬走后就空了）
  old_parent=$(dirname "$dir")
  while [ "$old_parent" != "." ] && [ -d "$old_parent" ] && [ -z "$(ls -A "$old_parent")" ]; do
    rmdir "$old_parent"
    old_parent=$(dirname "$old_parent")
  done
done

echo "完成。接下来手动检查："
echo "  1. 把 :app include 进 settings.gradle.kts，:app/build.gradle.kts 参照原项目 app/build.gradle.kts 的写法接上约定插件和模块依赖"
echo "  2. applicationId / namespace 在 :app 自己的 build.gradle.kts 里配，这个脚本不会碰 :app"
echo "  3. 跑一遍 ./gradlew projects :konsistTest:test detekt 确认骨架是好的"
