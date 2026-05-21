"""
统一消息中心 Prometheus 指标

提供发送量、成功率、渠道延迟、重试率等监控指标。
"""
import time
import logging
from contextlib import contextmanager
from typing import Optional

from prometheus_client import Counter, Histogram, Gauge, REGISTRY

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 指标定义
# ---------------------------------------------------------------------------

# 发送量计数器（按渠道、消息类型、租户分组）
NOTIFICATION_SEND_TOTAL = Counter(
    "unified_notification_send_total",
    "Total notifications sent",
    ["channel", "message_type", "tenant_id", "status"],
)

# 发送延迟直方图（按渠道分组）
NOTIFICATION_SEND_LATENCY = Histogram(
    "unified_notification_send_latency_seconds",
    "Notification send latency in seconds",
    ["channel"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# 重试计数器
NOTIFICATION_RETRY_TOTAL = Counter(
    "unified_notification_retry_total",
    "Total notification retries",
    ["channel", "result"],
)

# 当前失败队列大小
NOTIFICATION_FAILED_QUEUE_SIZE = Gauge(
    "unified_notification_failed_queue_size",
    "Number of failed deliveries pending retry",
    ["tenant_id"],
)

# 去重命中计数器
NOTIFICATION_DEDUP_HITS = Counter(
    "unified_notification_dedup_hits_total",
    "Total deduplication hits",
    ["tenant_id"],
)

# 渠道降级计数器（按首选渠道、实际渠道、消息类型、租户分组）
NOTIFICATION_FALLBACK_TOTAL = Counter(
    "unified_notification_fallback_total",
    "Total channel fallback events",
    ["primary_channel", "actual_channel", "event_type", "tenant_id"],
)


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def record_send(
    channel: str,
    message_type: str,
    tenant_id: str,
    success: bool,
):
    """记录一次发送结果"""
    status = "success" if success else "failed"
    NOTIFICATION_SEND_TOTAL.labels(
        channel=channel,
        message_type=message_type,
        tenant_id=tenant_id,
        status=status,
    ).inc()


def record_dedup_hit(tenant_id: str):
    """记录一次去重命中"""
    NOTIFICATION_DEDUP_HITS.labels(tenant_id=tenant_id).inc()


def record_fallback(
    primary_channel: str,
    actual_channel: str,
    event_type: str,
    tenant_id: str,
):
    """记录一次渠道降级事件"""
    NOTIFICATION_FALLBACK_TOTAL.labels(
        primary_channel=primary_channel,
        actual_channel=actual_channel,
        event_type=event_type,
        tenant_id=tenant_id,
    ).inc()


def record_retry(channel: str, success: bool):
    """记录一次重试结果"""
    result = "success" if success else "failed"
    NOTIFICATION_RETRY_TOTAL.labels(channel=channel, result=result).inc()


def update_failed_queue_size(tenant_id: str, size: int):
    """更新失败队列大小"""
    NOTIFICATION_FAILED_QUEUE_SIZE.labels(tenant_id=tenant_id).set(size)


@contextmanager
def track_send_latency(channel: str):
    """上下文管理器：追踪发送延迟

    用法:
        with track_send_latency("sms"):
            await sms_channel.send(event, content)
    """
    start = time.monotonic()
    try:
        yield
    finally:
        duration = time.monotonic() - start
        NOTIFICATION_SEND_LATENCY.labels(channel=channel).observe(duration)
