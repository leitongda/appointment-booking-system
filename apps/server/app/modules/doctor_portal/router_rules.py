"""医生端查看关联规则组端点"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_doctor_by_token
from app.models.doctor import Doctor
from app.modules.rule_sets.service import RuleSetService
from app.schemas.rule_set import PageResult, RuleSetDetailResponse
from app.core.config import settings

router = APIRouter()


@router.get(
    "/rule-sets",
    response_model=PageResult[RuleSetDetailResponse],
    summary="获取我的预约规则",
    description="""
    获取直接关联到当前医生的规则组列表（只读）。

    仅返回 doctor_id = 当前医生ID 的规则组。
    如需查看科室/门店级规则，请联系管理员在机构端查看。

    **权限**：只读，医生不可修改规则。
    """,
)
async def get_my_rule_sets(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db),
):
    """获取当前医生关联的规则组列表"""
    service = RuleSetService(db)

    # 查询直接关联到该医生的规则组
    rule_sets, total = await service.get_list(
        doctor_id=doctor.id,
        page=page,
        page_size=page_size,
    )

    return {"data": rule_sets, "total": total}
