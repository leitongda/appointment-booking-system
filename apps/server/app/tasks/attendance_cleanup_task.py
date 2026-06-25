"""
考勤数据归档清理 Celery 任务

清理策略：
- 考勤打卡记录：按 check_date 保留 N 天（默认 365 天）
- 考勤每日统计：按 date 保留 M 天（默认 730 天）
- 假期申请记录：已审批完成的保留 N 天
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, and_

from app.celery_app import celery_app
from app.core.config import settings
from app.db.session import get_sync_db
from app.models.attendance import AttendanceRecord, AttendanceStatDaily, AttendanceLeaveRequest

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.attendance_cleanup_task.attendance_cleanup",
    queue="scheduled",
    max_retries=3,
    default_retry_delay=60,
    time_limit=600,
    soft_time_limit=480,
)
def attendance_cleanup():
    """清理过期考勤数据

    清理策略：
    - 考勤打卡记录：保留 N 天（默认 365 天），按 check_date 判定
    - 考勤每日统计：保留 M 天（默认 730 天），按 date 判定
    - 假期申请记录：已审批完成（approved/rejected/cancelled）的保留 N 天
    """
    record_days = settings.ATTENDANCE_RECORD_RETENTION_DAYS
    stat_days = settings.ATTENDANCE_STAT_RETENTION_DAYS

    cutoff_record = datetime.utcnow().date() - timedelta(days=record_days)
    cutoff_stat = datetime.utcnow().date() - timedelta(days=stat_days)

    logger.info(f"[定时任务] 开始考勤数据清理: 打卡记录>{record_days}天, 统计>{stat_days}天")

    results = {
        "record_deleted": 0,
        "stat_deleted": 0,
        "leave_deleted": 0,
        "errors": [],
    }

    with get_sync_db() as db:
        try:
            # 1. 清理打卡记录
            result = db.execute(
                delete(AttendanceRecord).where(
                    AttendanceRecord.check_date < cutoff_record
                )
            )
            results["record_deleted"] = result.rowcount
            logger.info(f"清理打卡记录: {results['record_deleted']} 条")

        except Exception as e:
            db.rollback()
            logger.error(f"清理打卡记录失败: {e}")
            results["errors"].append(f"打卡记录清理失败: {str(e)}")

        try:
            # 2. 清理每日统计
            result = db.execute(
                delete(AttendanceStatDaily).where(
                    AttendanceStatDaily.date < cutoff_stat
                )
            )
            results["stat_deleted"] = result.rowcount
            logger.info(f"清理每日统计: {results['stat_deleted']} 条")

        except Exception as e:
            db.rollback()
            logger.error(f"清理每日统计失败: {e}")
            results["errors"].append(f"每日统计清理失败: {str(e)}")

        try:
            # 3. 清理已审批完成的假期申请（与打卡记录相同的保留天数）
            result = db.execute(
                delete(AttendanceLeaveRequest).where(
                    and_(
                        AttendanceLeaveRequest.status.in_(
                            ["approved", "rejected", "cancelled"]
                        ),
                        AttendanceLeaveRequest.created_at < datetime.utcnow() - timedelta(days=record_days),
                    )
                )
            )
            results["leave_deleted"] = result.rowcount
            logger.info(f"清理假期申请: {results['leave_deleted']} 条")

        except Exception as e:
            db.rollback()
            logger.error(f"清理假期申请失败: {e}")
            results["errors"].append(f"假期申请清理失败: {str(e)}")

        try:
            db.commit()
        except Exception as e:
            logger.error(f"提交事务失败: {e}")
            results["errors"].append(f"提交失败: {str(e)}")

    logger.info(
        f"[定时任务] 考勤数据清理完成: "
        f"打卡记录 {results['record_deleted']} 条, "
        f"统计 {results['stat_deleted']} 条, "
        f"假期申请 {results['leave_deleted']} 条"
    )
    return results
