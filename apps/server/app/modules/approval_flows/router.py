"""审批流定义路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth_deps import get_current_admin
from app.common.permission_deps import require_permission
from app.db.session import get_db
from app.modules.approval_flows.schemas import (
    FlowDefinitionCreate,
    FlowDefinitionListResponse,
    FlowDefinitionResponse,
    FlowDefinitionUpdate,
)
from app.modules.approval_flows.service_definitions import FlowDefinitionService

router = APIRouter()


@router.get("", summary="获取流程定义列表")
async def list_flow_definitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    business_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:list")),
):
    service = FlowDefinitionService(db)
    items, total = await service.get_list(page, page_size, business_type, status)
    return {
        "items": [FlowDefinitionListResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/by-business/{business_type}", summary="按业务类型获取激活流程")
async def get_by_business_type(
    business_type: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:list")),
):
    service = FlowDefinitionService(db)
    flow_def = await service.get_by_business_type(business_type)
    if not flow_def:
        return None
    return FlowDefinitionResponse.model_validate(flow_def)


@router.get("/templates/list", summary="获取流程模板列表")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:list")),
):
    """返回预置的流程模板"""
    templates = [
        {
            "id": "tpl_leave_request",
            "name": "停诊审批模板",
            "businessType": "leave_request",
            "description": "医生停诊申请 -> 科室负责人审批 -> 医务部审批",
            "nodes": [
                {"nodeKey": "start", "nodeName": "发起申请", "nodeType": "start", "sortOrder": 0, "positionX": 250, "positionY": 0},
                {"nodeKey": "dept_approval", "nodeName": "科室负责人审批", "nodeType": "approval", "approvalMode": "or", "assigneeType": "department", "sortOrder": 1, "positionX": 250, "positionY": 120},
                {"nodeKey": "condition_days", "nodeName": "请假天数判断", "nodeType": "condition", "sortOrder": 2, "positionX": 250, "positionY": 240, "conditions": [
                    {"targetNodeKey": "medical_approval", "fieldName": "days", "operator": "gt", "value": "3", "priority": 0}
                ]},
                {"nodeKey": "medical_approval", "nodeName": "医务部审批", "nodeType": "approval", "approvalMode": "or", "assigneeType": "role", "assigneeConfig": {"role_codes": ["MEDICAL_ADMIN"]}, "sortOrder": 3, "positionX": 250, "positionY": 360},
                {"nodeKey": "end", "nodeName": "结束", "nodeType": "end", "sortOrder": 4, "positionX": 250, "positionY": 480},
            ],
            "edges": [
                {"source": "start", "target": "dept_approval"},
                {"source": "dept_approval", "target": "condition_days"},
                {"source": "condition_days", "target": "medical_approval"},
                {"source": "condition_days", "target": "end", "sourceHandle": "default"},
                {"source": "medical_approval", "target": "end"},
            ],
        },
        {
            "id": "tpl_extra_quota",
            "name": "加号审批模板",
            "businessType": "extra_quota",
            "description": "医生加号申请 -> 科室负责人审批",
            "nodes": [
                {"nodeKey": "start", "nodeName": "发起申请", "nodeType": "start", "sortOrder": 0, "positionX": 250, "positionY": 0},
                {"nodeKey": "dept_approval", "nodeName": "科室负责人审批", "nodeType": "approval", "approvalMode": "or", "assigneeType": "department", "sortOrder": 1, "positionX": 250, "positionY": 120},
                {"nodeKey": "end", "nodeName": "结束", "nodeType": "end", "sortOrder": 2, "positionX": 250, "positionY": 240},
            ],
            "edges": [
                {"source": "start", "target": "dept_approval"},
                {"source": "dept_approval", "target": "end"},
            ],
        },
        {
            "id": "tpl_simple",
            "name": "简单审批模板",
            "businessType": "custom",
            "description": "发起人 -> 审批人 -> 结束（最简流程）",
            "nodes": [
                {"nodeKey": "start", "nodeName": "发起申请", "nodeType": "start", "sortOrder": 0, "positionX": 250, "positionY": 0},
                {"nodeKey": "approval_1", "nodeName": "审批", "nodeType": "approval", "approvalMode": "or", "assigneeType": "user", "sortOrder": 1, "positionX": 250, "positionY": 120},
                {"nodeKey": "end", "nodeName": "结束", "nodeType": "end", "sortOrder": 2, "positionX": 250, "positionY": 240},
            ],
            "edges": [
                {"source": "start", "target": "approval_1"},
                {"source": "approval_1", "target": "end"},
            ],
        },
    ]
    return {"items": templates}


@router.post("/{flow_def_id}/export", summary="导出流程定义 JSON")
async def export_flow(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:list")),
):
    """导出流程定义的完整 JSON（可用于导入）"""
    service = FlowDefinitionService(db)
    flow_def = await service.get_by_id(flow_def_id)
    if not flow_def:
        raise HTTPException(status_code=404, detail="流程定义不存在")

    export_data = {
        "name": flow_def.name,
        "businessType": flow_def.business_type,
        "description": flow_def.description,
        "formSchema": flow_def.form_schema,
        "callbackConfig": flow_def.callback_config,
        "nodes": [
            {
                "nodeKey": n.node_key,
                "nodeName": n.node_name,
                "nodeType": n.node_type,
                "approvalMode": n.approval_mode,
                "assigneeType": n.assignee_type,
                "assigneeConfig": n.assignee_config,
                "timeoutHours": n.timeout_hours,
                "timeoutAction": n.timeout_action,
                "sortOrder": n.sort_order,
                "positionX": n.position_x,
                "positionY": n.position_y,
                "conditions": [
                    {
                        "targetNodeKey": c.target_node_key,
                        "fieldName": c.field_name,
                        "operator": c.operator,
                        "value": c.value,
                        "priority": c.priority,
                    }
                    for c in n.conditions
                ],
            }
            for n in flow_def.nodes
        ],
        "edges": flow_def.edges or [],
    }
    return export_data


@router.post("/import", summary="导入流程定义")
async def import_flow(
    data: FlowDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:create")),
    current_admin: dict = Depends(get_current_admin),
):
    """导入流程定义（接受导出的 JSON 格式，创建为草稿状态）"""
    service = FlowDefinitionService(db)
    flow_def = await service.create(data, current_admin["id"])
    await db.commit()
    return FlowDefinitionResponse.model_validate(flow_def)


@router.get("/{flow_def_id}", summary="获取流程定义详情")
async def get_flow_definition(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:list")),
):
    service = FlowDefinitionService(db)
    flow_def = await service.get_by_id(flow_def_id)
    if not flow_def:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    return FlowDefinitionResponse.model_validate(flow_def)


@router.post("", summary="创建流程定义")
async def create_flow_definition(
    data: FlowDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:create")),
    current_admin: dict = Depends(get_current_admin),
):
    service = FlowDefinitionService(db)
    flow_def = await service.create(data, current_admin["id"])
    await db.commit()
    return FlowDefinitionResponse.model_validate(flow_def)


@router.put("/{flow_def_id}", summary="更新流程定义")
async def update_flow_definition(
    flow_def_id: str,
    data: FlowDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:update")),
    current_admin: dict = Depends(get_current_admin),
):
    service = FlowDefinitionService(db)
    try:
        flow_def = await service.update(flow_def_id, data, current_admin["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not flow_def:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    await db.commit()
    return FlowDefinitionResponse.model_validate(flow_def)


@router.put("/{flow_def_id}/activate", summary="激活流程")
async def activate_flow(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:manage")),
    current_admin: dict = Depends(get_current_admin),
):
    service = FlowDefinitionService(db)
    try:
        flow_def = await service.activate(flow_def_id, current_admin["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not flow_def:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    await db.commit()
    return FlowDefinitionResponse.model_validate(flow_def)


@router.put("/{flow_def_id}/archive", summary="归档流程")
async def archive_flow(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:manage")),
    current_admin: dict = Depends(get_current_admin),
):
    service = FlowDefinitionService(db)
    flow_def = await service.archive(flow_def_id, current_admin["id"])
    if not flow_def:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    await db.commit()
    return FlowDefinitionResponse.model_validate(flow_def)


@router.delete("/{flow_def_id}", summary="删除流程")
async def delete_flow(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:delete")),
    current_admin: dict = Depends(get_current_admin),
):
    service = FlowDefinitionService(db)
    try:
        result = await service.delete(flow_def_id, current_admin["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    await db.commit()
    return {"deleted": True}


@router.post("/{flow_def_id}/copy", summary="复制流程定义")
async def copy_flow(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:create")),
    current_admin: dict = Depends(get_current_admin),
):
    service = FlowDefinitionService(db)
    flow_def = await service.copy(flow_def_id, current_admin["id"])
    if not flow_def:
        raise HTTPException(status_code=404, detail="流程定义不存在")
    await db.commit()
    return FlowDefinitionResponse.model_validate(flow_def)


@router.get("/{flow_def_id}/validate", summary="校验流程定义")
async def validate_flow(
    flow_def_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("approval-flow:list")),
):
    service = FlowDefinitionService(db)
    return await service.validate(flow_def_id)
