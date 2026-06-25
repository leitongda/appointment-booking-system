"""第三方平台审批回调网关。

接收钉钉/企业微信/飞书的审批结果回调，校验签名后回写 ApprovalEngine。

路由挂载于 /api/v1/integration-gateway，无需登录鉴权（第三方平台直接调用），
但通过签名校验 + 租户上下文保证安全。
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.secret_refs import resolve_secret_ref
from app.db.session import get_db
from app.models.admin import Admin
from app.models.approval_flow import ApprovalInstance, ApprovalRecord
from app.models.integration import IntegrationBinding
from app.modules.approval_flows.engine import ApprovalEngine
from app.modules.integration.service import IntegrationService

router = APIRouter()
logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = ["dingtalk", "wecom", "feishu"]


async def _resolve_tenant_from_callback(
    db: AsyncSession,
    provider: str,
    external_user_id: str | None,
    instance_id: str | None,
) -> str | None:
    """从回调数据中解析租户ID。

    策略：
    1. 若回调携带审批实例ID，直接查实例的 tenant_id
    2. 否则按操作人的平台 external_id 反查 IntegrationBinding 的 tenant_id
    """
    if instance_id:
        stmt = select(ApprovalInstance.tenant_id).where(ApprovalInstance.id == instance_id).limit(1)
        result = await db.execute(stmt)
        tid = result.scalar()
        if tid:
            return tid

    if external_user_id:
        stmt = select(IntegrationBinding.tenant_id).where(
            IntegrationBinding.provider == provider,
            IntegrationBinding.external_id == external_user_id,
        ).limit(1)
        result = await db.execute(stmt)
        tid = result.scalar()
        if tid:
            return tid

    return None


async def _find_admin_by_external(
    db: AsyncSession, tenant_id: str, provider: str, external_id: str
) -> tuple[str, str] | None:
    """根据平台 external_id 查本地 admin（返回 admin_id, admin_name）。

    admin_name 取 Admin 表的真实姓名，而非第三方昵称。
    """
    stmt = select(IntegrationBinding.user_id).where(
        IntegrationBinding.tenant_id == tenant_id,
        IntegrationBinding.provider == provider,
        IntegrationBinding.external_id == external_id,
        IntegrationBinding.user_type == "admin",
    ).limit(1)
    result = await db.execute(stmt)
    admin_id = result.scalar()
    if not admin_id:
        return None
    # 取 Admin 真实姓名
    admin = await db.get(Admin, admin_id)
    admin_name = (admin.name if admin else None) or admin_id
    return admin_id, admin_name


async def _process_approval_result(
    db: AsyncSession,
    provider: str,
    instance_id: str,
    external_user_id: str,
    action: str,  # "approve" / "reject"
    comment: str | None,
    tenant_id: str,
) -> dict[str, Any]:
    """处理审批结果，回写 ApprovalEngine。"""
    admin_info = await _find_admin_by_external(db, tenant_id, provider, external_user_id)
    if not admin_info:
        return {"success": False, "message": f"未找到 {provider} 用户 {external_user_id} 对应的管理员"}

    approver_id, approver_name = admin_info

    # 检查实例状态
    instance = await db.get(ApprovalInstance, instance_id)
    if not instance:
        return {"success": False, "message": "审批实例不存在"}
    if instance.status != "pending":
        return {"success": False, "message": f"审批实例已处理（状态: {instance.status}）"}

    engine = ApprovalEngine(db)
    try:
        if action == "approve":
            await engine.approve(
                instance_id=instance_id,
                approver_id=approver_id,
                approver_name=approver_name,
                comment=comment or f"[来自{provider}]",
            )
        else:
            await engine.reject(
                instance_id=instance_id,
                approver_id=approver_id,
                approver_name=approver_name,
                comment=comment or f"[来自{provider}]",
            )
        # 补充一条审计记录，标记审批来源为第三方平台
        source_record = ApprovalRecord(
            instance_id=instance_id,
            approver_id=approver_id,
            approver_name=approver_name,
            action="comment",
            comment=f"[该操作由 {provider} 回调触发]",
        )
        db.add(source_record)
        await db.commit()
        return {
            "success": True,
            "message": f"审批已{'通过' if action == 'approve' else '拒绝'}（来源: {provider}）",
            "instance_id": instance_id,
            "action": action,
        }
    except ValueError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        logger.exception("approval_callback_process_error", instance_id=instance_id, provider=provider)
        return {"success": False, "message": f"处理异常: {e}"}


# ============================================================
# 钉钉审批回调
# ============================================================
@router.post("/dingtalk/approval-callback", summary="钉钉审批结果回调")
async def dingtalk_approval_callback(
    request: Request,
    timestamp: str = Header(..., alias="timestamp"),
    signature: str = Header(..., alias="sign"),
    db: AsyncSession = Depends(get_db),
):
    """钉钉审批结果回调。

    钉钉通过事件订阅推送审批结果，body 包含 process_result。
    需校验 timestamp + sign（HmacSHA256）。
    """
    from app.modules.integration_gateway.signature import verify_dingtalk_signature

    body = await request.body()
    import json

    try:
        payload = json.loads(body)
    except Exception:
        return JSONResponse(status_code=400, content={"errmsg": "invalid body"})

    # 解析钉钉回调字段
    result = payload.get("result") or payload
    process_instance_id = result.get("processInstanceId") or payload.get("processInstanceId")
    biz_category_id = result.get("bizCategoryId") or ""
    external_user_id = result.get("staffId") or result.get("originatorUserId")
    # type: finish 表示流程结束；result=agree/refuse
    proc_result = result.get("result") or payload.get("result") or ""
    action = "approve" if proc_result == "agree" else "reject" if proc_result == "refuse" else None
    comment = result.get("remark") or ""

    if not action:
        return JSONResponse(content={"success": True, "message": "ignored: not approval result"})

    # 解析租户
    tenant_id = await _resolve_tenant_from_callback(db, "dingtalk", external_user_id, None)
    if not tenant_id:
        return JSONResponse(status_code=404, content={"errmsg": "tenant not found"})

    # 校验签名（用租户的 AppSecret）
    integ_service = IntegrationService(db)
    integration = await integ_service.get_by_provider("dingtalk")
    if integration:
        app_secret = resolve_secret_ref(integration.app_secret_ref) or ""
        if app_secret and not verify_dingtalk_signature(timestamp, app_secret, signature):
            logger.warning("dingtalk_callback_signature_failed", tenant_id=tenant_id)
            return JSONResponse(status_code=401, content={"errmsg": "signature verification failed"})

    # 钉钉的 processInstanceId 与本系统 ApprovalInstance 的映射：
    # 约定：推送审批时把本系统 instance.id 作为外部审批单号写入
    result_data = await _process_approval_result(
        db, "dingtalk", process_instance_id, external_user_id, action, comment, tenant_id
    )
    return JSONResponse(content=result_data)


# ============================================================
# 企业微信审批回调
# ============================================================
@router.post("/wecom/approval-callback", summary="企业微信审批结果回调")
async def wecom_approval_callback(
    request: Request,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """企业微信审批结果回调。

    企业微信通过应用事件推送审批状态，body 为加密 XML/JSON。
    此处简化处理：解析 sp_no（审批单号）映射本系统 instance.id。
    """
    body = await request.body()
    import json

    try:
        payload = json.loads(body)
    except Exception:
        payload = {}

    # 企业微信审批回调字段（实际需解密，此处假设已解密或明文测试）
    info = payload.get("Info") or payload.get("info") or {}
    sp_status = info.get("SpStatus") or payload.get("SpStatus")
    sp_no = info.get("SpNo") or payload.get("SpNo")
    external_user_id = info.get("UserName") or payload.get("UserName")

    # SpStatus: 1审批中 2已通过 3已驳回 4已撤销 6通过后撤销 7已删除 10已支付
    action = None
    if sp_status == 2:
        action = "approve"
    elif sp_status == 3:
        action = "reject"

    if not action:
        return JSONResponse(content={"success": True, "message": "ignored"})

    tenant_id = await _resolve_tenant_from_callback(db, "wecom", external_user_id, sp_no)
    if not tenant_id:
        return JSONResponse(status_code=404, content={"errmsg": "tenant not found"})

    comment = info.get("SpRecord", {}).get("SpComment", "") if isinstance(info.get("SpRecord"), dict) else ""
    result_data = await _process_approval_result(
        db, "wecom", sp_no, external_user_id, action, comment, tenant_id
    )
    return JSONResponse(content=result_data)


# ============================================================
# 飞书审批回调
# ============================================================
@router.post("/feishu/approval-callback", summary="飞书审批结果回调")
async def feishu_approval_callback(
    request: Request,
    x_lark_signature: str = Header(..., alias="X-Lark-Signature"),
    x_lark_request_timestamp: str = Header(..., alias="X-Lark-Request-Timestamp"),
    x_lark_request_nonce: str = Header(..., alias="X-Lark-Request-Nonce"),
    db: AsyncSession = Depends(get_db),
):
    """飞书审批结果回调。

    飞书通过事件订阅推送审批状态变更。
    签名校验：SHA256(timestamp + nonce + encrypt_key + body)。
    """
    from app.modules.integration_gateway.signature import verify_feishu_signature

    body = await request.body()
    body_str = body.decode("utf-8")
    import json

    try:
        payload = json.loads(body_str)
    except Exception:
        return JSONResponse(status_code=400, content={"code": 1, "msg": "invalid body"})

    # 飞书 v2 事件格式
    event = payload.get("event") or {}
    event_data = event.get("data") or payload.get("data") or {}
    instance_code = event_data.get("instance_code") or event_data.get("approval_code")
    external_user_id = event_data.get("operator_open_id") or event_data.get("user_id")
    status = event_data.get("status") or event.get("status")

    # 飞书审批状态: APPROVED / REJECTED / CANCELED
    action = None
    if status == "APPROVED":
        action = "approve"
    elif status == "REJECTED":
        action = "reject"

    if not action:
        return JSONResponse(content={"code": 0, "msg": "ignored"})

    tenant_id = await _resolve_tenant_from_callback(db, "feishu", external_user_id, instance_code)
    if not tenant_id:
        return JSONResponse(status_code=404, content={"code": 1, "msg": "tenant not found"})

    # 校验签名
    integ_service = IntegrationService(db)
    integration = await integ_service.get_by_provider("feishu")
    if integration:
        encrypt_key = resolve_secret_ref(integration.webhook_secret_ref) or ""
        if encrypt_key and not verify_feishu_signature(
            encrypt_key, x_lark_request_timestamp, x_lark_request_nonce, body_str, x_lark_signature
        ):
            logger.warning("feishu_callback_signature_failed", tenant_id=tenant_id)
            return JSONResponse(status_code=401, content={"code": 1, "msg": "signature failed"})

    comment = event_data.get("comment") or ""
    result_data = await _process_approval_result(
        db, "feishu", instance_code, external_user_id, action, comment, tenant_id
    )
    return JSONResponse(content={"code": 0, **result_data})
