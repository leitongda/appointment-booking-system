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
from app.services.excel_service import ExcelImportService

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
        "与本人关系": "本人/父亲/母亲/配偶/子女/其他",
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
