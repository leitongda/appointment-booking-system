"""
操作日志相关任务
- 异步保存操作日志到数据库
"""
import logging
import uuid

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.admin import OperationLog

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.operation_log_task.save_operation_log",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=120,
    soft_time_limit=90,
)
def save_operation_log(log_data: dict):
    """
    保存操作日志到数据库
    
    Args:
        log_data: 日志数据字典，包含以下字段：
            - admin_id: 操作人ID
            - admin_name: 操作人姓名
            - module: 模块
            - action: 操作
            - method: 请求方法
            - path: 请求路径
            - params: 请求参数 (JSON字符串)
            - result: 结果 (成功/失败)
            - ip: IP地址
            - user_agent: User-Agent
            - duration: 耗时(毫秒)
    """
    logger.debug(f"[任务] 保存操作日志: {log_data.get('path')} - {log_data.get('action')}")
    
    with get_sync_db() as db:
        try:
            log = OperationLog(
                id=str(uuid.uuid4()),
                tenant_id=log_data.get("tenant_id"),
                admin_id=log_data.get("admin_id"),
                admin_name=log_data.get("admin_name"),
                module=log_data.get("module"),
                action=log_data.get("action"),
                method=log_data.get("method"),
                path=log_data.get("path"),
                params=log_data.get("params"),
                result=log_data.get("result", "成功"),
                ip=log_data.get("ip"),
                user_agent=log_data.get("user_agent"),
                duration=log_data.get("duration"),
            )
            db.add(log)
            db.commit()

            logger.debug(f"操作日志保存成功: id={log.id}")
            return {"success": True, "log_id": log.id}

        except Exception as e:
            db.rollback()
            logger.error(f"操作日志保存失败: {e}")
            raise


@celery_app.task(
    name="app.tasks.operation_log_task.batch_save_operation_logs",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=180,
    soft_time_limit=150,
)
def batch_save_operation_logs(logs_data: list):
    """
    批量保存操作日志到数据库

    Args:
        logs_data: 日志数据列表
    """
    logger.debug(f"[任务] 批量保存操作日志: {len(logs_data)} 条")

    with get_sync_db() as db:
        try:
            saved_count = 0
            for log_data in logs_data:
                log = OperationLog(
                    id=str(uuid.uuid4()),
                    tenant_id=log_data.get("tenant_id"),
                    admin_id=log_data.get("admin_id"),
                    admin_name=log_data.get("admin_name"),
                    module=log_data.get("module"),
                    action=log_data.get("action"),
                    method=log_data.get("method"),
                    path=log_data.get("path"),
                    params=log_data.get("params"),
                    result=log_data.get("result", "成功"),
                    ip=log_data.get("ip"),
                    user_agent=log_data.get("user_agent"),
                    duration=log_data.get("duration"),
                )
                db.add(log)
                saved_count += 1
            
            db.commit()
            logger.debug(f"批量保存操作日志成功: {saved_count} 条")
            return {"success": True, "saved_count": saved_count}
            
        except Exception as e:
            db.rollback()
            logger.error(f"批量保存操作日志失败: {e}")
            raise

