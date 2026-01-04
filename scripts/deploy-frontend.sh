#!/bin/bash

# 前端构建并上传到服务器脚本
# 在本地 Mac 上执行

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
echo -e "${GREEN}  前端构建并上传脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "服务器: $SERVER_USER@$SERVER_HOST:$SERVER_PORT"
echo "项目目录: $PROJECT_DIR"
echo ""

# 进入项目根目录
cd "$PROJECT_ROOT"

# 构建前端应用
echo -e "${YELLOW}[1/5] 构建 admin...${NC}"
pnpm build:admin

echo -e "${YELLOW}[2/5] 构建 doctor...${NC}"
pnpm build:doctor

echo -e "${YELLOW}[3/5] 构建 patient-h5...${NC}"
pnpm build:patient-h5

echo -e "${YELLOW}[4/5] 构建 temp-registration...${NC}"
pnpm build:temp-registration

echo -e "${YELLOW}[5/5] 上传构建产物到服务器...${NC}"

# 上传各个应用的 dist 目录
echo "  上传 admin..."
scp -i "$SSH_KEY_PATH" -P "$SERVER_PORT" -r apps/admin/dist/* "$SERVER_USER@$SERVER_HOST:$PROJECT_DIR/apps/admin/dist/"

echo "  上传 doctor..."
scp -i "$SSH_KEY_PATH" -P "$SERVER_PORT" -r apps/doctor/dist/* "$SERVER_USER@$SERVER_HOST:$PROJECT_DIR/apps/doctor/dist/"

echo "  上传 patient-h5..."
scp -i "$SSH_KEY_PATH" -P "$SERVER_PORT" -r apps/patient-h5/dist/* "$SERVER_USER@$SERVER_HOST:$PROJECT_DIR/apps/patient-h5/dist/"

echo "  上传 temp-registration..."
scp -i "$SSH_KEY_PATH" -P "$SERVER_PORT" -r apps/temp-registration/dist/* "$SERVER_USER@$SERVER_HOST:$PROJECT_DIR/apps/temp-registration/dist/"

echo ""
echo -e "${GREEN}✅ 前端构建并上传完成！${NC}"
echo ""
echo "已更新的应用："
echo "  - admin"
echo "  - doctor"
echo "  - patient-h5"
echo "  - temp-registration"

