#!/bin/bash
# Flower 启动脚本 - Celery 监控工具

set -e

# 默认配置
FLOWER_PORT=${FLOWER_PORT:-5555}
FLOWER_BASIC_AUTH=${FLOWER_BASIC_AUTH:-}
CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://localhost:6379/0}

echo "Starting Flower on port ${FLOWER_PORT}..."
echo "Broker: ${CELERY_BROKER_URL}"

# 构建 flower 命令
FLOWER_CMD="celery -A app.celery_app flower"

# 添加端口配置
FLOWER_CMD="${FLOWER_CMD} --port=${FLOWER_PORT}"

# 添加 broker 配置
FLOWER_CMD="${FLOWER_CMD} --broker=${CELERY_BROKER_URL}"

# 添加基本认证（如果配置）
if [ -n "$FLOWER_BASIC_AUTH" ]; then
    FLOWER_CMD="${FLOWER_CMD} --basic_auth=${FLOWER_BASIC_AUTH}"
    echo "Basic authentication enabled"
fi

# 添加其他配置
FLOWER_CMD="${FLOWER_CMD} --max_tasks=10000"
FLOWER_CMD="${FLOWER_CMD} --db=/tmp/flower.db"

echo "Executing: ${FLOWER_CMD}"
exec ${FLOWER_CMD}
