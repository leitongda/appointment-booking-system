#!/bin/bash

# 日志格式化脚本
# 提供结构化的日志输出

# 日志级别
declare -A LOG_LEVELS=(
    [DEBUG]=0
    [INFO]=1
    [WARNING]=2
    [ERROR]=3
)

# 当前日志级别（可通过环境变量设置）
CURRENT_LOG_LEVEL=${LOG_LEVELS[${LOG_LEVEL:-INFO}]}

# 结构化日志输出
log_structured() {
    local level=$1
    local message=$2
    local context=${3:-}

    local timestamp=$(get_timestamp)
    local level_num=${LOG_LEVELS[$level]}

    if [ $level_num -lt $CURRENT_LOG_LEVEL ]; then
        return 0
    fi

    local color=""
    case "$level" in
        DEBUG)   color=$PURPLE ;;
        INFO)    color=$BLUE ;;
        WARNING) color=$YELLOW ;;
        ERROR)   color=$RED ;;
        SUCCESS) color=$GREEN ;;
    esac

    if [ -n "$context" ]; then
        echo -e "${color}[$timestamp] [$level]${NC} $message | $context"
    else
        echo -e "${color}[$timestamp] [$level]${NC} $message"
    fi
}

# 步骤日志
log_step() {
    local step=$1
    local total=$2
    local message=$3

    echo -e "${CYAN}[步骤 $step/$total]${NC} $message"
}

# 进度条显示
show_progress() {
    local current=$1
    local total=$2
    local width=${3:-50}
    local percent=$((current * 100 / total))
    local filled=$((width * current / total))
    local empty=$((width - filled))

    printf "\r["
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' ' '
    printf "] %d%%" "$percent"

    if [ $current -eq $total ]; then
        echo ""
    fi
}

# 表格输出
print_table() {
    local headers=("$@")
    local column_count=${#headers[@]}
    local separator=""

    # 计算每列宽度
    declare -a widths
    for i in $(seq 0 $((column_count - 1))); do
        widths[$i]=${#headers[$i]}
    done

    # 打印表头
    for i in $(seq 0 $((column_count - 1))); do
        printf "| %-${widths[$i]}s " "${headers[$i]}"
        separator="${separator}+$(printf '%*s' $((widths[$i] + 2)) '' | tr ' ' '-')"
    done
    printf "|\n"
    echo "${separator}+"

    # 从管道读取数据行（如果有的话）
    while IFS='|' read -ra row; do
        for i in $(seq 0 $((column_count - 1))); do
            printf "| %-${widths[$i]}s " "${row[$i]:-}"
        done
        printf "|\n"
    done
}

# 服务状态表格
print_service_status() {
    local service=$1
    local status=$2
    local details=${3:-}

    local status_icon=""
    local status_color=""

    case "$status" in
        running|up|healthy)
            status_icon="✓"
            status_color=$GREEN
            ;;
        stopped|down)
            status_icon="✗"
            status_color=$RED
            ;;
        warning|degraded)
            status_icon="⚠"
            status_color=$YELLOW
            ;;
        *)
            status_icon="?"
            status_color=$NC
            ;;
    esac

    printf "%-20s " "$service"
    echo -e "${status_color}${status_icon} ${status}${NC}"
    if [ -n "$details" ]; then
        printf "                    %-20s\n" "$details"
    fi
}

# 错误详情输出
print_error_details() {
    local error_code=$1
    local error_msg=$2
    local suggestion=${3:-}

    echo ""
    echo -e "${RED}╔════════════════════════════════════════╗${NC}"
    echo -e "${RED}║              错误详情                  ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}错误代码:${NC} $error_code"
    echo -e "${YELLOW}错误信息:${NC} $error_msg"
    if [ -n "$suggestion" ]; then
        echo ""
        echo -e "${CYAN}建议:${NC} $suggestion"
    fi
    echo ""
}

# 成功摘要输出
print_success_summary() {
    local title=${1:-"操作完成"}
    local items=("${@:2}")

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         $title                        ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""

    if [ ${#items[@]} -gt 0 ]; then
        for item in "${items[@]}"; do
            echo -e "${GREEN}  ✓${NC} $item"
        done
        echo ""
    fi
}

# 开始/结束标记
log_operation_start() {
    local operation=$1
    echo ""
    show_title "▶ $operation"
}

log_operation_end() {
    local operation=$1
    local status=${2:-success}

    echo ""
    if [ "$status" = "success" ]; then
        echo -e "${GREEN}▶ $operation - 完成${NC}"
    else
        echo -e "${RED}▶ $operation - 失败${NC}"
    fi
    echo ""
}

# 导出函数
export -f log_structured log_step show_progress
export -f print_table print_service_status
export -f print_error_details print_success_summary
export -f log_operation_start log_operation_end
