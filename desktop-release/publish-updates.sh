#!/usr/bin/env bash
# 把已发布的 GitHub Release 上的桌面端产物同步到生产 nginx，并按端生成自动更新清单 latest.json。
#
# 为什么不用 tauri-action 自带的 latest.json：
#   ① 两端共用一个 Release，单份 latest.json 的平台键（darwin-*/windows-*）会互相覆盖；
#   ② 其下载地址指向 GitHub，国内机构直连不可靠；
#   ③ macOS 是 universal 包，需同时登记到 darwin-aarch64 与 darwin-x86_64（客户端按自身架构查键）。
#
# 用法：desktop-release/publish-updates.sh desktop-v1.1.0 [--dry-run]
#   --dry-run 只生成产物目录与 latest.json，不上传（路径会打印出来，便于肉眼核对）。
# 依赖：gh（已登录且对仓库有读权限）、python3、ssh/scp 可达生产机。
# 环境变量（可写在 desktop-release/.env.local，已 gitignore）：
#   DESKTOP_UPDATE_BASE_URL    对外更新源根地址，必须与 CI secret 同值且为 https，如 https://yy.xxx.com
#   DESKTOP_UPDATE_SSH         ssh 目标，如 root@106.52.195.26
#   DESKTOP_UPDATE_REMOTE_DIR  nginx 中 /desktop/updates 对应的物理目录，如 /www/wwwroot/yy.xxx.com/desktop/updates
#
# 服务器布局（nginx 直接静态托管；latest.json 需 no-cache，见 README）：
#   <REMOTE_DIR>/<admin|doctor>/latest.json
#   <REMOTE_DIR>/<admin|doctor>/<version>/<更新包与安装包>
# 历史版本目录保留，不自动清理：回滚 = 发更高版本号的包，updater 只装比当前新的版本。
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$here/.env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$here/.env.local"
  set +a
fi

tag=${1:?用法: $0 desktop-vX.Y.Z [--dry-run]}
dry_run=${2:-}
version=${tag#desktop-v}
# 允许 -rcN 预发布后缀：desktop-v1.1.0-rc1 的版本与公告按 1.1.0（与 package.json / CHANGELOG 对齐）
version="${version%%-*}"
: "${DESKTOP_UPDATE_BASE_URL:?缺少 DESKTOP_UPDATE_BASE_URL}"
: "${DESKTOP_UPDATE_SSH:?缺少 DESKTOP_UPDATE_SSH}"
: "${DESKTOP_UPDATE_REMOTE_DIR:?缺少 DESKTOP_UPDATE_REMOTE_DIR}"
base="${DESKTOP_UPDATE_BASE_URL%/}"
case "$base" in
  https://*) ;;
  *) echo "✗ DESKTOP_UPDATE_BASE_URL 必须是 https（Tauri updater 生产态强制 TLS）：$base" >&2; exit 1 ;;
esac

notes="$("$here/extract-notes.sh" "$version")"
pub_date="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
work="$(mktemp -d)"
keep_work=0
cleanup() { [ "$keep_work" = 1 ] || rm -rf "$work"; }
trap cleanup EXIT

echo "▶ 下载 Release $tag 的产物到 $work"
# 到 GitHub 的链路可能慢且不稳（百 MB 级产物曾中途 unexpected EOF），最多重试 5 次，--clobber 允许续传覆盖
download_ok=0
for attempt in 1 2 3 4 5; do
  if gh release download "$tag" --dir "$work" --clobber \
    --pattern '*.app.tar.gz' --pattern '*.app.tar.gz.sig' \
    --pattern '*-setup.exe' --pattern '*-setup.exe.sig' \
    --pattern '*.dmg'; then
    download_ok=1; break
  fi
  echo "  下载失败（第 $attempt 次），15 秒后重试…" >&2
  sleep 15
done
[ "$download_ok" = 1 ] || { echo "✗ Release 产物下载连续失败" >&2; exit 1; }

# pick <glob>：在下载目录里恰好匹配 1 个文件，否则报错退出（产物命名变了要立刻暴露，而不是发出错包）
pick() {
  local matches=()
  while IFS= read -r f; do matches+=("$f"); done < <(find "$work" -maxdepth 1 -name "$1" | sort)
  if [ "${#matches[@]}" -ne 1 ]; then
    echo "✗ 期望恰好 1 个匹配 '$1'，实际 ${#matches[@]} 个：${matches[*]:-无}" >&2
    exit 1
  fi
  printf '%s' "${matches[0]}"
}

stage="$work/stage"
for app in admin doctor; do
  if [ "$app" = admin ]; then product=HospitalAdmin; else product=HospitalDoctor; fi
  mac_bundle="$(pick "${product}*.app.tar.gz")"
  win_bundle="$(pick "${product}*-setup.exe")"
  dmg="$(pick "${product}*.dmg")"
  dir="$stage/$app/$version"
  mkdir -p "$dir"
  cp "$mac_bundle" "$mac_bundle.sig" "$win_bundle" "$win_bundle.sig" "$dmg" "$dir/"

  mac_url="$base/desktop/updates/$app/$version/$(basename "$mac_bundle")"
  win_url="$base/desktop/updates/$app/$version/$(basename "$win_bundle")"
  NOTES="$notes" python3 - "$version" "$pub_date" \
    "$mac_url" "$(cat "$mac_bundle.sig")" \
    "$win_url" "$(cat "$win_bundle.sig")" > "$stage/$app/latest.json" <<'PY'
import json, os, sys

version, pub_date, mac_url, mac_sig, win_url, win_sig = sys.argv[1:7]
mac = {"url": mac_url, "signature": mac_sig}
manifest = {
    "version": version,
    "notes": os.environ["NOTES"],
    "pub_date": pub_date,
    "platforms": {
        # universal 包同时服务两种架构的 Mac
        "darwin-aarch64": mac,
        "darwin-x86_64": mac,
        "windows-x86_64": {"url": win_url, "signature": win_sig},
    },
}
print(json.dumps(manifest, ensure_ascii=False, indent=2))
PY
  echo "✔ $app：$(basename "$mac_bundle") / $(basename "$win_bundle") / $(basename "$dmg") → latest.json"
done

if [ "$dry_run" = "--dry-run" ]; then
  keep_work=1
  echo "（dry-run）已生成，未上传。核对后可删除：$stage"
  find "$stage" -type f | sort
  exit 0
fi

echo "▶ 上传到 $DESKTOP_UPDATE_SSH:$DESKTOP_UPDATE_REMOTE_DIR"
for app in admin doctor; do
  remote="$DESKTOP_UPDATE_REMOTE_DIR/$app"
  ssh "$DESKTOP_UPDATE_SSH" "mkdir -p '$remote/$version'"
  scp -q "$stage/$app/$version"/* "$DESKTOP_UPDATE_SSH:$remote/$version/"
  # latest.json 最后上传并原子替换：客户端任何时刻读到的都是完整文件，且其指向的产物已经就位
  scp -q "$stage/$app/latest.json" "$DESKTOP_UPDATE_SSH:$remote/latest.json.tmp"
  ssh "$DESKTOP_UPDATE_SSH" "mv -f '$remote/latest.json.tmp' '$remote/latest.json'"
  echo "✔ $app 已发布：$base/desktop/updates/$app/latest.json"
done
