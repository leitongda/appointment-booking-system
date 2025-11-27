from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class CreateAppointmentRequest(BaseModel):
    doctor_id: str
    schedule_id: str
    patient_id: str

@router.get("")
async def get_appointments():
    """获取预约列表"""
    return {"data": [], "total": 0}

@router.get("/today")
async def get_today_appointments():
    """获取今日预约"""
    return []

@router.get("/statistics")
async def get_appointment_statistics():
    """获取预约统计"""
    return {"total": 0, "pending": 0, "confirmed": 0, "completed": 0, "cancelled": 0}

@router.get("/{id}")
async def get_appointment(id: str):
    """获取预约详情"""
    return {"id": id}

@router.post("")
async def create_appointment(data: CreateAppointmentRequest):
    """创建预约"""
    return {"message": "预约成功", "appointment_no": "YY20241127001"}

@router.put("/{id}/cancel")
async def cancel_appointment(id: str):
    """取消预约"""
    return {"message": "取消成功"}

@router.put("/{id}/sign-in")
async def sign_in_appointment(id: str):
    """签到"""
    return {"message": "签到成功"}

@router.put("/{id}/call")
async def call_appointment(id: str):
    """叫号"""
    return {"message": "已呼叫"}

@router.put("/{id}/complete")
async def complete_appointment(id: str):
    """完成就诊"""
    return {"message": "就诊完成"}

