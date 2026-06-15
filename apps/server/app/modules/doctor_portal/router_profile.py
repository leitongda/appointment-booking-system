"""医生个人信息相关端点"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_doctor_by_token
from app.db.session import get_db
from app.models.doctor import Doctor

router = APIRouter()


class DoctorProfileUpdate(BaseModel):
    """医生个人信息更新请求"""
    title: str | None = None
    specialty: str | None = None
    introduction: str | None = None
    avatar: str | None = None
    gender: int | None = None
    years_of_experience: int | None = None
    education: str | None = None
    graduate_school: str | None = None
    license_number: str | None = None
    honors: str | None = None
    schedule_desc: str | None = None


@router.get("/me", summary="获取我的信息")
async def get_my_info(
    doctor: Doctor = Depends(get_current_doctor_by_token),
):
    """获取当前医生信息"""
    return {
        "id": doctor.id,
        "name": doctor.name,
        "phone": doctor.phone,
        "email": doctor.email if hasattr(doctor, 'email') else None,
        "title": doctor.title,
        "avatar": doctor.avatar,
        "gender": doctor.gender,
        "years_of_experience": doctor.years_of_experience,
        "education": doctor.education,
        "graduate_school": doctor.graduate_school,
        "license_number": doctor.license_number,
        "honors": doctor.honors,
        "store_id": doctor.store_id,
        "store_name": doctor.store.name if doctor.store else None,
        "department_id": doctor.department_id,
        "department_name": doctor.department.name if doctor.department else None,
        "specialty": doctor.specialty,
        "introduction": doctor.introduction,
        "schedule_desc": doctor.schedule_desc,
    }


@router.put("/me", summary="更新我的信息")
async def update_my_info(
    data: DoctorProfileUpdate,
    doctor: Doctor = Depends(get_current_doctor_by_token),
    db: AsyncSession = Depends(get_db),
):
    """更新当前医生个人信息

    仅允许更新个人展示相关字段，不允许修改姓名、手机、所属门店/科室等管理字段
    """
    update_fields = data.model_dump(exclude_unset=True)

    if not update_fields:
        return {"message": "无更新内容"}

    for field, value in update_fields.items():
        if hasattr(doctor, field):
            setattr(doctor, field, value)

    await db.commit()
    await db.refresh(doctor)

    return {"message": "更新成功", "doctor": {
        "id": doctor.id,
        "name": doctor.name,
        "title": doctor.title,
        "avatar": doctor.avatar,
        "gender": doctor.gender,
        "years_of_experience": doctor.years_of_experience,
        "education": doctor.education,
        "graduate_school": doctor.graduate_school,
        "license_number": doctor.license_number,
        "honors": doctor.honors,
        "specialty": doctor.specialty,
        "introduction": doctor.introduction,
        "schedule_desc": doctor.schedule_desc,
    }}
