from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def get_schedules():
    """获取排班列表"""
    return {"data": [], "total": 0}

@router.get("/available")
async def get_available_schedules(doctor_id: str):
    """获取可预约排班"""
    return []

@router.post("")
async def create_schedule():
    """创建排班"""
    return {"message": "创建成功"}

@router.post("/batch")
async def batch_create_schedules():
    """批量创建排班"""
    return {"message": "创建成功"}

@router.put("/{id}")
async def update_schedule(id: str):
    """更新排班"""
    return {"message": "更新成功"}

@router.put("/{id}/suspend")
async def suspend_schedule(id: str):
    """停诊"""
    return {"message": "停诊成功"}

