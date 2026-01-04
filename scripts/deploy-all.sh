#!/bin/bash

# 一键部署脚本
# 在本地 Mac 上执行，依次执行前端构建上传和服务器部署

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       一键部署脚本 - 全量部署           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# 检查配置文件
if [ ! -f "$SCRIPT_DIR/deploy.env" ]; then
    echo -e "${RED}错误: 配置文件不存在${NC}"
    echo "请先复制配置文件: cp scripts/deploy.env.example scripts/deploy.env"
    echo "然后编辑 scripts/deploy.env 填入实际配置"
    exit 1
fi

# 显示菜单
echo "请选择部署选项："
echo "  1) 全量部署（前端 + 后端）"
echo "  2) 仅部署前端"
echo "  3) 仅部署后端"
echo ""
read -p "请输入选项 [1/2/3，默认 1]: " choice
choice=${choice:-1}

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}========== 步骤 1/2: 前端构建并上传 ==========${NC}"
        bash "$SCRIPT_DIR/deploy-frontend.sh"
        
        echo ""
        echo -e "${YELLOW}========== 步骤 2/2: 服务器部署 ==========${NC}"
        bash "$SCRIPT_DIR/deploy-server.sh"
        
        echo ""
        echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║         ✅ 全量部署完成！               ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
        ;;
    2)
        echo ""
        bash "$SCRIPT_DIR/deploy-frontend.sh"
        ;;
    3)
        echo ""
        bash "$SCRIPT_DIR/deploy-server.sh"
        ;;
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

