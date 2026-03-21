#!/bin/bash

# 服务器端脚本：拉取代码、安装依赖、迁移数据库、重启服务
# SSH 到服务器后直接执行

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="/www/wwwroot/appointment-booking-system"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  服务器一键更新部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "项目目录: $PROJECT_DIR"
echo ""

# 1. 进入项目目录并拉取代码
echo -e "${YELLOW}[1/5] 拉取最新代码...${NC}"
cd "$PROJECT_DIR"

# 保护 uploads 目录：如果存在冲突，先丢弃本地更改
if git diff --name-only apps/server/uploads/ 2>/dev/null | grep -q .; then
    echo -e "${YELLOW}检测到 uploads 目录有本地更改，跳过这些文件...${NC}"
    git checkout -- apps/server/uploads/
fi

git pull
echo "代码已更新"

# 2. 安装 Python 依赖
echo -e "${YELLOW}[2/5] 安装 Python 依赖...${NC}"
cd apps/server
python3 -m pip install -r requirements.txt
echo "依赖安装完成"

# 3. 执行数据库迁移
echo -e "${YELLOW}[3/5] 执行数据库迁移...${NC}"
python3 -m alembic upgrade head
echo "数据库迁移完成"

# 4. 重新构建并启动容器
echo -e "${YELLOW}[4/5] 重新构建并启动 Docker 容器...${NC}"
cd "$PROJECT_DIR"
docker compose down
docker compose up -d --build

# 5. 清理并查看状态
echo -e "${YELLOW}[5/5] 清理未使用的镜像...${NC}"
docker image prune -f

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "当前容器状态："
docker compose ps
