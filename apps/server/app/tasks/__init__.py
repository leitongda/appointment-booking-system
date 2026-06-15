"""
定时任务模块

任务调度由 Celery Beat 管理，配置在 celery_app.py 中

任务列表：
- blacklist_task: 黑名单自动解禁、爽约自动标记
- notification_task: 预约提醒
- schedule_task: 排班自动生成
- suspension_processing_task: 停诊处置补偿
- wechat_task: 微信 Token 刷新
- cleanup_task: 数据清理
"""

from app.tasks.blacklist_task import (
    auto_release_blacklist_task,
    check_and_add_blacklist,
    mark_no_show_appointments_task,
)
from app.tasks.cleanup_task import (
    cleanup_expired_data_task,
    cleanup_old_messages,
    cleanup_redis_cache,
)
from app.tasks.follow_up_task import (
    mark_overdue_task,
    send_follow_up_reminders,
)
from app.tasks.lowcode_deploy_task import (
    build_lowcode_page_task,
    publish_release_task,
    rollback_task,
    submit_audit_task,
    upload_to_wechat_task,
)
from app.tasks.notification_task import (
    send_appointment_reminder,
    send_appointment_reminder_task,
)
from app.tasks.schedule_task import (
    auto_generate_schedules_task,
    generate_schedules_for_template,
    generate_schedules_for_tenant_task,
    summarize_auto_generate_schedules_task,
)
from app.tasks.suspension_processing_task import (
    check_pending_suspension_processing,
)
from app.tasks.wechat_task import (
    refresh_wechat_token,
    refresh_wechat_token_task,
)

__all__ = [
    # 黑名单任务
    'auto_release_blacklist_task',
    'mark_no_show_appointments_task',
    'check_and_add_blacklist',
    # 通知任务
    'send_appointment_reminder_task',
    'send_appointment_reminder',
    # 排班任务
    'auto_generate_schedules_task',
    'generate_schedules_for_tenant_task',
    'summarize_auto_generate_schedules_task',
    'generate_schedules_for_template',
    # 停诊处置补偿任务
    'check_pending_suspension_processing',
    # 微信任务
    'refresh_wechat_token_task',
    'refresh_wechat_token',
    # 清理任务
    'cleanup_expired_data_task',
    'cleanup_redis_cache',
    'cleanup_old_messages',
    # 随访任务
    'mark_overdue_task',
    'send_follow_up_reminders',
    # 低代码部署任务
    'build_lowcode_page_task',
    'upload_to_wechat_task',
    'submit_audit_task',
    'publish_release_task',
    'rollback_task',
]
