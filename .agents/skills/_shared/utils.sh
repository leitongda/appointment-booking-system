#!/bin/bash

# 通用工具函数库
# 提供日志输出、颜色显示、确认提示等通用功能

# 颜色定义
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export PURPLE='\033[0;35m'
export CYAN='\033[0;36m'
export NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [ "${DEBUG:-false}" = "true" ]; then
        echo -e "${PURPLE}[DEBUG]${NC} $1"
    fi
}

# 确认提示
confirm_action() {
    local message=$1
    local default=${2:-N}  # 默认为 No

    if [ "$default" = "Y" ]; then
        read -p "$(echo -e ${CYAN}${message}${NC} [Y/n]: ")" -n 1 -r
        echo
        [[ $REPLY =~ ^[Nn]$ ]] && return 1 || return 0
    else
        read -p "$(echo -e ${CYAN}${message}${NC} [y/N]: ")" -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]] && return 0 || return 1
    fi
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查端口占用
check_port() {
    local port=$1
    lsof -i :"$port" >/dev/null 2>&1
}

# 获取项目根目录（优先 git 仓库根，回退到本文件上溯三级：_shared -> skills -> .agents）
get_project_root() {
    local root
    root="$(git rev-parse --show-toplevel 2>/dev/null)"
    if [ -n "$root" ]; then
        echo "$root"
    else
        local script_dir
        script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
        echo "$(cd "$script_dir/../../.." && pwd)"
    fi
}

# 检查文件是否存在
check_file_exists() {
    local file=$1
    if [ ! -f "$file" ]; then
        log_error "文件不存在: $file"
        return 1
    fi
    return 0
}

# 检查目录是否存在
check_dir_exists() {
    local dir=$1
    if [ ! -d "$dir" ]; then
        log_error "目录不存在: $dir"
        return 1
    fi
    return 0
}

# 显示分隔线
show_separator() {
    local char=${1:-=}
    local length=${2:-50}
    printf '%*s\n' "$length" '' | tr ' ' "$char"
}

# 显示标题
show_title() {
    local title=$1
    local width=${2:-50}
    local padding=$(((width - ${#title}) / 2))

    echo ""
    show_separator "=" "$width"
    printf "%${padding}s%s\n" "" "$title"
    show_separator "=" "$width"
    echo ""
}

# 执行命令并显示结果
run_cmd() {
    local cmd=$1
    local silent=${2:-false}

    log_debug "执行: $cmd"

    if [ "$silent" = "true" ]; then
        eval "$cmd" >/dev/null 2>&1
        return $?
    else
        eval "$cmd"
        return $?
    fi
}

# 检查上一个命令是否成功
check_last_cmd() {
    if [ $? -eq 0 ]; then
        return 0
    else
        log_error "命令执行失败"
        return 1
    fi
}

# 获取当前时间戳
get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# 创建目录（如果不存在）
ensure_dir() {
    local dir=$1
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        log_debug "创建目录: $dir"
    fi
}

# 获取文件大小（字节）
get_file_size() {
    local file=$1
    if [ -f "$file" ]; then
        stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# 格式化文件大小
format_size() {
    local bytes=$1
    if [ "$bytes" -lt 1024 ]; then
        echo "${bytes}B"
    elif [ "$bytes" -lt 1048576 ]; then
        echo "$((bytes / 1024))KB"
    elif [ "$bytes" -lt 1073741824 ]; then
        echo "$((bytes / 1048576))MB"
    else
        echo "$((bytes / 1073741824))GB"
    fi
}

# 检查 Docker 是否运行
check_docker_running() {
    docker info >/dev/null 2>&1
}

# 检查 Docker Compose 是否可用
check_docker_compose() {
    command_exists docker-compose || docker compose version >/dev/null 2>&1
}

# 获取 Docker Compose 命令
get_docker_compose_cmd() {
    if command_exists docker-compose; then
        echo "docker-compose"
    else
        echo "docker compose"
    fi
}

# 检查数据库连接
check_db_connection() {
    local host=${1:-localhost}
    local port=${2:-5432}
    local user=${3:-postgres}
    local db=${4:-hospital}

    psql -h "$host" -p "$port" -U "$user" -d "$db" -c "SELECT 1;" >/dev/null 2>&1
}

# 检查 Redis 连接
check_redis_connection() {
    local host=${1:-localhost}
    local port=${2:-6379}

    redis-cli -h "$host" -p "$port" ping >/dev/null 2>&1
}

# 导出所有函数供其他脚本使用
export -f log_info log_success log_warning log_error log_debug
export -f confirm_action command_exists check_port
export -f get_project_root check_file_exists check_dir_exists
export -f show_separator show_title run_cmd check_last_cmd
export -f get_timestamp ensure_dir get_file_size format_size
export -f check_docker_running check_docker_compose get_docker_compose_cmd
export -f check_db_connection check_redis_connection
