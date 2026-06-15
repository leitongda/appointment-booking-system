"""
用户行为日志相关任务
- 异步保存用户行为日志到数据库
- 定时清理过期数据
"""
import json
import logging
import uuid
from datetime import datetime, timedelta

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.behavior_log import UserBehaviorLog

logger = logging.getLogger(__name__)

# 数据保留天数（可通过环境变量覆盖）
RETENTION_DAYS = 90


@celery_app.task(
    name="app.tasks.behavior_log_task.save_behavior_log",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=120,
    soft_time_limit=90,
)
def save_behavior_log(log_data: dict):
    """
    保存用户行为日志到数据库
    
    Args:
        log_data: 日志数据字典
    """
    logger.debug(f"[任务] 保存行为日志: {log_data.get('event_type')} - {log_data.get('page_path')}")
    
    with get_sync_db() as db:
        try:
            # 处理 extra_data
            extra_data = log_data.get("extra_data")
            if extra_data and isinstance(extra_data, dict):
                extra_data = json.dumps(extra_data, ensure_ascii=False)
            
            log = UserBehaviorLog(
                id=str(uuid.uuid4()),
                tenant_id=log_data.get("tenant_id"),
                platform=log_data.get("platform"),
                user_id=log_data.get("user_id"),
                session_id=log_data.get("session_id"),
                event_type=log_data.get("event_type"),
                page_path=log_data.get("page_path"),
                page_title=log_data.get("page_title"),
                element_id=log_data.get("element_id"),
                element_text=log_data.get("element_text"),
                search_keyword=log_data.get("search_keyword"),
                event_name=log_data.get("event_name"),
                duration=log_data.get("duration"),
                referrer=log_data.get("referrer"),
                extra_data=extra_data,
                ip=log_data.get("ip"),
                user_agent=log_data.get("user_agent"),
                device_type=log_data.get("device_type"),
                browser=log_data.get("browser"),
                os=log_data.get("os"),
            )
            db.add(log)
            db.commit()
            
            logger.debug(f"行为日志保存成功: id={log.id}")
            return {"success": True, "log_id": log.id}
            
        except Exception as e:
            db.rollback()
            logger.error(f"行为日志保存失败: {e}")
            raise


@celery_app.task(
    name="app.tasks.behavior_log_task.batch_save_behavior_logs",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=180,
    soft_time_limit=150,
)
def batch_save_behavior_logs(logs_data: list):
    """
    批量保存用户行为日志到数据库
    
    Args:
        logs_data: 日志数据列表
    """
    logger.debug(f"[任务] 批量保存行为日志: {len(logs_data)} 条")
    
    with get_sync_db() as db:
        try:
            saved_count = 0
            for log_data in logs_data:
                # 处理 extra_data
                extra_data = log_data.get("extra_data")
                if extra_data and isinstance(extra_data, dict):
                    extra_data = json.dumps(extra_data, ensure_ascii=False)
                
                log = UserBehaviorLog(
                    id=str(uuid.uuid4()),
                    tenant_id=log_data.get("tenant_id"),
                    platform=log_data.get("platform"),
                    user_id=log_data.get("user_id"),
                    session_id=log_data.get("session_id"),
                    event_type=log_data.get("event_type"),
                    page_path=log_data.get("page_path"),
                    page_title=log_data.get("page_title"),
                    element_id=log_data.get("element_id"),
                    element_text=log_data.get("element_text"),
                    search_keyword=log_data.get("search_keyword"),
                    event_name=log_data.get("event_name"),
                    duration=log_data.get("duration"),
                    referrer=log_data.get("referrer"),
                    extra_data=extra_data,
                    ip=log_data.get("ip"),
                    user_agent=log_data.get("user_agent"),
                    device_type=log_data.get("device_type"),
                    browser=log_data.get("browser"),
                    os=log_data.get("os"),
                )
                db.add(log)
                saved_count += 1
            
            db.commit()
            logger.debug(f"批量保存行为日志成功: {saved_count} 条")
            return {"success": True, "saved_count": saved_count}

        except Exception as e:
            db.rollback()
            logger.error(f"批量保存行为日志失败: {e}")
            raise


@celery_app.task(
    name="app.tasks.behavior_log_task.cleanup_expired_behavior_logs",
    time_limit=600,
    soft_time_limit=540,
)
def cleanup_expired_behavior_logs(retention_days: int = RETENTION_DAYS):
    """
    清理过期的用户行为日志
    每日凌晨由 Celery Beat 调度执行

    Args:
        retention_days: 数据保留天数，默认 90 天
    """
    cutoff = datetime.now() - timedelta(days=retention_days)

    with get_sync_db() as db:
        try:
            # 分批删除，避免长事务锁表
            batch_size = 5000
            total_deleted = 0

            while True:
                # 使用子查询定位待删除行的 ID
                ids = db.execute(
                    UserBehaviorLog.__table__.select()
                    .with_only_columns(UserBehaviorLog.id)
                    .where(UserBehaviorLog.created_at < cutoff)
                    .limit(batch_size)
                ).fetchall()

                if not ids:
                    break

                id_list = [row[0] for row in ids]
                db.execute(
                    UserBehaviorLog.__table__.delete()
                    .where(UserBehaviorLog.id.in_(id_list))
                )
                db.commit()
                total_deleted += len(id_list)

                logger.info(f"[清理] 已删除 {total_deleted} 条过期行为日志（保留 {retention_days} 天）")

            logger.info(f"[清理] 行为日志清理完成，共删除 {total_deleted} 条（截止 {cutoff.date()}）")
            return {"success": True, "deleted": total_deleted, "cutoff": cutoff.isoformat()}

        except Exception as e:
            db.rollback()
            logger.error(f"行为日志清理失败: {e}")
            raise

