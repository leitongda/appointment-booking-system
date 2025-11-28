from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.db.session import get_db
from app.schemas.doctor import DoctorCreate, DoctorUpdate, DoctorResponse, DoctorListResponse
from app.schemas.response import PageResponse
from app.services.doctor_service import DoctorService
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.core.config import settings

router = APIRouter()


# ========== 医生登录相关 ==========
class DoctorLoginRequest(BaseModel):
    phone: str
    password: str


class DoctorLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    doctor: DoctorResponse


@router.post("/login", response_model=DoctorLoginResponse)
async def doctor_login(
    data: DoctorLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """医生登录"""
    service = DoctorService(db)
    doctor = await service.authenticate(data.phone, data.password)
    
    if not doctor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="手机号或密码错误")
    
    if doctor.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    
    # 更新登录信息
    client_ip = request.client.host if request.client else ""
    await service.update_login_info(doctor.id, client_ip)
    
    # 生成Token
    access_token = create_access_token(data={"sub": doctor.id, "type": "doctor"})
    refresh_token = create_refresh_token(data={"sub": doctor.id, "type": "doctor"})
    
    return DoctorLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        doctor=DoctorResponse(
            id=doctor.id,
            user_id=doctor.user_id,
            name=doctor.name,
            phone=doctor.phone,
            avatar=doctor.avatar,
            title=doctor.title,
            department_id=doctor.department_id,
            department_name=doctor.department.name if doctor.department else None,
            specialty=doctor.specialty,
            introduction=doctor.introduction,
            registration_fee=doctor.registration_fee,
            is_recommended=doctor.is_recommended,
            sort_order=doctor.sort_order,
            status=doctor.status,
            created_at=doctor.created_at,
            updated_at=doctor.updated_at
        ),
    )


@router.get("/me", response_model=DoctorResponse)
async def get_current_doctor_info(
    db: AsyncSession = Depends(get_db),
    # TODO: 添加医生认证依赖
):
    """获取当前登录医生信息"""
    # 需要从 token 中获取医生 ID
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="待实现")

@router.get("", response_model=PageResponse[DoctorListResponse])
async def get_doctors(
    name: Optional[str] = None,
    department_id: Optional[str] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取医生列表"""
    service = DoctorService(db)
    doctors, total = await service.get_list(
        name=name, department_id=department_id, status=status, page=page, page_size=page_size
    )
    
    result = []
    for d in doctors:
        result.append(DoctorListResponse(
            id=d.id,
            name=d.name,
            avatar=d.avatar,
            title=d.title,
            department_id=d.department_id,
            department_name=d.department.name if d.department else None,
            specialty=d.specialty,
            registration_fee=d.registration_fee,
            is_recommended=d.is_recommended
        ))
    
    return PageResponse(data=result, total=total, page=page, page_size=page_size)

@router.get("/recommended", response_model=List[DoctorListResponse])
async def get_recommended_doctors(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """获取推荐医生"""
    service = DoctorService(db)
    doctors = await service.get_recommended(limit=limit)
    
    return [DoctorListResponse(
        id=d.id,
        name=d.name,
        avatar=d.avatar,
        title=d.title,
        department_id=d.department_id,
        department_name=d.department.name if d.department else None,
        specialty=d.specialty,
        registration_fee=d.registration_fee,
        is_recommended=d.is_recommended
    ) for d in doctors]

@router.get("/by-department/{department_id}", response_model=List[DoctorListResponse])
async def get_doctors_by_department(
    department_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取科室下的医生"""
    service = DoctorService(db)
    doctors = await service.get_by_department(department_id)
    
    return [DoctorListResponse(
        id=d.id,
        name=d.name,
        avatar=d.avatar,
        title=d.title,
        department_id=d.department_id,
        department_name=d.department.name if d.department else None,
        specialty=d.specialty,
        registration_fee=d.registration_fee,
        is_recommended=d.is_recommended
    ) for d in doctors]

@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(doctor_id: str, db: AsyncSession = Depends(get_db)):
    """获取医生详情"""
    service = DoctorService(db)
    doctor = await service.get_by_id(doctor_id)
    
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在")
    
    return DoctorResponse(
        id=doctor.id,
        user_id=doctor.user_id,
        department_id=doctor.department_id,
        department_name=doctor.department.name if doctor.department else None,
        name=doctor.name,
        phone=doctor.phone,
        avatar=doctor.avatar,
        title=doctor.title,
        specialty=doctor.specialty,
        introduction=doctor.introduction,
        registration_fee=doctor.registration_fee,
        is_recommended=doctor.is_recommended,
        sort_order=doctor.sort_order,
        status=doctor.status,
        created_at=doctor.created_at,
        updated_at=doctor.updated_at
    )

@router.post("", response_model=DoctorResponse)
async def create_doctor(data: DoctorCreate, db: AsyncSession = Depends(get_db)):
    """创建医生"""
    service = DoctorService(db)
    doctor = await service.create(data)
    
    return DoctorResponse(
        id=doctor.id,
        user_id=doctor.user_id,
        department_id=doctor.department_id,
        name=doctor.name,
        phone=doctor.phone,
        avatar=doctor.avatar,
        title=doctor.title,
        specialty=doctor.specialty,
        introduction=doctor.introduction,
        registration_fee=doctor.registration_fee,
        is_recommended=doctor.is_recommended,
        sort_order=doctor.sort_order,
        status=doctor.status,
        created_at=doctor.created_at,
        updated_at=doctor.updated_at
    )

@router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(
    doctor_id: str,
    data: DoctorUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新医生"""
    service = DoctorService(db)
    doctor = await service.update(doctor_id, data)
    
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在")
    
    return DoctorResponse(
        id=doctor.id,
        user_id=doctor.user_id,
        department_id=doctor.department_id,
        department_name=doctor.department.name if doctor.department else None,
        name=doctor.name,
        phone=doctor.phone,
        avatar=doctor.avatar,
        title=doctor.title,
        specialty=doctor.specialty,
        introduction=doctor.introduction,
        registration_fee=doctor.registration_fee,
        is_recommended=doctor.is_recommended,
        sort_order=doctor.sort_order,
        status=doctor.status,
        created_at=doctor.created_at,
        updated_at=doctor.updated_at
    )

@router.delete("/{doctor_id}")
async def delete_doctor(doctor_id: str, db: AsyncSession = Depends(get_db)):
    """删除医生"""
    service = DoctorService(db)
    success = await service.delete(doctor_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在")
    
    return {"message": "删除成功"}
