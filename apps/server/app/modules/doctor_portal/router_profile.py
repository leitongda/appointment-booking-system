"""医生个人信息相关端点"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_doctor_by_token
from app.models.doctor import Doctor

router = APIRouter()


@router.get("/me", summary="获取我的信息")
async def get_my_info(
    doctor: Doctor = Depends(get_current_doctor_by_token),
):
    """获取当前医生信息"""
    return {
        "id": doctor.id,
        "name": doctor.name,
        "phone": doctor.phone,
        "title": doctor.title,
        "avatar": doctor.avatar,
        "store_id": doctor.store_id,
        "store_name": doctor.store.name if doctor.store else None,
        "department_id": doctor.department_id,
        "department_name": doctor.department.name if doctor.department else None,
        "specialty": doctor.specialty,
        "introduction": doctor.introduction,
    }
