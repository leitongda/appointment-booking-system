#!/bin/bash

# ============================================================
# 医院挂号系统 - Celery 启动脚本
# 
# 使用方式：
#   ./scripts/start_celery.sh worker   # 启动 Worker
#   ./scripts/start_celery.sh beat     # 启动 Beat
#   ./scripts/start_celery.sh all      # 启动 Worker + Beat
#   ./scripts/start_celery.sh stop     # 停止所有 Celery 进程
#   ./scripts/start_celery.sh status   # 查看状态
# ============================================================

set -e

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# PID 文件路径
WORKER_PID_FILE="/tmp/celery_worker.pid"
BEAT_PID_FILE="/tmp/celery_beat.pid"

# 启动 Worker
start_worker() {
    log_info "启动 Celery Worker..."
    
    if [ -f "$WORKER_PID_FILE" ]; then
        if kill -0 $(cat "$WORKER_PID_FILE") 2>/dev/null; then
            log_warn "Worker 已在运行中 (PID: $(cat $WORKER_PID_FILE))"
            return 0
        fi
        rm -f "$WORKER_PID_FILE"
    fi
    
    celery -A app.celery_app worker \
        -l info \
        -c 4 \
        -Q default,scheduled,notification \
        --pidfile="$WORKER_PID_FILE" \
        --logfile=logs/celery_worker.log \
        --detach
    
    sleep 2
    if [ -f "$WORKER_PID_FILE" ]; then
        log_info "Worker 已启动 (PID: $(cat $WORKER_PID_FILE))"
    else
        log_error "Worker 启动失败"
        return 1
    fi
}

# 启动 Beat
start_beat() {
    log_info "启动 Celery Beat..."
    
    if [ -f "$BEAT_PID_FILE" ]; then
        if kill -0 $(cat "$BEAT_PID_FILE") 2>/dev/null; then
            log_warn "Beat 已在运行中 (PID: $(cat $BEAT_PID_FILE))"
            return 0
        fi
        rm -f "$BEAT_PID_FILE"
    fi
    
    celery -A app.celery_app beat \
        -l info \
        --pidfile="$BEAT_PID_FILE" \
        --logfile=logs/celery_beat.log \
        --detach
    
    sleep 2
    if [ -f "$BEAT_PID_FILE" ]; then
        log_info "Beat 已启动 (PID: $(cat $BEAT_PID_FILE))"
    else
        log_error "Beat 启动失败"
        return 1
    fi
}

# 停止 Worker
stop_worker() {
    log_info "停止 Celery Worker..."
    
    if [ -f "$WORKER_PID_FILE" ]; then
        if kill -0 $(cat "$WORKER_PID_FILE") 2>/dev/null; then
            kill $(cat "$WORKER_PID_FILE")
            log_info "Worker 已停止"
        else
            log_warn "Worker 进程不存在"
        fi
        rm -f "$WORKER_PID_FILE"
    else
        log_warn "Worker PID 文件不存在"
    fi
}

# 停止 Beat
stop_beat() {
    log_info "停止 Celery Beat..."
    
    if [ -f "$BEAT_PID_FILE" ]; then
        if kill -0 $(cat "$BEAT_PID_FILE") 2>/dev/null; then
            kill $(cat "$BEAT_PID_FILE")
            log_info "Beat 已停止"
        else
            log_warn "Beat 进程不存在"
        fi
        rm -f "$BEAT_PID_FILE"
    else
        log_warn "Beat PID 文件不存在"
    fi
}

# 查看状态
show_status() {
    echo "=============================================="
    echo "          Celery 服务状态"
    echo "=============================================="
    
    # Worker 状态
    echo -n "Worker: "
    if [ -f "$WORKER_PID_FILE" ] && kill -0 $(cat "$WORKER_PID_FILE") 2>/dev/null; then
        echo -e "${GREEN}运行中${NC} (PID: $(cat $WORKER_PID_FILE))"
    else
        echo -e "${RED}未运行${NC}"
    fi
    
    # Beat 状态
    echo -n "Beat:   "
    if [ -f "$BEAT_PID_FILE" ] && kill -0 $(cat "$BEAT_PID_FILE") 2>/dev/null; then
        echo -e "${GREEN}运行中${NC} (PID: $(cat $BEAT_PID_FILE))"
    else
        echo -e "${RED}未运行${NC}"
    fi
    
    echo "=============================================="
    
    # 显示活跃的 Worker
    echo ""
    echo "活跃的 Worker 节点："
    celery -A app.celery_app inspect active_queues 2>/dev/null || echo "无法获取 Worker 信息"
}

# 前台运行 Worker（用于调试）
run_worker_foreground() {
    log_info "前台运行 Celery Worker..."
    celery -A app.celery_app worker \
        -l info \
        -c 4 \
        -Q default,scheduled,notification
}

# 前台运行 Beat（用于调试）
run_beat_foreground() {
    log_info "前台运行 Celery Beat..."
    celery -A app.celery_app beat -l info
}

# 创建日志目录
mkdir -p logs

# 主函数
case "$1" in
    worker)
        if [ "$2" == "-f" ] || [ "$2" == "--foreground" ]; then
            run_worker_foreground
        else
            start_worker
        fi
        ;;
    beat)
        if [ "$2" == "-f" ] || [ "$2" == "--foreground" ]; then
            run_beat_foreground
        else
            start_beat
        fi
        ;;
    all)
        start_worker
        start_beat
        ;;
    stop)
        stop_worker
        stop_beat
        ;;
    restart)
        stop_worker
        stop_beat
        sleep 2
        start_worker
        start_beat
        ;;
    status)
        show_status
        ;;
    *)
        echo "使用方式: $0 {worker|beat|all|stop|restart|status}"
        echo ""
        echo "命令说明："
        echo "  worker    启动 Celery Worker（后台运行）"
        echo "  beat      启动 Celery Beat 调度器（后台运行）"
        echo "  all       启动 Worker 和 Beat"
        echo "  stop      停止所有 Celery 进程"
        echo "  restart   重启所有 Celery 进程"
        echo "  status    查看运行状态"
        echo ""
        echo "调试模式（前台运行）："
        echo "  $0 worker -f    前台运行 Worker"
        echo "  $0 beat -f      前台运行 Beat"
        exit 1
        ;;
esac

