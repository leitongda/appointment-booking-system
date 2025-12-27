from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.user import UserResponse, UserUpdate, PatientCreate, PatientUpdate, PatientResponse
from app.services.user_service import UserService, PatientService

router = APIRouter()

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户信息"""
    user_service = UserService(db)
    user = await user_service.get_by_id(current_user["id"])
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
    
    return UserResponse(
        id=user.id,
        phone=user.phone,
        nickname=user.nickname,
        avatar=user.avatar,
        gender=user.gender,
        status=user.status
    )

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新用户信息"""
    user_service = UserService(db)
    user = await user_service.update(current_user["id"], data)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
    
    return UserResponse(
        id=user.id,
        phone=user.phone,
        nickname=user.nickname,
        avatar=user.avatar,
        gender=user.gender,
        status=user.status
    )

# ========== 就诊人管理 ==========
@router.get("/patients", response_model=List[PatientResponse])
async def get_patients(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取就诊人列表"""
    patient_service = PatientService(db)
    patients = await patient_service.get_by_user_id(current_user["id"])
    return [PatientResponse.model_validate(p) for p in patients]

@router.post("/patients", response_model=PatientResponse)
async def add_patient(
    data: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """添加就诊人"""
    patient_service = PatientService(db)
    patient = await patient_service.create(current_user["id"], data)
    return PatientResponse.model_validate(patient)

@router.put("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新就诊人"""
    patient_service = PatientService(db)
    patient = await patient_service.update(patient_id, current_user["id"], data)
    
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="就诊人不存在，请检查后重试")
    
    return PatientResponse.model_validate(patient)

@router.delete("/patients/{patient_id}")
async def delete_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除就诊人"""
    patient_service = PatientService(db)
    success = await patient_service.delete(patient_id, current_user["id"])
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="就诊人不存在，请检查后重试")
    
    return {"message": "删除成功"}
