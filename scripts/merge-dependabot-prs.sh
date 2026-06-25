#!/usr/bin/env bash
# =============================================================================
# Dependabot 依赖升级合并脚本（PR + CI 门禁流程）
# =============================================================================
# 用途：在【联网机器】上执行，通过 gh CLI 走 PR 合并 25 个 Dependabot 升级。
#       让 CI（test.yml/security.yml）先验证后再合并，避免直接 push main 绕过门禁。
#
# 前置条件（联网机器）：
#   1. gh 已认证：            gh auth login  （或 export GH_TOKEN=xxx）
#   2. 本仓库已 clone 且干净： git status 应无改动
#   3. node/pnpm 已装：        pnpm -v 能输出版本
#
# 使用方法：
#   chmod +x scripts/merge-dependabot-prs.sh
#   # 全自动按推荐顺序跑（P0 → 绿色 → P1）：
#   ./scripts/merge-dependabot-prs.sh
#   # 只跑某一阶段（阶段见下方 STAGES）：
#   ./scripts/merge-dependabot-prs.sh green
#
# ⚠️ 重要：每一步都会真实创建/合并 PR 到 main，合并会触发生产部署。
#    核心依赖（cryptography/fastapi 等）合并前务必确认对应 PR 的 CI 全绿。
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ---------- 颜色 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
err()   { echo -e "${RED}✗${NC} $*" >&2; }
step()  { echo -e "\n${BLUE}▶ $*${NC}"; }
pause() { read -rp "$(echo -e "${YELLOW}$* (Enter 继续 / Ctrl-C 取消): ${NC}")"; }

# ---------- 前置检查 ----------
preflight() {
  step "前置检查"
  command -v gh >/dev/null || { err "未找到 gh CLI，请先 brew install gh 并 gh auth login"; exit 1; }
  gh auth status >/dev/null 2>&1 || { err "gh 未认证，请运行 gh auth login"; exit 1; }
  command -v pnpm >/dev/null || { err "未找到 pnpm"; exit 1; }
  [ -n "$(git status --porcelain)" ] && { err "工作区不干净，请先 git stash 或提交"; exit 1; }
  git fetch origin --prune --quiet
  ok "前置检查通过"
}

# ---------- 工具函数 ----------
# 列出 Dependabot 已开的 PR 编号（按包名匹配）。Dependabot 分支名即 PR 分支。
pr_number_for() {
  local pkg="$1"
  # gh pr list 返回 "编号\t标题"，取编号
  gh pr list --state open --author "app/dependabot" --search "$pkg" --json number,headRefName \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(next((p['number'] for p in d if '$pkg' in p['headRefName']), ''))" 2>/dev/null || true
}

# 合并一个依赖升级 PR：等 CI 绿 → squash 合并
merge_dep_pr() {
  local pkg="$1"   # 用于在分支名/PR 标题里定位
  local pr
  pr="$(pr_number_for "$pkg")"
  if [ -z "$pr" ]; then
    warn "未找到 $pkg 对应的 Dependabot PR（可能已被合并/关闭/重命名）。跳过。"
    return 0
  fi
  step "处理 PR #$pr  ($pkg)"
  echo "  PR: $(gh pr view "$pr" --json url -q .url)"

  # 同步本地 main，确保基于最新
  git checkout main --quiet
  git pull origin main --ff-only --quiet

  # 等 CI 跑完（最多 20 分钟）。squash merge。
  echo "  等待 CI 检查通过（最长 20 分钟）…"
  if gh pr checks "$pr" --watch --interval 30 --fail-fast 2>/dev/null; then
    ok "CI 通过"
  else
    err "CI 失败或超时。请去 GitHub 查看 PR #$pr。本脚本中止，已合并的不会回滚。"
    exit 1
  fi

  gh pr merge "$pr" --squash --delete-branch --quiet
  ok "已合并 PR #$pr ($pkg)"
}

# =============================================================================
# 阶段定义
# 每个条目："<Dependabot 分支名里的关键串>" （用于在 PR 列表里定位）
# =============================================================================

# P0：唯一确认带 CVE 修复（GHSA-4xgf-cpjx-pc3j，符号链接读取 secrets）
# 搭配 python-dotenv 一起验证 .env/secrets 加载链路
P0_PKGS=( "pydantic-settings-2.14.1" "python-dotenv-1.2.2" )

# 绿色批次：低风险，CI 绿即可合（pip dev / github-actions / npm 低风险）
GREEN_PKGS=(
  "pytest-asyncio-gte-1.4.0"   # dev，本仓库已满足 1.0 迁移前提
  "pytest-cov-gte-7.1.0"       # dev
  "aiosmtplib-5.1.1"
  "prometheus-client-0.25.0"
  "actions/checkout-6"         # ci
  "actions/setup-python-6"     # ci
  "actions/setup-node-6"       # ci（已显式 cache:pnpm，规避自动缓存变更）
  "babel/core-7.29.7"          # npm minor
  "pinyin-pro-3.28.1"          # npm minor（admin 运行时 import）
)

# P1：核心运行时 / 生产部署通道，需重点看 CI 且建议人工再验证
P1_PKGS=(
  "fastapi-0.136.3"            # 官方声明无破坏性（破坏在 0.137）
  "asyncpg-0.31.0"             # DB 核心驱动
  "cryptography-48.0.0"        # major×2，重点回归 RSA/微信回调/Fernet
  "sentry-sdk-2.61.0"          # 跨 34 版本
  "appleboy/ssh-action-1.2.5"  # 生产部署通道，建议手动 workflow_dispatch 验证一次
  "aquasecurity/trivy-action-0.36.0"  # 镜像扫描 exit-code:1 可能因新规则误红
  "eslint-plugin-react-hooks-7.1.1"   # major 4→7，React18+ESLint8，合后重跑 lint
  "vitejs/plugin-react-6.0.2"          # major 4→6，实测可与 vite6 共存
)

# 暂缓（不在本脚本自动合并，见文件末尾说明）：
#   - @tarojs/* 组 5 个：必须整体升级 + 补齐另外 ~7 个子包，不能单独合
#   - typescript-eslint/parser-8.60.0：parser/plugin 版本不一致，需配套升级 eslint-plugin

run_stage() {
  local stage_name="$1"; shift
  local pkgs=("$@")
  step "==== 阶段：$stage_name （${#pkgs[@]} 个 PR）===="
  pause "即将合并 $stage_name 的 ${#pkgs[@]} 个 PR，每个都会等 CI 绿再合"
  for pkg in "${pkgs[@]}"; do
    merge_dep_pr "$pkg"
  done
  ok "$stage_name 完成"
}

# =============================================================================
# 主流程
# =============================================================================
main() {
  preflight

  echo
  echo "本脚本将按推荐顺序合并 Dependabot 依赖升级 PR："
  echo "  P0   (安全修复):      ${#P0_PKGS[@]} 个   → ${P0_PKGS[*]}"
  echo "  绿色 (低风险):         ${#GREEN_PKGS[@]} 个 → ${GREEN_PKGS[*]}"
  echo "  P1   (核心，需重点验证): ${#P1_PKGS[@]} 个   → ${P1_PKGS[*]}"
  echo
  echo "暂不处理：@tarojs/* 组（需整体升级）、typescript-eslint/parser（需配套 plugin）。"
  echo "⚠️ 每次合并会触发 main 的生产部署（前端 SCP 到腾讯云 CVM + 后端 docker 重建）。"
  pause "确认要开始吗？"

  local stage="${1:-all}"
  case "$stage" in
    p0)    run_stage "P0 安全修复"   "${P0_PKGS[@]}" ;;
    green) run_stage "绿色低风险"     "${GREEN_PKGS[@]}" ;;
    p1)    run_stage "P1 核心(谨慎)"  "${P1_PKGS[@]}" ;;
    all)
      run_stage "P0 安全修复"   "${P0_PKGS[@]}"
      run_stage "绿色低风险"     "${GREEN_PKGS[@]}"
      run_stage "P1 核心(谨慎)"  "${P1_PKGS[@]}"
      ;;
    *) err "未知阶段：$stage（可选: p0 / green / p1 / all）"; exit 1 ;;
  esac

  step "全部完成"
  echo "已合并各 Dependabot PR 到 main。剩余未处理的："
  echo "  - @tarojs/* 组：见脚本末尾「暂缓项处理说明」"
  echo "  - typescript-eslint/parser：见脚本末尾"
  ok "done"
}

main "$@"


# =============================================================================
# 附录 A：暂缓项处理说明（@tarojs 组 / typescript-eslint）
# =============================================================================
#
# 【@tarojs/* 组（5 个 Dependabot 分支，4.1.9 → 4.2.0）】
#   为什么不能单独合：Taro 强制所有子包版本严格一致。这 5 个分支只升了 5 个子包，
#   还有 ~7 个仍钉在 4.1.9（cli / runtime / taro / components / shared / react /
#   webpack5-runner）。单独合任何一个 → 混合版本态 → 小程序构建崩。
#
#   正确做法（手动，不要用本脚本）：
#     1. git checkout -b chore/taro-4.2-upgrade origin/main
#     2. 手动把 3 个小程序 app（patient-miniapp / miniapp-instance / mini-appointment-miniapp）
#        的 package.json 里所有 @tarojs/* 从 4.1.9 改成 4.2.0
#     3. pnpm install           # 重新生成 lockfile，确保全部 @tarojs/* 统一到 4.2.0
#     4. pnpm -r --filter="@hospital/patient-miniapp" build:weapp   # 逐 app 验证构建
#        （以及 miniapp-instance / mini-appointment-miniapp 各跑一次）
#     5. 验证通过后开 PR 合并；同时关闭 5 个 Dependabot 分支对应的 PR
#
# 【typescript-eslint/parser-8.60.0（parser 5→8 major）】
#   为什么不能直接合：只升了 parser，配套的 @typescript-eslint/eslint-plugin 仍是 5.x，
#   版本不一致 → ESLint 报错。需等 Dependabot 开出 eslint-plugin 的升级 PR，或手动配套升。
#
#   正确做法：在 mini-appointment-miniapp/package.json 把 parser 和 eslint-plugin 同时升到 ^8.x，
#   pnpm install 后重跑 lint 验证。

# =============================================================================
# 附录 B：与功能分支 feat/third-party-integrations 的冲突处理
# =============================================================================
# 你的功能分支也在 requirements.txt 末尾【追加】了 playwright==1.58.0，并改了 pnpm-lock.yaml。
# Dependabot 分支与它的冲突情况（已用 git merge-tree 核实）：
#
#   pip 分支（改 requirements.txt，直接行替换）：【不冲突】
#     Dependabot 是 "-fastapi==0.115.12\n+fastapi==0.136.3" 的行替换，
#     功能分支是在文件【末尾追加】playwright——git merge 能自动合并两者。
#
#   dev 分支（改 requirements-dev.txt）：【不冲突】功能分支没动这个文件。
#
#   github-actions 分支（改 .github/）：【不冲突】功能分支没动 .github/。
#
#   npm 分支（改 pnpm-lock.yaml + package.json）：【可能冲突】
#     lockfile 是大段重排，易冲突。处理方式：
#       git merge origin/dependabot/npm_and_yarn/<pkg>
#       # 若 pnpm-lock.yaml 冲突：
#       git checkout --theirs pnpm-lock.yaml   # 先取 Dependabot 版本
#       pnpm install --frozen-lockfile         # 若报错，去掉 --frozen-lockfile 重生成
#       git add pnpm-lock.yaml package.json
#       git commit
#
#   推荐顺序：先合并功能分支到 main（开 PR），再在 main 上合 Dependabot PR，
#   这样 Dependabot PR 会自动 rebase 到含 playwright 的 main 上，冲突面最小。

# =============================================================================
# 附录 C：P1 核心依赖的人工验证清单（CI 绿之外的建议检查）
# =============================================================================
#   cryptography-48.0.0（major 46→48）：
#     - RSA 密钥签发（core/security.py）
#     - 微信支付回调解密（utils/wechat_callback.py）
#     - Fernet 邮件同步加解密
#   fastapi-0.136.3（跨 21 版本）：路由注册 / 鉴权 middleware / 依赖注入
#   asyncpg-0.31.0：DB 连接池 / 事务 / prepared statement（跑集成测试）
#   sentry-sdk-2.61.0（跨 34 版本）：触发一次真实错误，确认上报 + trace 正常
#   appleboy/ssh-action-1.2.5：手动 workflow_dispatch 触发一次部署，确认 SSH/脚本正常
#   aquasecurity/trivy-action-0.36.0：镜像扫描 exit-code:1 是否因新规则误红
#   eslint-plugin-react-hooks-7.1.1（major 4→7）：合后重跑 pnpm lint，看是否有新报错
#   vitejs/plugin-react-6.0.2（major 4→6）：apps/website 跑一次 pnpm build / pnpm dev
