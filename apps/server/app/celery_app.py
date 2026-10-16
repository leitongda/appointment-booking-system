"""
Celery 应用配置
用于定时任务调度和异步任务处理
"""
from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from app.core.config import settings

# 创建 Celery 应用
celery_app = Celery(
    "hospital_booking",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery 配置
celery_app.conf.update(
    # 时区配置
    timezone="Asia/Shanghai",
    enable_utc=False,
    
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 任务结果配置
    result_expires=3600,  # 任务结果过期时间（1小时）
    task_track_started=True,
    
    # 任务重试配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Worker 配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # 任务超时配置
    task_soft_time_limit=300,  # 软超时：5分钟后抛出 SoftTimeLimitExceeded
    task_time_limit=600,  # 硬超时：10分钟后强制终止任务
    
    # 队列配置
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("scheduled", routing_key="scheduled"),
        Queue("notification", routing_key="notification"),
    ),
    task_default_queue="default",
    task_default_routing_key="default",
    
    # 任务路由
    task_routes={
        "app.tasks.blacklist_task.*": {"queue": "scheduled"},
        "app.tasks.schedule_task.*": {"queue": "scheduled"},
        "app.tasks.notification_task.*": {"queue": "notification"},
        "app.tasks.email_hook_task.*": {"queue": "notification"},
        "app.tasks.wechat_task.*": {"queue": "default"},
        "app.tasks.cleanup_task.*": {"queue": "scheduled"},
        "app.tasks.cleanup_login_history.*": {"queue": "scheduled"},
        "app.tasks.unified_message_cleanup_task.*": {"queue": "scheduled"},
        "app.tasks.unified_message_retry_task.*": {"queue": "notification"},
        "app.tasks.operation_log_task.*": {"queue": "default"},
        "app.tasks.behavior_log_task.*": {"queue": "default"},
        "app.tasks.session_event_task.*": {"queue": "scheduled"},
        "app.tasks.screenshot_task.*": {"queue": "scheduled"},
        "app.tasks.payment_task.*": {"queue": "scheduled"},
        "app.tasks.payment_reconciliation.*": {"queue": "scheduled"},
        "app.tasks.refund_sync.*": {"queue": "scheduled"},
        "app.tasks.suspension_processing_task.*": {"queue": "scheduled"},
        "app.tasks.approval_task.send_approval_notification": {"queue": "notification"},
        "app.tasks.approval_task.check_approval_timeouts": {"queue": "scheduled"},
        "app.tasks.approval_task.advance_after_auto_approve": {"queue": "default"},
        "app.tasks.approval_task.auto_reject_after_timeout": {"queue": "default"},
        "app.tasks.approval_task.transfer_after_timeout": {"queue": "default"},
        "app.tasks.follow_up_task.mark_overdue_task": {"queue": "scheduled"},
        "app.tasks.follow_up_task.send_follow_up_reminders": {"queue": "notification"},
        "app.tasks.lowcode_deploy_task.*": {"queue": "default"},
        "app.tasks.attendance_stat_task.*": {"queue": "scheduled"},
        "app.tasks.attendance_alert_task.*": {"queue": "scheduled"},
        "app.tasks.attendance_cleanup_task.*": {"queue": "scheduled"},
    },
    
    # Beat 调度器配置（定时任务）
    beat_schedule={
        # 黑名单自动解禁 - 每小时执行
        "blacklist-auto-release": {
            "task": "app.tasks.blacklist_task.auto_release_blacklist_task",
            "schedule": crontab(minute=0),  # 每小时整点
            "options": {"queue": "scheduled"},
        },
        
        # 预约提醒调度器 - 每10分钟检查（三级提醒：24h/2h/30min）
        "appointment-reminder-scheduler": {
            "task": "app.tasks.notification_task.send_appointment_reminder_scheduler",
            "schedule": crontab(minute="*/10"),  # 每10分钟
            "options": {"queue": "notification"},
        },

        # 候补递补卡死探测 - 每10分钟（递补 task 崩溃未回退 PROCESSING 的告警兜底）
        "waitlist-promotion-stuck-reconcile": {
            "task": "app.tasks.waitlist_promotion_task.reconcile_stuck_promotions",
            "schedule": crontab(minute="*/10"),  # 每10分钟
            "options": {"queue": "scheduled"},
        },

        # 预约提醒（旧版兼容）- 已禁用，由新版 appointment-reminder-scheduler 替代
        # "appointment-reminder-legacy": {
        #     "task": "app.tasks.notification_task.send_appointment_reminder_task",
        #     "schedule": crontab(minute="*/30"),
        #     "options": {"queue": "notification"},
        # },
        
        # 爽约自动检测 - 每30分钟检查
        "no-show-auto-mark": {
            "task": "app.tasks.blacklist_task.mark_no_show_appointments_task",
            "schedule": crontab(minute="*/30"),  # 每30分钟
            "options": {"queue": "scheduled"},
        },
        
        # 排班自动生成 - 每天凌晨2点
        "schedule-auto-generate": {
            "task": "app.tasks.schedule_task.auto_generate_schedules_task",
            "schedule": crontab(hour=2, minute=0),  # 每天凌晨2:00
            "options": {"queue": "scheduled"},
        },
        
        # 微信 Token 刷新 - 每2小时
        "wechat-token-refresh": {
            "task": "app.tasks.wechat_task.refresh_wechat_token_task",
            "schedule": crontab(minute=0, hour="*/2"),  # 每2小时
            "options": {"queue": "default"},
        },
        
        # 数据清理 - 每天凌晨3点
        "data-cleanup": {
            "task": "app.tasks.cleanup_task.cleanup_expired_data_task",
            "schedule": crontab(hour=3, minute=0),  # 每天凌晨3:00
            "options": {"queue": "scheduled"},
        },

        # 登录历史清理 - 每天凌晨3:15（与数据清理错开）
        "login-history-cleanup": {
            "task": "cleanup_login_history",
            "schedule": crontab(hour=3, minute=15),  # 每天凌晨3:15
            "options": {"queue": "scheduled"},
        },

        # 租户用量统计 - 每天凌晨1点
        "tenant-record-daily-usage": {
            "task": "app.tasks.tenant_usage_task.record_daily_usage",
            "schedule": crontab(hour=1, minute=0),  # 每天凌晨1:00
            "options": {"queue": "scheduled"},
        },

        # 平台经营看台 - 门店每日经营指标预聚合（每天凌晨2:30，补算近3天）
        "store-metrics-daily-aggregate": {
            "task": "app.tasks.store_metric_task.aggregate_store_daily_metrics",
            "schedule": crontab(hour=2, minute=30),  # 每天凌晨2:30
            "options": {"queue": "scheduled"},
        },

        # 租户订阅到期检查 - 每天凌晨2点
        "tenant-check-subscription-expiry": {
            "task": "app.tasks.tenant_usage_task.check_subscription_expiry",
            "schedule": crontab(hour=2, minute=0),  # 每天凌晨2:00
            "options": {"queue": "scheduled"},
        },

        # 租户用量限制检查 - 每天凌晨4点
        "tenant-check-usage-limits": {
            "task": "app.tasks.tenant_usage_task.check_usage_limits",
            "schedule": crontab(hour=4, minute=0),  # 每天凌晨4:00
            "options": {"queue": "scheduled"},
        },

        # 支付超时自动取消 - 每5分钟
        "payment-cancel-expired-pending": {
            "task": "payment.cancel_expired_pending",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "scheduled"},
        },

        # 支付状态主动对账 - 每15分钟
        "payment-reconciliation": {
            "task": "payment.reconciliation",
            "schedule": crontab(minute="*/15"),
            "options": {"queue": "scheduled"},
        },

        # 退款状态主动同步 - 每30分钟
        # 注意：task 必须与任务注册名一致（refund_sync.py 中显式 name="refund.status_sync"），
        # 否则 beat 派发时报 Received unregistered task 被丢弃
        "refund-status-sync": {
            "task": "refund.status_sync",
            "schedule": crontab(minute="*/30"),
            "options": {"queue": "scheduled"},
        },

        # 停诊处置补偿 - 每30分钟检查 pending 状态的停诊记录
        "suspension-processing-compensation": {
            "task": "app.tasks.suspension_processing_task.check_pending_suspension_processing",
            "schedule": crontab(minute="*/30"),
            "options": {"queue": "scheduled"},
        },

        # 排班号源对账 - 每天凌晨3:30（与排班生成错开）
        "schedule-booked-slots-reconciliation": {
            "task": "app.tasks.schedule_reconciliation_task.reconcile_booked_slots",
            "schedule": crontab(hour=3, minute=30),
            "options": {"queue": "scheduled"},
        },

        # 审批超时检查 - 每10分钟
        "approval-timeout-check": {
            "task": "app.tasks.approval_task.check_approval_timeouts",
            "schedule": crontab(minute="*/10"),
            "options": {"queue": "scheduled"},
        },

        # 失败通知自动重试 - 每5分钟
        "retry-failed-notifications": {
            "task": "app.tasks.notification_retry_task.retry_failed_notifications",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "notification"},
        },

        # 统一消息投递重试 - 每5分钟（与旧重试任务错开 1 分钟）
        "unified-message-retry": {
            "task": "app.tasks.unified_message_retry_task.retry_failed_deliveries",
            "schedule": crontab(minute="1,6,11,16,21,26,31,36,41,46,51,56"),
            "options": {"queue": "notification"},
        },

        # 统一消息过期清理 - 每天凌晨 3:05（与旧清理任务错开 5 分钟）
        "unified-message-cleanup": {
            "task": "app.tasks.unified_message_cleanup_task.cleanup_expired_messages",
            "schedule": crontab(hour=3, minute=5),
            "options": {"queue": "scheduled"},
        },

        # 行为日志过期清理 - 每天凌晨 3:20（保留 90 天）
        "behavior-log-cleanup": {
            "task": "app.tasks.behavior_log_task.cleanup_expired_behavior_logs",
            "schedule": crontab(hour=3, minute=20),
            "options": {"queue": "scheduled"},
        },

        # 会话回放批次段过期清理 - 每天凌晨 3:25（与行为日志清理错开 5 分钟）
        "session-events-cleanup": {
            "task": "app.tasks.session_event_task.cleanup_session_events",
            "schedule": crontab(hour=3, minute=25),
            "options": {"queue": "scheduled"},
        },

        # 热力图点位过期清理 - 每天凌晨 3:30
        "heatmap-points-cleanup": {
            "task": "app.tasks.session_event_task.cleanup_heatmap_points",
            "schedule": crontab(hour=3, minute=30),
            "options": {"queue": "scheduled"},
        },

        # 随访逾期标记 - 每天凌晨 4:30
        "follow-up-mark-overdue": {
            "task": "app.tasks.follow_up_task.mark_overdue_task",
            "schedule": crontab(hour=4, minute=30),
            "options": {"queue": "scheduled"},
        },

        # 随访任务到期提醒 - 每天早上 8:00
        "follow-up-reminder": {
            "task": "app.tasks.follow_up_task.send_follow_up_reminders",
            "schedule": crontab(hour=8, minute=0),
            "options": {"queue": "notification"},
        },

        # 兼职费用结算扫描 - 每天下午 5 点
        "freelance-generate-settlements": {
            "task": "freelance.generate_settlements",
            "schedule": crontab(hour=17, minute=0),
            "options": {"queue": "scheduled"},
        },

        # 定期 admin 网页截图 - 每天凌晨 2:15
        # （与 2:00 的 schedule-auto-generate / tenant-check-subscription-expiry 错开）
        "admin-periodic-screenshot": {
            "task": "app.tasks.screenshot_task.capture_admin_screenshots",
            "schedule": crontab(hour=2, minute=15),
            "options": {"queue": "scheduled"},
        },

        # 平台公告定时发布 - 每分钟检查
        "announcement-publish-scheduled": {
            "task": "app.tasks.announcement_task.publish_scheduled_announcements",
            "schedule": crontab(minute="*/1"),
            "options": {"queue": "scheduled"},
        },

        # 统一通知系统重试 - 每5分钟
        "unified-notification-retry": {
            "task": "app.tasks.unified_notification_retry_task.retry_failed_deliveries",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "notification"},
        },

        # 考勤每日统计 - 每天凌晨 1:30（与租户用量统计错开 30 分钟）
        "attendance-daily-stat": {
            "task": "attendance_daily_stat",
            "schedule": crontab(hour=1, minute=30),
            "options": {"queue": "scheduled"},
        },

        # 考勤异常告警 - 每天早上 8:30（在 daily-stat 1:30 之后执行，确保统计数据已生成）
        "attendance-alert": {
            "task": "attendance_alert",
            "schedule": crontab(hour=8, minute=30),
            "options": {"queue": "scheduled"},
        },

        # 考勤数据归档清理 - 每周日凌晨 4:00（与 daily-stat 1:30 和日常清理 3:15 错开）
        "attendance-cleanup": {
            "task": "app.tasks.attendance_cleanup_task.attendance_cleanup",
            "schedule": crontab(hour=4, minute=0, day_of_week=0),  # 每周日凌晨 4:00
            "options": {"queue": "scheduled"},
        },

        # 第三方集成组织架构同步 - 每6小时（钉钉/企业微信/飞书通讯录）
        "integration-org-sync": {
            "task": "app.tasks.integration_sync_task.sync_all_tenants_task",
            "schedule": crontab(minute=0, hour="*/6"),  # 每6小时整点
            "options": {"queue": "scheduled"},
        },
    },
)

# 自动发现任务模块
celery_app.autodiscover_tasks([
    "app.tasks.blacklist_task",
    "app.tasks.schedule_task",
    "app.tasks.notification_task",
    "app.tasks.notification_retry_task",
    "app.tasks.unified_message_retry_task",
    "app.tasks.unified_message_cleanup_task",
    "app.tasks.email_hook_task",
    "app.tasks.wechat_task",
    "app.tasks.cleanup_task",
    "app.tasks.cleanup_login_history",
    "app.tasks.operation_log_task",
    "app.tasks.behavior_log_task",
    "app.tasks.session_event_task",
    "app.tasks.screenshot_task",
    "app.tasks.tenant_usage_task",
    "app.tasks.payment_task",
    "app.tasks.payment_reconciliation",
    "app.tasks.refund_sync",
    "app.tasks.schedule_reconciliation_task",
    "app.tasks.suspension_processing_task",
    "app.tasks.approval_task",
    "app.tasks.follow_up_task",
    "app.tasks.freelance_task",
    "app.tasks.lowcode_deploy_task",
    "app.tasks.announcement_task",
    "app.tasks.unified_notification_retry_task",
    "app.tasks.attendance_stat_task",
    "app.tasks.attendance_alert_task",
    "app.tasks.attendance_cleanup_task",
    "app.tasks.waitlist_promotion_task",
    # beat 引用了这两个模块的任务，缺了会被报 Received unregistered task 并丢弃
    "app.tasks.store_metric_task",
    "app.tasks.integration_sync_task",
])

# Flower 监控配置
# 通过环境变量 FLOWER_BASIC_AUTH 配置认证，格式: username:password
# 启动命令: celery -A app.celery_app flower --port=5555
