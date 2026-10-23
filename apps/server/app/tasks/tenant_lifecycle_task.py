"""租户生命周期定时任务

对应改造项 P4-7「软删除闭环」：软删除租户保留 90 天后才允许物理删除。

首版安全策略（双保险）：
- ``TENANT_PURGE_ENABLED=False``（默认）：任务直接返回，不扫描、不删除。
- ``TENANT_PURGE_ENABLED=True``：仅以 dry-run 方式输出「已到期可物理删除」的
  租户清单，**不执行任何物理删除**。物理删除留待备份策略确认后单独实现。

租户软删除的字段与 90 天承诺见 ``app/modules/tenants/service_tenant.py`` 的
``TenantService.delete``；软删除字段定义见 ``app/models/tenant.py`` 的
``Tenant.deleted_at`` / ``Tenant.deleted_by``。
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.celery_app import celery_app
from app.core.config import settings
from app.db.session import get_sync_db
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# 软删除后的保留天数（与 TenantService.delete 文档承诺一致）
TENANT_PURGE_RETENTION_DAYS = 90


def _find_expired_deleted_tenants(db, cutoff: datetime) -> list[Tenant]:
    """查询 ``deleted_at`` 早于 ``cutoff`` 的租户，按删除时间升序。

    使用 ORM 表达式构造条件，不做任何 SQL 字符串拼接。
    """
    stmt = (
        select(Tenant)
        .where(
            Tenant.deleted_at.is_not(None),
            Tenant.deleted_at < cutoff,
        )
        .order_by(Tenant.deleted_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


@celery_app.task(
    name="app.tasks.tenant_lifecycle_task.purge_deleted_tenants_task",
    queue="scheduled",
    time_limit=600,
    soft_time_limit=480,
)
def purge_deleted_tenants_task() -> dict:
    """扫描并（首版仅 dry-run）列出到期可物理删除的软删除租户。

    Returns:
        结构化结果：开关状态、保留天数、截止时间、候选清单。

    注意：本版本绝不执行 DELETE。即使 ``TENANT_PURGE_DRY_RUN=False``，
    也只输出清单并在日志中提示物理删除尚未实现。
    """
    if not settings.TENANT_PURGE_ENABLED:
        logger.info(
            "[租户清理] TENANT_PURGE_ENABLED=False，跳过租户物理删除扫描"
        )
        return {
            "enabled": False,
            "dry_run": True,
            "deleted": 0,
            "candidates": [],
        }

    cutoff = datetime.utcnow() - timedelta(days=TENANT_PURGE_RETENTION_DAYS)

    with get_sync_db() as db:
        tenants = _find_expired_deleted_tenants(db, cutoff)

    candidates = [
        {
            "id": tenant.id,
            "tenant_code": tenant.tenant_code,
            "name": tenant.name,
            "status": tenant.status,
            "deleted_at": (
                tenant.deleted_at.isoformat() if tenant.deleted_at else None
            ),
            "deleted_by": tenant.deleted_by,
        }
        for tenant in tenants
    ]

    if settings.TENANT_PURGE_DRY_RUN:
        logger.warning(
            "[租户清理] dry-run：共 %s 个软删除租户已超过 %s 天保留期，"
            "本次不执行物理删除。cutoff=%s",
            len(candidates),
            TENANT_PURGE_RETENTION_DAYS,
            cutoff.isoformat(),
        )
    else:
        # 首版无论 DRY_RUN 取值都只输出清单，避免误删不可逆数据
        logger.error(
            "[租户清理] TENANT_PURGE_DRY_RUN=False，但当前版本尚未实现物理删除；"
            "仍仅输出 %s 个候选租户清单，未删除任何数据。cutoff=%s",
            len(candidates),
            cutoff.isoformat(),
        )

    for candidate in candidates:
        logger.warning(
            "[租户清理] 候选租户 id=%s tenant_code=%s name=%s deleted_at=%s",
            candidate["id"],
            candidate["tenant_code"],
            candidate["name"],
            candidate["deleted_at"],
        )

    return {
        "enabled": True,
        "dry_run": True,
        "retention_days": TENANT_PURGE_RETENTION_DAYS,
        "cutoff": cutoff.isoformat(),
        "deleted": 0,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
