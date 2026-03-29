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
        "app.tasks.operation_log_task.*": {"queue": "default"},
        "app.tasks.behavior_log_task.*": {"queue": "default"},
    },
    
    # Beat 调度器配置（定时任务）
    beat_schedule={
        # 黑名单自动解禁 - 每小时执行
        "blacklist-auto-release": {
            "task": "app.tasks.blacklist_task.auto_release_blacklist_task",
            "schedule": crontab(minute=0),  # 每小时整点
            "options": {"queue": "scheduled"},
        },
        
        # 预约提醒 - 每30分钟检查
        "appointment-reminder": {
            "task": "app.tasks.notification_task.send_appointment_reminder_task",
            "schedule": crontab(minute="*/30"),  # 每30分钟
            "options": {"queue": "notification"},
        },
        
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

        # 租户用量统计 - 每天凌晨1点
        "tenant-record-daily-usage": {
            "task": "app.tasks.tenant_usage_task.record_daily_usage",
            "schedule": crontab(hour=1, minute=0),  # 每天凌晨1:00
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
    },
)

# 自动发现任务模块
celery_app.autodiscover_tasks([
    "app.tasks.blacklist_task",
    "app.tasks.schedule_task",
    "app.tasks.notification_task",
    "app.tasks.email_hook_task",
    "app.tasks.wechat_task",
    "app.tasks.cleanup_task",
    "app.tasks.operation_log_task",
    "app.tasks.behavior_log_task",
    "app.tasks.tenant_usage_task",
])

# Flower 监控配置
# 通过环境变量 FLOWER_BASIC_AUTH 配置认证，格式: username:password
# 启动命令: celery -A app.celery_app flower --port=5555

