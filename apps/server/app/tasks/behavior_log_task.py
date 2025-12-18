"""
用户行为日志相关任务
- 异步保存用户行为日志到数据库
"""
import logging
import uuid
import json

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.behavior_log import UserBehaviorLog

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.behavior_log_task.save_behavior_log")
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


@celery_app.task(name="app.tasks.behavior_log_task.batch_save_behavior_logs")
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

