#!/usr/bin/env bash
# 从 desktop-release/CHANGELOG.md 提取指定版本的公告段落（`## X.Y.Z` 起、下一个 `## ` 止，去首尾空行）。
# CI（Release 正文）与 publish-updates.sh（latest.json 的 notes → 应用内更新弹窗）共用，
# 保证两处公告一字不差。
#
# 用法：extract-notes.sh 1.1.0 → stdout；版本段落缺失或为空时退出 1（禁止空公告发版）。
# 只依赖 bash + awk（BSD/GNU 均可），自托管 Mac 与 ubuntu runner 都能跑。
set -euo pipefail

version=${1:?用法: $0 X.Y.Z}
changelog="$(cd "$(dirname "$0")" && pwd)/CHANGELOG.md"

notes=$(awk -v v="$version" '
  /^## / { inblock = ($2 == v); next }
  inblock { lines[++n] = $0 }
  END {
    first = 1; last = n
    while (first <= last && lines[first] ~ /^[[:space:]]*$/) first++
    while (last >= first && lines[last] ~ /^[[:space:]]*$/) last--
    for (i = first; i <= last; i++) print lines[i]
  }
' "$changelog")

if [ -z "$notes" ]; then
  echo "::error file=desktop-release/CHANGELOG.md::缺少版本 ${version} 的公告段落（需要 '## ${version} (YYYY-MM-DD)' 且内容非空）" >&2
  exit 1
fi

printf '%s\n' "$notes"
