"""跨租户数据迁移路由

包含：
- POST /{tenant_id}/migrate/precheck — 迁移前预检
- POST /{tenant_id}/migrate — 跨租户数据迁移
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import require_platform_admin
from app.db.session import get_db
from app.modules.tenants.schemas import (
    TenantMigratePrecheckRequest,
    TenantMigratePrecheckResponse,
    TenantMigrateRequest,
    TenantMigrateResponse,
)
from app.modules.tenants.service_migration import TenantMigrationService

router = APIRouter()


@router.post(
    "/{tenant_id}/migrate/precheck",
    response_model=TenantMigratePrecheckResponse,
    summary="迁移前预检",
)
async def precheck_tenant_migration(
    tenant_id: str,
    data: TenantMigratePrecheckRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """迁移前预检：检查目标租户配额、源数据量等（仅平台管理员）"""
    service = TenantMigrationService(db)
    try:
        result = await service.precheck_migration(
            target_tenant_id=tenant_id,
            source_tenant_id=data.source_tenant_id,
            entity_types=data.entity_types,
        )
        return TenantMigratePrecheckResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{tenant_id}/migrate",
    response_model=TenantMigrateResponse,
    summary="跨租户数据迁移",
    description="""将源租户的配置类数据迁移到目标租户，仅限平台管理员操作。

**支持迁移的实体类型：**
- stores: 门店
- departments: 科室
- doctors: 医生
- schedule_templates: 排班模板
- doctor_booking_settings: 医生预约设置
- booking_notices: 预约须知
- email_templates: 邮件模板
- message_templates: 消息模板
- rest_days: 休息日
- blacklists: 黑名单
- store_visit_type_configs: 门店复诊规则配置
- store_email_recipients: 门店邮件接收人
- consultation_fee_templates: 诊费模板
- rule_sets: 规则组（含 windows、booking_policy、checkin_policy、capacity_policy、shift_types 关联）

**配额检查：**
- 迁移前会自动检查目标租户的门店数和医生数配额是否足够
- 如果配额不足，返回 400 错误

**ID 处理：**
- 默认生成新的 UUID，避免冲突
- 设置 preserve_ids=true 可保留原始 ID（需谨慎使用）

**请求示例：**
```json
{
  "sourceTenantId": "tenant_abc123",
  "preserveIds": false,
  "entityTypes": ["stores", "departments", "doctors"]
}
```

**响应示例：**
```json
{
  "targetTenantId": "tenant_xyz789",
  "sourceTenantId": "tenant_abc123",
  "durationMs": 1250,
  "copied": {
    "stores": 2,
    "departments": 5,
    "doctors": 10
  },
  "failures": []
}
```
""",
)
async def migrate_tenant_data(
    tenant_id: str,
    data: TenantMigrateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_platform_admin()),
):
    """跨租户数据迁移（仅平台管理员）"""
    service = TenantMigrationService(db)

    try:
        result = await service.migrate_data(
            target_tenant_id=tenant_id,
            source_tenant_id=data.source_tenant_id,
            preserve_ids=data.preserve_ids,
            entity_types=data.entity_types,
            created_by=current_admin.get("id"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"迁移失败: {str(e)}",
        )

    return TenantMigrateResponse(
        target_tenant_id=tenant_id,
        source_tenant_id=data.source_tenant_id,
        duration_ms=result["duration_ms"],
        copied=result["copied"],
        failures=result["failures"],
    )
