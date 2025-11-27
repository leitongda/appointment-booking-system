from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def get_doctors():
    """获取医生列表"""
    return {"data": [], "total": 0}

@router.get("/recommended")
async def get_recommended_doctors():
    """获取推荐医生"""
    return []

@router.get("/{id}")
async def get_doctor(id: str):
    """获取医生详情"""
    return {"id": id, "name": "张医生"}

@router.get("/{id}/schedules")
async def get_doctor_schedules(id: str):
    """获取医生排班"""
    return []

@router.post("")
async def create_doctor():
    """创建医生"""
    return {"message": "创建成功"}

@router.put("/{id}")
async def update_doctor(id: str):
    """更新医生"""
    return {"message": "更新成功"}

