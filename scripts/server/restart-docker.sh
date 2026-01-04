#!/bin/bash

# 服务器端脚本：仅重启 Docker 服务（不拉代码）
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
echo -e "${GREEN}  Docker 重启脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "项目目录: $PROJECT_DIR"
echo ""

# 进入项目目录
cd "$PROJECT_DIR"

# 解析参数
REBUILD=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --rebuild|-r)
            REBUILD=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

if [ "$REBUILD" = true ]; then
    echo -e "${YELLOW}[1/3] 停止容器...${NC}"
    docker compose down

    echo -e "${YELLOW}[2/3] 重新构建并启动容器...${NC}"
    docker compose up -d --build

    echo -e "${YELLOW}[3/3] 清理未使用的镜像...${NC}"
    docker image prune -f
else
    echo -e "${YELLOW}[1/2] 停止容器...${NC}"
    docker compose down

    echo -e "${YELLOW}[2/2] 启动容器...${NC}"
    docker compose up -d
fi

echo ""
echo -e "${GREEN}✅ Docker 服务已重启！${NC}"
echo ""
echo "当前容器状态："
docker compose ps

echo ""
echo "提示：使用 --rebuild 或 -r 参数可重新构建镜像"
echo "示例：./restart-docker.sh --rebuild"

