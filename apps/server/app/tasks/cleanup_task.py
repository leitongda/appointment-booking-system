"""
数据清理定时任务
- 清理过期的临时数据
- 清理过期的验证码
- 清理过期的登录 session
- 清理租户过期日志
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, delete, select

from app.celery_app import celery_app
from app.core.redis import get_sync_redis
from app.db.session import get_sync_db
from app.models.message import Message
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.cleanup_task.cleanup_expired_data_task",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=300,
    soft_time_limit=240,
)
def cleanup_expired_data_task():
    """
    清理过期数据
    每天凌晨3点执行
    
    清理内容：
    1. Redis 中的过期验证码键
    2. Redis 中的过期扫码登录状态
    3. 超过 90 天的已读系统消息
    """
    logger.info("[定时任务] 开始执行：数据清理")
    
    results = {
        "redis_keys_cleaned": 0,
        "messages_cleaned": 0,
        "errors": []
    }
    
    # 1. 清理 Redis 过期键（Redis 会自动清理过期键，这里主要是清理一些遗留的）
    try:
        redis_client = get_sync_redis()
        
        # 清理过期的短信验证码键
        sms_keys = redis_client.keys("sms:*")
        for key in sms_keys:
            ttl = redis_client.ttl(key)
            if ttl == -1:  # 没有设置过期时间的键
                redis_client.delete(key)
                results["redis_keys_cleaned"] += 1
        
        # 清理过期的扫码登录状态
        scan_keys = redis_client.keys("scan:login:*")
        for key in scan_keys:
            ttl = redis_client.ttl(key)
            if ttl == -1:
                redis_client.delete(key)
                results["redis_keys_cleaned"] += 1
        
        logger.info(f"清理了 {results['redis_keys_cleaned']} 个 Redis 键")
        
    except Exception as e:
        logger.error(f"清理 Redis 键失败: {e}")
        results["errors"].append(f"Redis 清理失败: {str(e)}")
    
    # 2. 清理过期的系统消息
    with get_sync_db() as db:
        try:
            # 删除超过 90 天的已读系统消息
            cutoff_date = datetime.now() - timedelta(days=90)
            
            result = db.execute(
                delete(Message).where(
                    and_(
                        Message.is_read == 1,
                        Message.message_type == 'system',
                        Message.created_at < cutoff_date
                    )
                )
            )
            
            results["messages_cleaned"] = result.rowcount
            db.commit()
            
            logger.info(f"清理了 {results['messages_cleaned']} 条过期消息")
            
        except Exception as e:
            db.rollback()
            logger.error(f"清理消息失败: {e}")
            results["errors"].append(f"消息清理失败: {str(e)}")
    
    logger.info(f"[定时任务] 数据清理完成: {results}")
    return results


@celery_app.task(
    name="app.tasks.cleanup_task.cleanup_redis_cache",
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=120,
    soft_time_limit=90,
)
def cleanup_redis_cache(pattern: str = None):
    """
    清理 Redis 缓存（手动触发）
    
    Args:
        pattern: 键模式，如 "cache:*"，不传则不执行
    """
    if not pattern:
        return {"cleaned": 0, "reason": "未指定模式"}
    
    logger.info(f"[任务] 清理 Redis 缓存: pattern={pattern}")
    
    try:
        redis_client = get_sync_redis()
        keys = redis_client.keys(pattern)
        
        if keys:
            redis_client.delete(*keys)
            logger.info(f"清理了 {len(keys)} 个 Redis 键")
            return {"cleaned": len(keys), "pattern": pattern}
        else:
            return {"cleaned": 0, "pattern": pattern}
            
    except Exception as e:
        logger.error(f"清理 Redis 缓存失败: {e}")
        return {"cleaned": 0, "error": str(e)}


@celery_app.task(
    name="app.tasks.cleanup_task.cleanup_old_messages",
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=180,
    soft_time_limit=150,
)
def cleanup_old_messages(days: int = 90, message_type: str = None):
    """
    清理旧消息（手动触发）
    
    Args:
        days: 清理多少天前的消息
        message_type: 消息类型，不传则清理所有类型
    """
    logger.info(f"[任务] 清理旧消息: days={days}, type={message_type}")
    
    with get_sync_db() as db:
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            conditions = [
                Message.is_read == 1,
                Message.created_at < cutoff_date
            ]
            
            if message_type:
                conditions.append(Message.message_type == message_type)
            
            result = db.execute(
                delete(Message).where(and_(*conditions))
            )
            
            cleaned = result.rowcount
            db.commit()
            
            logger.info(f"清理了 {cleaned} 条消息")
            return {"cleaned": cleaned, "days": days, "type": message_type}
            
        except Exception as e:
            db.rollback()
            logger.error(f"清理消息失败: {e}")
            return {"cleaned": 0, "error": str(e)}


@celery_app.task(
    name="app.tasks.cleanup_task.cleanup_tenant_logs",
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    time_limit=600,
    soft_time_limit=480,
)
def cleanup_tenant_logs():
    """清理租户过期日志（每天执行）

    根据每个租户配置的 log_retention_days 清理：
    - 操作日志 (operation_logs)
    - 租户审计日志 (tenant_audit_logs)
    """
    from app.models.admin import OperationLog
    from app.models.tenant_audit_log import TenantAuditLog

    logger.info("[定时任务] 开始清理租户过期日志")

    with get_sync_db() as db:
        try:
            result = db.execute(
                select(Tenant).where(Tenant.status.in_([1, 3]))
            )
            tenants = result.scalars().all()
            total_cleaned = 0

            for tenant in tenants:
                try:
                    retention_days = tenant.log_retention_days or 90
                    cutoff = datetime.utcnow() - timedelta(days=retention_days)

                    op_count = db.execute(
                        delete(OperationLog).where(
                            and_(
                                OperationLog.tenant_id == tenant.id,
                                OperationLog.created_at < cutoff,
                            )
                        )
                    ).rowcount

                    audit_count = db.execute(
                        delete(TenantAuditLog).where(
                            and_(
                                TenantAuditLog.tenant_id == tenant.id,
                                TenantAuditLog.created_at < cutoff,
                            )
                        )
                    ).rowcount

                    cleaned = op_count + audit_count
                    total_cleaned += cleaned

                    if cleaned > 0:
                        logger.info(
                            f"租户 {tenant.name}: 清理 {cleaned} 条过期日志 "
                            f"(op={op_count}, audit={audit_count})"
                        )

                except Exception as e:
                    logger.error(f"清理租户 {tenant.id} 日志失败: {e}")
                    db.rollback()
                    continue

            db.commit()
            logger.info(f"[定时任务] 日志清理完成，共清理 {total_cleaned} 条")
            return {"total_cleaned": total_cleaned}

        except Exception as e:
            db.rollback()
            logger.error(f"[定时任务] 日志清理失败: {e}")
            raise

