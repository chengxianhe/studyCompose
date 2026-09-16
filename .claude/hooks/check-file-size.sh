#!/usr/bin/env bash
# 目标文件超过 250 行则拒绝写入。退出码 2 = 阻止工具调用，stderr 回喂给模型。
#
# Write 工具的 tool_input 里带着完整的新内容，直接数它的行数——这样能拦住
# "新建一个超长文件"（磁盘上还没有这个文件，不能只看现有文件的行数）。
# Edit 工具只有局部 diff，没有整file的最终内容，退化成检查磁盘上现有文件的行数。
input=$(cat)
path=$(jq -r '.tool_input.file_path // empty' <<<"$input")
[ -z "$path" ] && exit 0

content=$(jq -r '.tool_input.content // empty' <<<"$input")
if [ -n "$content" ]; then
  lines=$(printf '%s' "$content" | wc -l)
else
  [ ! -f "$path" ] && exit 0
  lines=$(wc -l < "$path")
fi

if [ "$lines" -gt 250 ]; then
  echo "文件 $path 将有 $lines 行，超过 250 行上限。请先拆分，或把新逻辑放进新文件。" >&2
  exit 2
fi
exit 0
