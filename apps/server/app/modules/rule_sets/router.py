"""
规则组管理 API

提供规则组的 CRUD 接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import time
import logging

from app.db.session import get_db
from app.api.deps import get_current_admin, get_current_super_admin
from app.schemas.rule_set import (
    PageResult, RuleSetCreate, RuleSetUpdate, RuleSetResponse, RuleSetDetailResponse,
    RulePreviewRequest, RulePreviewResponse,
    RuleWindowCreate, RuleWindowUpdate, RuleWindowResponse,
    RuleBookingPolicyCreate, RuleBookingPolicyResponse,
    RuleCheckinPolicyCreate, RuleCheckinPolicyResponse,
    RuleCapacityPolicyCreate, RuleCapacityPolicyResponse,
    RuleSetPresetCreate, RuleSetPresetUpdate, RuleSetPresetResponse,
    RuleSetAuditLogResponse,
)
from app.modules.rule_sets.service import RuleSetService
from app.modules.rule_engine import RuleEngineService
from app.models.schedule import Schedule
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# 超时配置（从配置文件读取）
API_TIMEOUT = settings.API_TIMEOUT
DB_QUERY_TIMEOUT = settings.DB_QUERY_TIMEOUT


@router.get(
    "",
    response_model=PageResult[RuleSetDetailResponse],
    summary="获取规则组列表",
    description="""
    获取规则组列表，支持分页和筛选。

    **支持筛选条件**：
    - enabled: 按启用状态筛选（true/false）
    - shift_type_id: 按班次类型筛选

    **返回数据**：
    - 包含规则组基本信息及关联的时间窗、策略配置
    - 带超时监控，记录查询耗时
    """,
)
async def get_rule_sets(
    enabled: Optional[bool] = Query(None, description="是否启用"),
    shift_type_id: Optional[str] = Query(None, description="班次类型ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取规则组列表（带超时监控）"""
    start_time = time.time()

    try:
        service = RuleSetService(db)
        rule_sets, total = await service.get_list(
            enabled=enabled,
            shift_type_id=shift_type_id,
            page=page,
            page_size=page_size
        )

        # 记录耗时
        duration = time.time() - start_time
        logger.info(
            f"获取规则组列表: admin_id={current_admin['id']}, "
            f"total={total}, duration={duration:.2f}s"
        )

        return {"data": rule_sets, "total": total}

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"获取规则组列表失败: admin_id={current_admin['id']}, "
            f"duration={duration:.2f}s, error={str(e)}"
        )
        raise


@router.get(
    "/performance",
    summary="获取规则引擎性能统计",
    description="""
    获取规则引擎性能统计数据（仅超级管理员）。

    **参数说明**：
    - operation: 操作类型筛选（可选，不填则返回所有操作）
    - hours: 统计时间范围（默认24小时，最大168小时即7天）

    **返回数据**：
    - 调用次数、延迟统计（P50/P95/P99/平均值/最大值/最小值）
    - 慢查询数量、平均调用速率
    """,
)
async def get_performance_stats(
    operation: Optional[str] = Query(None, description="操作类型"),
    hours: int = Query(24, ge=1, le=168, description="统计时间范围（小时）"),
    current_admin: dict = Depends(get_current_super_admin)
):
    """
    获取规则引擎性能统计信息

    需要超级管理员权限

    Args:
        operation: 操作类型，不填则返回所有操作
        hours: 统计时间范围（1-168小时）

    Returns:
        性能统计数据，包括：
        - 调用次数
        - 延迟统计（P50、P95、P99、平均值、最大值、最小值）
        - 慢查询数量
        - 平均调用速率
    """
    from app.services.rule_performance_service import performance_monitor

    stats = await performance_monitor.get_performance_stats(
        operation=operation,
        hours=hours
    )

    return stats


@router.get(
    "/slow-queries",
    summary="获取规则引擎慢查询列表",
    description="""
    获取规则引擎慢查询列表（仅超级管理员），按时间倒序排列。

    **参数说明**：
    - operation: 按操作类型筛选（可选）
    - limit: 返回数量限制（默认100，最大1000）

    **返回数据**：
    - total: 慢查询总数
    - data: 慢查询详情列表
    """,
)
async def get_slow_queries(
    operation: Optional[str] = Query(None, description="操作类型"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    current_admin: dict = Depends(get_current_super_admin)
):
    """
    获取规则引擎慢查询列表

    需要超级管理员权限

    Args:
        operation: 操作类型，不填则返回所有操作
        limit: 返回数量限制（1-1000）

    Returns:
        慢查询列表，按时间倒序排列
    """
    from app.services.rule_performance_service import performance_monitor

    slow_queries = await performance_monitor.get_slow_queries(
        operation=operation,
        limit=limit
    )

    return {
        "total": len(slow_queries),
        "data": slow_queries
    }


@router.delete(
    "/performance/metrics",
    summary="清除性能指标",
    description="""
    清除规则引擎性能指标数据（仅超级管理员）。

    **参数说明**：
    - operation: 按操作类型清除（可选，不填则清除所有操作的指标）

    **适用场景**：性能调优时重置统计数据。
    """,
)
async def clear_performance_metrics(
    operation: Optional[str] = Query(None, description="操作类型"),
    current_admin: dict = Depends(get_current_super_admin)
):
    """
    清除规则引擎性能指标

    需要超级管理员权限

    Args:
        operation: 操作类型，不填则清除所有操作的指标

    Returns:
        清除结果
    """
    from app.services.rule_performance_service import performance_monitor

    result = await performance_monitor.clear_metrics(operation=operation)

    return result


# ==================== 预设模板管理 ====================

@router.get(
    "/presets",
    response_model=list[RuleSetPresetResponse],
    summary="获取预设模板列表",
    description="获取系统预设模板和当前租户的自定义预设模板。",
)
async def get_presets(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """获取预设模板列表"""
    service = RuleSetService(db)
    presets = await service.get_presets()
    return presets


@router.post(
    "/presets",
    response_model=RuleSetPresetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建自定义预设模板",
    description="创建自定义预设模板（仅超级管理员）。",
)
async def create_preset(
    data: RuleSetPresetCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin),
):
    """创建自定义预设模板"""
    service = RuleSetService(db)
    preset = await service.create_preset(
        name=data.name,
        description=data.description,
        config=data.config,
        sort_order=data.sort_order,
        operator_id=current_admin["id"],
    )
    return preset


@router.put(
    "/presets/{preset_id}",
    response_model=RuleSetPresetResponse,
    summary="更新预设模板",
    description="更新自定义预设模板（系统预设不可修改，仅超级管理员）。",
)
async def update_preset(
    preset_id: str,
    data: RuleSetPresetUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin),
):
    """更新预设模板"""
    service = RuleSetService(db)
    preset = await service.update_preset(
        preset_id=preset_id,
        operator_id=current_admin["id"],
        name=data.name,
        description=data.description,
        config=data.config,
        sort_order=data.sort_order,
    )
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预设模板不存在或为系统预设，不可修改",
        )
    return preset


@router.delete(
    "/presets/{preset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除预设模板",
    description="删除自定义预设模板（系统预设不可删除，仅超级管理员）。",
)
async def delete_preset(
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin),
):
    """删除预设模板"""
    service = RuleSetService(db)
    success = await service.delete_preset(preset_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="预设模板不存在或为系统预设，不可删除",
        )


# ==================== 规则组 CRUD ====================

@router.get(
    "/{rule_set_id}",
    response_model=RuleSetDetailResponse,
    summary="获取规则组详情",
    description="""
    获取规则组详情，包含关联的时间窗和策略配置。

    **参数说明**：
    - rule_set_id: 规则组ID（路径参数）

    **返回数据**：
    - 规则组基本信息
    - 关联的时间窗列表（windows）
    - 预约策略（booking_policy）
    - 签到策略（checkin_policy）
    - 容量策略（capacity_policy）
    """,
)
async def get_rule_set(
    rule_set_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取规则组详情（带超时监控）"""
    start_time = time.time()

    try:
        service = RuleSetService(db)
        rule_set = await service.get_by_id(rule_set_id)

        if not rule_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="规则组不存在"
            )

        # 记录耗时
        duration = time.time() - start_time
        logger.info(
            f"获取规则组详情: admin_id={current_admin['id']}, "
            f"rule_set_id={rule_set_id}, duration={duration:.2f}s"
        )

        return rule_set

    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"获取规则组详情失败: admin_id={current_admin['id']}, "
            f"rule_set_id={rule_set_id}, duration={duration:.2f}s, error={str(e)}"
        )
        raise


@router.post(
    "",
    response_model=RuleSetDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建规则组",
    description="""
    创建新的规则组（仅超级管理员）。

    **业务规则**：
    - 规则组名称在同一租户下必须唯一
    - 可关联班次类型（shift_type_id）
    - 创建时记录创建者（operator_id）
    """,
)
async def create_rule_set(
    data: RuleSetCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """创建规则组（仅超级管理员）"""
    service = RuleSetService(db)
    try:
        rule_set = await service.create(data, current_admin["id"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    return rule_set


@router.put(
    "/{rule_set_id}",
    response_model=RuleSetDetailResponse,
    summary="更新规则组",
    description="""
    更新规则组信息（仅超级管理员）。

    **参数说明**：
    - rule_set_id: 规则组ID（路径参数）

    **业务规则**：
    - 记录最后更新者（operator_id）
    - 已被排班引用的规则组修改后影响后续规则计算
    """,
)
async def update_rule_set(
    rule_set_id: str,
    data: RuleSetUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """更新规则组（仅超级管理员）"""
    service = RuleSetService(db)
    try:
        rule_set = await service.update(rule_set_id, data, current_admin["id"])
    except ValueError as e:
        # 乐观锁冲突返回 409，其他验证错误返回 400
        error_msg = str(e)
        if "已被其他操作修改" in error_msg or "请刷新后重试" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    if not rule_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )
    return rule_set


@router.delete(
    "/{rule_set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除规则组",
    description="""
    删除规则组（仅超级管理员）。

    **业务规则**：
    - 已被排班或预约引用的规则组不允许删除（请先禁用规则组）
    - 删除操作为软删除，记录保留在数据库中
    - 历史预约仍可基于快照正常使用
    - 返回 204 No Content
    """,
)
async def delete_rule_set(
    rule_set_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """删除规则组（仅超级管理员）"""
    service = RuleSetService(db)
    try:
        success = await service.delete(rule_set_id, current_admin["id"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )
    return None


@router.post(
    "/{rule_set_id}/enable",
    status_code=status.HTTP_200_OK,
    summary="启用规则组",
    description="""
    启用规则组（仅超级管理员）。

    **业务规则**：
    - 启用后规则组可被排班模板引用
    - 记录操作者（operator_id）
    """,
)
async def enable_rule_set(
    rule_set_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """启用规则组（仅超级管理员）"""
    service = RuleSetService(db)
    success = await service.enable(rule_set_id, current_admin["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )
    return {"message": "启用成功"}


@router.post(
    "/{rule_set_id}/disable",
    status_code=status.HTTP_200_OK,
    summary="禁用规则组",
    description="""
    禁用规则组（仅超级管理员）。

    **业务规则**：
    - 禁用后规则组不再被新排班模板引用
    - 已引用该规则组的排班不受影响（规则引擎运行时不检查 enabled 状态）
    - 记录操作者（operator_id）
    """,
)
async def disable_rule_set(
    rule_set_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """禁用规则组（仅超级管理员）"""
    service = RuleSetService(db)
    success = await service.disable(rule_set_id, current_admin["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )
    return {"message": "禁用成功"}


@router.post(
    "/preview",
    response_model=RulePreviewResponse,
    summary="预览规则效果",
    description="""
    预览规则效果，根据输入的班次信息计算各动作窗口的结果。

    **适用场景**：管理后台编辑规则时的实时预览。

    **参数说明**：
    - schedule_date: 排班日期
    - start_time / end_time: 排班起止时间
    - shift_type_id: 班次类型ID
    - current_time: 模拟的当前时间（用于测试不同时间点的效果）

    **返回数据**：
    - book_window: 预约动作窗口检查结果
    - checkin_window: 签到动作窗口检查结果
    - cancel_window: 取消动作窗口检查结果

    **超时保护**：API 调用超时 30s，数据库查询超时 10s。
    """,
)
async def preview_rule(
    data: RulePreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """预览规则效果

    根据输入的班次信息，计算各动作窗口的结果

    超时配置：API 调用 30s，数据库查询 10s
    """
    start_time = time.time()

    try:
        # 设置数据库查询超时
        await db.execute(text(f"SET statement_timeout TO {DB_QUERY_TIMEOUT * 1000}"))

        engine = RuleEngineService(db)

        # 构造虚拟 schedule 对象
        schedule = Schedule()
        schedule.schedule_date = data.schedule_date
        schedule.start_time = data.start_time
        schedule.end_time = data.end_time
        schedule.shift_type_id = data.shift_type_id

        current_time = data.current_time

        # 获取候选规则组信息
        candidates = await engine.get_candidate_rule_sets(data.shift_type_id)
        matched = candidates[0] if candidates else None

        # 检查各动作窗口（带超时监控）
        book_result = await engine.check_action_window(schedule, 'BOOK', current_time)
        checkin_result = await engine.check_action_window(schedule, 'CHECKIN', current_time)
        cancel_result = await engine.check_action_window(schedule, 'CANCEL', current_time)

        # 记录成功耗时
        duration = time.time() - start_time
        logger.info(
            f"规则预览成功: admin_id={current_admin['id']}, "
            f"shift_type_id={data.shift_type_id}, "
            f"duration={duration:.2f}s"
        )

        from app.schemas.rule_set import RuleSetBrief
        return RulePreviewResponse(
            book_window=book_result,
            checkin_window=checkin_result,
            cancel_window=cancel_result,
            matched_rule_set=RuleSetBrief(
                id=matched.id, name=matched.name,
                priority=matched.priority, enabled=matched.enabled,
            ) if matched else None,
            candidate_rule_sets=[
                RuleSetBrief(
                    id=rs.id, name=rs.name,
                    priority=rs.priority, enabled=rs.enabled,
                ) for rs in candidates
            ],
        )

    except Exception as e:
        duration = time.time() - start_time
        is_timeout = duration >= API_TIMEOUT

        logger.error(
            f"规则预览{'超时' if is_timeout else '失败'}: "
            f"admin_id={current_admin['id']}, "
            f"shift_type_id={data.shift_type_id}, "
            f"duration={duration:.2f}s, "
            f"error={str(e)}"
        )

        if is_timeout:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="规则预览超时，请稍后重试"
            )
        else:
            raise
    finally:
        # 重置数据库查询超时
        try:
            await db.execute(text("SET statement_timeout TO 0"))
        except Exception:
            pass


# ==================== RuleWindow 独立管理 ====================

@router.post(
    "/{rule_set_id}/windows",
    response_model=RuleWindowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建时间窗",
    description="""
    为指定规则组创建时间窗配置（仅超级管理员）。

    **参数说明**：
    - rule_set_id: 规则组ID（路径参数）
    - action: 动作类型（BOOK/CHECKIN/CANCEL）
    - open_offset_minutes: 开放偏移分钟数（相对于排班开始时间）
    - close_offset_minutes: 截止偏移分钟数

    **业务规则**：
    - 规则组不存在时返回 404
    - 记录创建者（operator_id）
    """,
)
async def create_window(
    rule_set_id: str,
    data: RuleWindowCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """创建时间窗（仅超级管理员）"""
    service = RuleSetService(db)
    window = await service.create_window(rule_set_id, data, current_admin["id"])
    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )
    return window


@router.put(
    "/windows/{window_id}",
    response_model=RuleWindowResponse,
    summary="更新时间窗",
    description="""
    更新时间窗配置（仅超级管理员）。

    **参数说明**：
    - window_id: 时间窗ID（路径参数）

    **业务规则**：
    - 时间窗不存在时返回 404
    - 记录最后更新者（operator_id）
    """,
)
async def update_window(
    window_id: str,
    data: RuleWindowUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """更新时间窗（仅超级管理员）"""
    service = RuleSetService(db)
    window = await service.update_window(window_id, data, current_admin["id"])
    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="时间窗不存在"
        )
    return window


@router.delete(
    "/windows/{window_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除时间窗",
    description="""
    删除时间窗配置（仅超级管理员）。

    **参数说明**：
    - window_id: 时间窗ID（路径参数）

    **业务规则**：
    - 时间窗不存在时返回 404
    - 返回 204 No Content
    """,
)
async def delete_window(
    window_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """删除时间窗（仅超级管理员）"""
    service = RuleSetService(db)
    success = await service.delete_window(window_id, current_admin["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="时间窗不存在"
        )
    return None


# ==================== Policy 独立管理 ====================

@router.put(
    "/{rule_set_id}/booking-policy",
    response_model=RuleBookingPolicyResponse,
    summary="更新预约策略",
    description="""
    更新规则组的预约策略（仅超级管理员）。

    **业务规则**：
    - 策略不存在则自动创建，存在则更新（upsert）
    - 规则组不存在时返回 404
    - 预约策略控制：提前预约天数限制、同日预约上限等

    **参数说明**：
    - rule_set_id: 规则组ID（路径参数）
    """,
)
async def update_booking_policy(
    rule_set_id: str,
    data: RuleBookingPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """更新预约策略（仅超级管理员）

    如果策略不存在则创建，存在则更新
    """
    service = RuleSetService(db)

    # 先检查规则组是否存在
    rule_set = await service.get_by_id(rule_set_id)
    if not rule_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )

    policy = await service.update_booking_policy(rule_set_id, data, current_admin["id"])
    return policy


@router.put(
    "/{rule_set_id}/checkin-policy",
    response_model=RuleCheckinPolicyResponse,
    summary="更新签到策略",
    description="""
    更新规则组的签到策略（仅超级管理员）。

    **业务规则**：
    - 策略不存在则自动创建，存在则更新（upsert）
    - 规则组不存在时返回 404
    - 签到策略控制：签到开放时间、签到截止时间、迟到处理等

    **参数说明**：
    - rule_set_id: 规则组ID（路径参数）
    """,
)
async def update_checkin_policy(
    rule_set_id: str,
    data: RuleCheckinPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """更新签到策略（仅超级管理员）

    如果策略不存在则创建，存在则更新
    """
    service = RuleSetService(db)

    # 先检查规则组是否存在
    rule_set = await service.get_by_id(rule_set_id)
    if not rule_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )

    policy = await service.update_checkin_policy(rule_set_id, data, current_admin["id"])
    return policy


@router.put(
    "/{rule_set_id}/capacity-policy",
    response_model=RuleCapacityPolicyResponse,
    summary="更新容量策略",
    description="""
    更新规则组的容量策略（仅超级管理员）。

    **业务规则**：
    - 策略不存在则自动创建，存在则更新（upsert）
    - 规则组不存在时返回 404
    - 容量策略控制：号源上限、超号规则、候补机制等

    **参数说明**：
    - rule_set_id: 规则组ID（路径参数）
    """,
)
async def update_capacity_policy(
    rule_set_id: str,
    data: RuleCapacityPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """更新容量策略（仅超级管理员）

    如果策略不存在则创建，存在则更新
    """
    service = RuleSetService(db)

    # 先检查规则组是否存在
    rule_set = await service.get_by_id(rule_set_id)
    if not rule_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )

    policy = await service.update_capacity_policy(rule_set_id, data, current_admin["id"])
    return policy


# ==================== 审计日志 ====================

@router.get(
    "/{rule_set_id}/audit-logs",
    response_model=PageResult[RuleSetAuditLogResponse],
    summary="获取规则组审计日志",
    description="""
    获取指定规则组的变更历史记录。

    **参数说明**：
    - rule_set_id: 规则组ID（路径参数）
    - page: 页码（默认1）
    - page_size: 每页数量（默认20，最大100）

    **返回数据**：
    - 按时间倒序排列的审计日志列表
    - 每条记录包含操作类型、资源类型、操作前后快照
    """,
)
async def get_audit_logs(
    rule_set_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """获取规则组审计日志"""
    service = RuleSetService(db)
    logs, total = await service.get_audit_logs(rule_set_id, page=page, page_size=page_size)
    return {"data": logs, "total": total}
