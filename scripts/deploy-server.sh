#!/bin/bash

# 服务器部署脚本（后端）
# 在本地 Mac 上执行，通过 SSH 连接服务器执行部署命令

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 加载配置
if [ -f "$SCRIPT_DIR/deploy.env" ]; then
    source "$SCRIPT_DIR/deploy.env"
else
    echo -e "${RED}错误: 配置文件不存在${NC}"
    echo "请先复制配置文件: cp scripts/deploy.env.example scripts/deploy.env"
    echo "然后编辑 scripts/deploy.env 填入实际配置"
    exit 1
fi

# 默认值
SERVER_PORT=${SERVER_PORT:-22}
SSH_KEY_PATH=${SSH_KEY_PATH:-~/.ssh/github_deploy_key}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  服务器部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "服务器: $SERVER_USER@$SERVER_HOST:$SERVER_PORT"
echo "项目目录: $PROJECT_DIR"
echo ""

echo -e "${YELLOW}正在连接服务器并执行部署...${NC}"

ssh -i "$SSH_KEY_PATH" -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" << EOF
    set -e
    
    echo "进入项目目录..."
    cd $PROJECT_DIR
    
    echo "拉取最新代码..."
    git fetch origin main
    git reset --hard origin/main
    
    echo "停止旧容器..."
    docker compose down
    
    echo "构建并启动新容器..."
    docker compose up -d --build
    
    echo "清理未使用的镜像..."
    docker image prune -f
    
    echo ""
    echo "当前容器状态："
    docker compose ps
EOF

echo ""
echo -e "${GREEN}✅ 服务器部署完成！${NC}"

