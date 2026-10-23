#!/usr/bin/env bash
# 后端单测包装脚本：供 CI/工作流从任意工作目录调用（pytest 依赖以 apps/server 为工作目录解析配置）
set -e
cd "$(dirname "$0")"
exec python3 -m pytest tests/unit -q --no-header "$@"
