#!/bin/bash

# 服务器端脚本：拉取代码并重启服务
# 在服务器上直接执行

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目目录（可根据实际情况修改）
PROJECT_DIR=${PROJECT_DIR:-/www/hospital-booking}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  服务器更新脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "项目目录: $PROJECT_DIR"
echo ""

# 进入项目目录
cd "$PROJECT_DIR"

echo -e "${YELLOW}[1/4] 拉取最新代码...${NC}"
git fetch origin main
git reset --hard origin/main
echo "代码已更新到最新版本"

echo -e "${YELLOW}[2/4] 停止旧容器...${NC}"
docker compose down

echo -e "${YELLOW}[3/4] 构建并启动新容器...${NC}"
docker compose up -d --build

echo -e "${YELLOW}[4/4] 清理未使用的镜像...${NC}"
docker image prune -f

echo ""
echo -e "${GREEN}✅ 更新完成！${NC}"
echo ""
echo "当前容器状态："
docker compose ps

