from fastapi import APIRouter
from typing import List

router = APIRouter()

@router.get("")
async def get_departments():
    """获取科室列表"""
    return {"data": [], "total": 0}

@router.get("/tree")
async def get_department_tree():
    """获取科室树"""
    return []

@router.get("/hot")
async def get_hot_departments():
    """获取热门科室"""
    return []

@router.get("/{id}")
async def get_department(id: str):
    """获取科室详情"""
    return {"id": id, "name": "内科"}

@router.post("")
async def create_department():
    """创建科室"""
    return {"message": "创建成功"}

@router.put("/{id}")
async def update_department(id: str):
    """更新科室"""
    return {"message": "更新成功"}

@router.delete("/{id}")
async def delete_department(id: str):
    """删除科室"""
    return {"message": "删除成功"}

