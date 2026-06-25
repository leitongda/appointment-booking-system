"""联系人 CRUD 路由"""

import csv
import io
import logging
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.auth_deps import get_current_admin
from app.common.permission_deps import require_permission
from app.db.session import get_db
from app.models.contact import Contact, ContactChannel
from app.modules.contacts.schemas import (
    BatchDeleteRequest,
    BatchMoveGroupRequest,
    BatchTagRequest,
    ContactCreate,
    ContactListResponse,
    ContactQuery,
    ContactResponse,
    ContactUpdate,
)
from app.modules.contacts.service import ContactService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", summary="获取联系人列表")
async def list_contacts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    contact_type: str | None = None,
    status: int | None = None,
    group_id: str | None = None,
    store_id: str | None = None,
    department_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:view")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactService(db)
    items, total = await service.get_list(
        tenant_id=current_admin["tenant_id"],
        keyword=keyword,
        contact_type=contact_type,
        status=status,
        group_id=group_id,
        store_id=store_id,
        department_id=department_id,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [ContactListResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{contact_id}", summary="获取联系人详情")
async def get_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:view")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactService(db)
    contact = await service.get_by_id(contact_id, current_admin["tenant_id"])
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    return ContactResponse.model_validate(contact)


@router.post("", summary="创建联系人")
async def create_contact(
    data: ContactCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:create")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactService(db)
    contact = await service.create(
        data.model_dump(exclude_unset=True),
        tenant_id=current_admin["tenant_id"],
        created_by=current_admin.get("id"),
    )
    await db.commit()
    return ContactResponse.model_validate(contact)


@router.put("/{contact_id}", summary="更新联系人")
async def update_contact(
    contact_id: str,
    data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:edit")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactService(db)
    contact = await service.update(
        contact_id,
        data.model_dump(exclude_unset=True),
        tenant_id=current_admin["tenant_id"],
        updated_by=current_admin.get("id"),
    )
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    await db.commit()
    return ContactResponse.model_validate(contact)


@router.delete("/{contact_id}", summary="删除联系人")
async def delete_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:delete")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactService(db)
    success = await service.delete(contact_id, current_admin["tenant_id"])
    if not success:
        raise HTTPException(status_code=404, detail="联系人不存在")
    await db.commit()
    return {"deleted": True}


@router.get("/export", summary="导出联系人（CSV 格式）")
async def export_contacts(
    keyword: str | None = None,
    contact_type: str | None = None,
    status: int | None = None,
    group_id: str | None = None,
    store_id: str | None = None,
    department_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:export", "contact:view")),
    current_admin: dict = Depends(get_current_admin),
):
    """导出联系人为 CSV 文件"""
    service = ContactService(db)
    items, _ = await service.get_list(
        tenant_id=current_admin["tenant_id"],
        keyword=keyword,
        contact_type=contact_type,
        status=status,
        group_id=group_id,
        store_id=store_id,
        department_id=department_id,
        page=1,
        page_size=10000,
    )

    gender_map = {0: "未知", 1: "男", 2: "女"}
    status_map = {0: "禁用", 1: "正常"}
    type_map = {
        "patient": "患者", "doctor": "医生", "admin": "管理员",
        "staff": "员工", "external": "外部联系人",
    }

    output = io.StringIO()
    # 写入 UTF-8 BOM，确保 Excel 正确识别中文
    output.write("﻿")
    writer = csv.writer(output)
    writer.writerow([
        "姓名", "昵称", "性别", "手机号", "邮箱", "联系人类型",
        "职位", "所属机构", "状态", "分组", "标签", "备注", "创建时间",
    ])

    for c in items:
        groups_str = ",".join(g.name for g in c.groups) if c.groups else ""
        tags_str = ",".join(t.name for t in c.tags) if c.tags else ""
        writer.writerow([
            c.name,
            c.nickname or "",
            gender_map.get(c.gender, ""),
            c.phone or "",
            c.email or "",
            type_map.get(c.contact_type, c.contact_type),
            c.position or "",
            c.organization or "",
            status_map.get(c.status, ""),
            groups_str,
            tags_str,
            c.notes or "",
            c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
        ])

    content = output.getvalue()
    filename = f"contacts_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/import", summary="导入联系人（Excel/CSV）")
async def import_contacts(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:create")),
    current_admin: dict = Depends(get_current_admin),
):
    """从 Excel (.xlsx) 或 CSV 文件导入联系人

    列顺序: 姓名, 昵称, 性别, 手机号, 邮箱, 联系人类型, 职位, 所属机构, 备注
    """
    filename = file.filename or ""
    content = await file.read()

    gender_reverse = {"未知": 0, "男": 1, "女": 2}
    type_reverse = {
        "患者": "patient", "医生": "doctor", "管理员": "admin",
        "员工": "staff", "外部联系人": "external",
    }
    required_headers = ["姓名"]

    rows: list[list[str]] = []

    if filename.lower().endswith(".csv"):
        # CSV 解析
        text = content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        headers = next(reader, None)
        if not headers:
            raise HTTPException(status_code=400, detail="文件为空")
        # 校验必需列
        for rh in required_headers:
            if rh not in headers:
                raise HTTPException(status_code=400, detail=f"缺少必需列: {rh}")
        for row in reader:
            rows.append(row)
    elif filename.lower().endswith((".xlsx", ".xls")):
        # Excel 解析
        from app.infrastructure.excel.import_service import ExcelImportService
        parsed = ExcelImportService.parse_file(content, filename)
        headers = parsed["headers"]
        for rh in required_headers:
            if rh not in headers:
                raise HTTPException(status_code=400, detail=f"缺少必需列: {rh}")
        rows = parsed["data"]
    else:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx、.xls 或 .csv 文件")

    # 构建列索引映射
    col_map = {h: i for i, h in enumerate(headers)}

    def _get(row: list[str], col_name: str) -> str:
        idx = col_map.get(col_name)
        if idx is None or idx >= len(row):
            return ""
        return str(row[idx]).strip()

    service = ContactService(db)
    success_count = 0
    fail_count = 0
    errors: list[dict] = []

    for row_idx, row in enumerate(rows, start=2):
        try:
            name = _get(row, "姓名")
            if not name:
                errors.append({"row": row_idx, "error": "姓名为空"})
                fail_count += 1
                continue

            gender_str = _get(row, "性别")
            gender = gender_reverse.get(gender_str, 0)
            contact_type_str = _get(row, "联系人类型")
            contact_type = type_reverse.get(contact_type_str, contact_type_str or "external")

            data = {
                "name": name,
                "nickname": _get(row, "昵称") or None,
                "gender": gender,
                "phone": _get(row, "手机号") or None,
                "email": _get(row, "邮箱") or None,
                "contact_type": contact_type,
                "position": _get(row, "职位") or None,
                "organization": _get(row, "所属机构") or None,
                "notes": _get(row, "备注") or None,
            }
            await service.create(
                data,
                tenant_id=current_admin["tenant_id"],
                created_by=current_admin.get("id"),
            )
            success_count += 1
        except Exception as e:
            logger.warning(f"导入第 {row_idx} 行失败: {e}")
            errors.append({"row": row_idx, "error": str(e)})
            fail_count += 1

    if success_count > 0:
        await db.commit()

    return {
        "success_count": success_count,
        "fail_count": fail_count,
        "total": success_count + fail_count,
        "errors": errors[:100],
    }


@router.post("/batch-delete", summary="批量删除联系人")
async def batch_delete_contacts(
    data: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:delete")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactService(db)
    count = await service.batch_delete(data.ids, current_admin["tenant_id"])
    await db.commit()
    return {"deleted_count": count}


@router.post("/batch-move-group", summary="批量移动分组")
async def batch_move_group(
    data: BatchMoveGroupRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:edit")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactService(db)
    count = await service.batch_move_group(data.ids, data.group_id, current_admin["tenant_id"])
    await db.commit()
    return {"updated_count": count}


@router.post("/batch-add-tags", summary="批量打标签")
async def batch_add_tags(
    data: BatchTagRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:edit")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactService(db)
    count = await service.batch_add_tags(data.ids, data.tag_ids, current_admin["tenant_id"])
    await db.commit()
    return {"updated_count": count}


@router.post("/batch-remove-tags", summary="批量移除标签")
async def batch_remove_tags(
    data: BatchTagRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:edit")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ContactService(db)
    count = await service.batch_remove_tags(data.ids, data.tag_ids, current_admin["tenant_id"])
    await db.commit()
    return {"updated_count": count}
