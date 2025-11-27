from fastapi import APIRouter, Depends
from typing import List

router = APIRouter()

@router.get("/profile")
async def get_profile():
    """获取当前用户信息"""
    return {"id": "1", "name": "测试用户", "phone": "13800138000"}

@router.put("/profile")
async def update_profile():
    """更新用户信息"""
    return {"message": "更新成功"}

@router.get("/patients")
async def get_patients():
    """获取就诊人列表"""
    return []

@router.post("/patients")
async def add_patient():
    """添加就诊人"""
    return {"message": "添加成功"}

