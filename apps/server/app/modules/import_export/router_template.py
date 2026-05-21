"""导入模板下载端点"""
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from io import BytesIO

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.infrastructure.excel.import_service import ExcelImportService

router = APIRouter()


@router.get("/doctors", summary="下载医生导入模板")
async def download_doctor_template(
    current_admin = Depends(get_current_admin),
):
    """下载医生导入模板"""
    headers = ["姓名", "性别", "手机号", "门店名称", "科室名称", "职称", "擅长", "标签"]
    required_fields = ["姓名", "门店名称", "科室名称"]
    sample_data = [
        ["张医生", "男", "13800138000", "总院", "内科", "主任医师", "心血管疾病", "专家,推荐"],
        ["李医生", "女", "13900139000", "分院", "外科", "副主任医师", "骨科手术", "骨科专家"],
        ["王医生", "未知", "13700137000", "总院", "儿科", "主治医师", "儿科常见病", "儿科"],
    ]
    field_notes = {
        "姓名": "必填，医生姓名",
        "性别": "未知/男/女",
        "手机号": "11位手机号",
        "门店名称": "必填，需与系统中门店名称一致",
        "科室名称": "必填，需与系统中科室名称一致",
        "职称": "如：主任医师、副主任医师、主治医师等",
        "擅长": "医生擅长的领域",
        "标签": "多个标签用逗号分隔",
    }

    excel_bytes = ExcelImportService.create_template(headers, sample_data, required_fields, field_notes)

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=doctor_import_template.xlsx"}
    )


@router.get("/patients", summary="下载患者导入模板")
async def download_patient_template(
    current_admin = Depends(get_current_admin),
):
    """下载患者导入模板"""
    headers = ["姓名", "手机号", "身份证号", "性别", "出生日期", "与本人关系", "省", "市", "区", "详细地址"]
    required_fields = ["姓名", "手机号"]
    sample_data = [
        ["张三", "13800138000", "110101199001011234", "男", "1990-01-01", "本人", "北京市", "北京市", "朝阳区", "xx街道xx号"],
        ["李四", "13900139000", "110101199502021234", "女", "1995-02-02", "配偶", "北京市", "北京市", "海淀区", "xx路xx号"],
    ]
    field_notes = {
        "姓名": "必填，患者姓名",
        "手机号": "必填，11位手机号",
        "身份证号": "18位身份证号",
        "性别": "未知/男/女",
        "出生日期": "格式：YYYY-MM-DD",
        "与本人关系": "本人/父母/配偶/子女/其他",
        "省": "省份",
        "市": "城市",
        "区": "区县",
        "详细地址": "详细地址",
    }

    excel_bytes = ExcelImportService.create_template(headers, sample_data, required_fields, field_notes)

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=patient_import_template.xlsx"}
    )


@router.get("/departments", summary="下载科室导入模板")
async def download_department_template(
    current_admin= Depends(get_current_admin),
):
    """下载科室导入模板"""
    headers = ["科室名称", "门店名称", "科室标签", "排序", "是否终极科室", "是否推荐", "是否热门"]
    required_fields = ["科室名称", "门店名称"]
    sample_data = [
        ["内科", "总院", "常见病", "1", "是", "是", "是"],
        ["外科", "总院", "手术", "2", "是", "否", "否"],
    ]
    field_notes = {
        "科室名称": "必填，科室名称",
        "门店名称": "必填，需与系统中门店名称一致",
        "科室标签": "科室标签",
        "排序": "数字，越小越靠前",
        "是否终极科室": "是/否，终极科室可绑定医生",
        "是否推荐": "是/否",
        "是否热门": "是/否",
    }

    excel_bytes = ExcelImportService.create_template(headers, sample_data, required_fields, field_notes)

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=department_import_template.xlsx"}
    )


@router.get("/schedules", summary="下载排班导入模板")
async def download_schedule_template(
    current_admin=Depends(get_current_admin),
):
    """下载排班导入模板"""
    headers = ["医生姓名", "门店名称", "日期", "时段", "开始时间", "结束时间", "总号源", "在线号源"]
    required_fields = ["医生姓名", "门店名称", "日期", "时段", "开始时间", "结束时间", "总号源"]
    sample_data = [
        ["张医生", "总院", "2026-06-01", "morning", "08:00", "12:00", 20, 15],
        ["张医生", "总院", "2026-06-01", "afternoon", "14:00", "17:00", 15, 10],
        ["李医生", "分院", "2026-06-02", "morning", "08:30", "11:30", 10, 8],
    ]
    field_notes = {
        "医生姓名": "必填，需与系统中医生姓名一致",
        "门店名称": "必填，需与系统中门店名称一致",
        "日期": "必填，格式：YYYY-MM-DD",
        "时段": "必填，morning/afternoon/evening",
        "开始时间": "必填，格式：HH:MM",
        "结束时间": "必填，格式：HH:MM",
        "总号源": "必填，大于0的整数",
        "在线号源": "可选，线上可预约号源数，默认等于总号源",
    }

    excel_bytes = ExcelImportService.create_template(headers, sample_data, required_fields, field_notes)

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=schedule_import_template.xlsx"}
    )


@router.get("/stores", summary="下载门店导入模板")
async def download_store_template(
    current_admin = Depends(get_current_admin),
):
    """下载门店导入模板"""
    headers = ["门店名称", "门店编码", "城市", "地址", "联系电话", "营业时间"]
    required_fields = ["门店名称", "城市"]
    sample_data = [
        ["总院", "STORE001", "北京", "北京市朝阳区xx路xx号", "010-12345678", "08:00-17:00"],
        ["分院", "STORE002", "上海", "上海市浦东新区xx路xx号", "021-12345678", "08:30-17:30"],
    ]
    field_notes = {
        "门店名称": "必填，门店名称",
        "门店编码": "门店唯一编码",
        "城市": "必填，所在城市",
        "地址": "详细地址",
        "联系电话": "联系电话",
        "营业时间": "如：08:00-17:00",
    }

    excel_bytes = ExcelImportService.create_template(headers, sample_data, required_fields, field_notes)

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=store_import_template.xlsx"}
    )


@router.get("/rule-sets", summary="下载规则组导入模板")
async def download_rule_set_template(
    current_admin = Depends(get_current_admin),
):
    """下载规则组导入模板（多工作表：规则组、时间窗、预约策略、签到策略、容量策略）"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Comment

    wb = Workbook()

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    required_fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")

    sheets_config = {
        "规则组": {
            "headers": ["规则组名称", "优先级", "是否启用", "时间来源", "时区来源", "比较精度",
                        "开放边界包含", "截止边界包含", "取整模式", "时钟偏差容忍度(秒)", "描述"],
            "required": ["规则组名称"],
            "sample": [
                ["标准门诊规则", 100, "是", "SERVER", "HOSPITAL", "SECOND", "是", "否", "NONE", 5, "标准门诊预约规则"],
            ],
            "notes": {
                "规则组名称": "必填，规则组名称",
                "优先级": "数字，越小越优先，默认100",
                "是否启用": "是/否",
                "时间来源": "SERVER/CLIENT",
                "时区来源": "HOSPITAL/SHIFT/USER",
                "比较精度": "SECOND/MILLISECOND/MINUTE",
                "取整模式": "NONE/CEIL/FLOOR/ROUND",
            },
        },
        "时间窗": {
            "headers": ["规则组名称", "动作类型", "参考点", "开放偏移(秒)", "截止偏移(秒)",
                        "开放边界包含", "截止边界包含", "失败策略", "失败标签", "是否启用", "描述"],
            "required": ["规则组名称", "动作类型", "参考点"],
            "sample": [
                ["标准门诊规则", "BOOK", "SHIFT_START", -604800, 0, "是", "否", "REJECT", "", "是", "提前7天开放预约"],
                ["标准门诊规则", "CHECKIN", "SHIFT_START", -1800, 900, "是", "否", "REJECT", "", "是", "提前30分钟开放签到"],
                ["标准门诊规则", "CANCEL", "SHIFT_START", -86400, 0, "是", "否", "REJECT", "", "是", "提前1天可取消"],
            ],
            "notes": {
                "规则组名称": "必填，需与「规则组」表中的名称一致",
                "动作类型": "BOOK/CHECKIN/CANCEL/HOLD_RELEASE",
                "参考点": "SHIFT_START/SHIFT_END/BOOKING_CREATED_AT",
                "开放偏移(秒)": "负数=提前，正数=延后",
                "失败策略": "REJECT/ALLOW_WITH_TAG/AUTO_TO_WAITLIST",
            },
        },
        "预约策略": {
            "headers": ["规则组名称", "要求登录", "要求档案完整", "每用户每班次", "每用户每天", "每用户每周",
                        "同班次冲突策略", "时间重叠策略", "同类型同日策略"],
            "required": ["规则组名称"],
            "sample": [
                ["标准门诊规则", "是", "否", 1, 3, 10, "REJECT", "REJECT", "ALLOW"],
            ],
            "notes": {
                "规则组名称": "必填，需与「规则组」表中的名称一致",
                "同班次冲突策略": "REJECT/REPLACE",
                "时间重叠策略": "REJECT/ALLOW",
                "同类型同日策略": "REJECT/ALLOW",
            },
        },
        "签到策略": {
            "headers": ["规则组名称", "必须预约", "允许现场补约", "允许签到次数", "记录审计日志",
                        "宽限期(秒)", "宽限后状态", "截止后未签到处理"],
            "required": ["规则组名称"],
            "sample": [
                ["标准门诊规则", "是", "否", 1, "是", 900, "LATE", "KEEP_BOOKED"],
            ],
            "notes": {
                "规则组名称": "必填，需与「规则组」表中的名称一致",
                "宽限后状态": "LATE/ON_TIME",
                "截止后未签到处理": "KEEP_BOOKED/AUTO_CANCEL/ABSENT",
            },
        },
        "容量策略": {
            "headers": ["规则组名称", "总容量", "每用户容量", "启用候补", "候补队列最大长度",
                        "候补递补策略", "允许超额", "超额最大数量"],
            "required": ["规则组名称"],
            "sample": [
                ["标准门诊规则", 50, 1, "否", 0, "MANUAL", "否", 0],
            ],
            "notes": {
                "规则组名称": "必填，需与「规则组」表中的名称一致",
                "总容量": "0表示不限制",
                "候补递补策略": "MANUAL/AUTO",
            },
        },
    }

    # 删除默认工作表
    default_sheet = wb.active
    wb.remove(default_sheet)

    for sheet_name, config in sheets_config.items():
        ws = wb.create_sheet(title=sheet_name)
        headers = config["headers"]
        required = config.get("required", [])
        notes = config.get("notes", {})

        # 写入表头
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = required_fill if header in required else header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if header in notes:
                cell.comment = Comment(notes[header], "system")

        # 写入示例数据
        for row_idx, row_data in enumerate(config.get("sample", []), 2):
            for col_idx, value in enumerate(row_data, 1):
                ws.cell(row=row_idx, column=col_idx, value=value)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=rule_set_import_template.xlsx"}
    )
