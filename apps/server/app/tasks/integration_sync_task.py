"""第三方集成组织架构同步定时任务。

- 定时同步所有已启用集成的租户的组织架构（部门 + 成员 + 绑定）
- 也可通过 API 手动触发单个租户 + 平台的同步

由于 Provider 是异步实现，本任务在同步 Session 中通过 asyncio.run 调用。
"""
import logging

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import get_sync_db_session
from app.models.integration import Integration
from app.modules.integration.sync_service import sync_organization

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.integration_sync_task.sync_organization_task",
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    time_limit=300,
    soft_time_limit=240,
)
def sync_organization_task(tenant_id: str, provider: str, store_id: str | None = None):
    """同步单个租户 + 平台的组织架构。

    Args:
        tenant_id: 租户ID
        provider: 平台 dingtalk/wecom/feishu
        store_id: 关联门店ID（可选）
    """
    logger.info(
        "integration_sync_task_start",
        tenant_id=tenant_id,
        provider=provider,
        store_id=store_id,
    )
    try:
        with get_sync_db_session() as db:
            result = sync_organization(db, tenant_id, provider, store_id)
        logger.info("integration_sync_task_done", tenant_id=tenant_id, provider=provider, result=result)
        return result
    except Exception as e:
        logger.exception(
            "integration_sync_task_failed",
            tenant_id=tenant_id,
            provider=provider,
        )
        raise


@celery_app.task(
    name="app.tasks.integration_sync_task.sync_all_tenants_task",
    autoretry_for=(Exception,),
    max_retries=1,
    retry_backoff=True,
    time_limit=1800,
    soft_time_limit=1500,
)
def sync_all_tenants_task():
    """遍历所有已启用集成的租户，同步组织架构（定时调度）。"""
    logger.info("integration_sync_all_start")
    results = []
    try:
        with get_sync_db_session() as db:
            stmt = select(Integration).where(Integration.status == 1)
            integrations = db.execute(stmt).scalars().all()

        for integ in integrations:
            try:
                result = sync_organization_task.delay(
                    tenant_id=integ.tenant_id,
                    provider=integ.provider,
                )
                results.append({
                    "tenant_id": integ.tenant_id,
                    "provider": integ.provider,
                    "task_id": result.id,
                })
            except Exception as e:
                logger.exception(
                    "integration_sync_dispatch_failed",
                    tenant_id=integ.tenant_id,
                    provider=integ.provider,
                )
                results.append({
                    "tenant_id": integ.tenant_id,
                    "provider": integ.provider,
                    "error": str(e),
                })

        logger.info("integration_sync_all_dispatched", count=len(results))
        return results
    except Exception:
        logger.exception("integration_sync_all_failed")
        raise
