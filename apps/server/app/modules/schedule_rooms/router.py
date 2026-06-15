
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_store_access, get_current_admin, get_store_filter, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.schedule_rooms.service import ScheduleRoomService
from app.schemas.response import PageResponse, to_camel

router = APIRouter()

# ==================== Pydantic Schemas ====================

class ScheduleRoomBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str = Field(..., max_length=100, description="诊室名称")
    store_id: str = Field(..., description="门店ID")
    room_number: str | None = Field(None, max_length=50, description="房间号")
    floor: str | None = Field(None, max_length=20, description="楼层")
    department_id: str | None = Field(None, description="所属科室")
    capacity: int = Field(1, ge=1, description="容量")
    status: int = Field(1, ge=0, le=1, description="状态: 0禁用 1启用")
    remark: str | None = Field(None, max_length=500, description="备注")

class ScheduleRoomCreate(ScheduleRoomBase):
    pass

class ScheduleRoomUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str | None = Field(None, max_length=100, description="诊室名称")
    store_id: str | None = Field(None, description="门店ID")
    room_number: str | None = Field(None, max_length=50, description="房间号")
    floor: str | None = Field(None, max_length=20, description="楼层")
    department_id: str | None = Field(None, description="所属科室")
    capacity: int | None = Field(None, ge=1, description="容量")
    status: int | None = Field(None, ge=0, le=1, description="状态: 0禁用 1启用")
    remark: str | None = Field(None, max_length=500, description="备注")

class ScheduleRoomResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        by_alias=True,
    )

    id: str
    name: str
    store_id: str
    store_name: str | None = Field(None, description="门店名称")
    room_number: str | None = None
    floor: str | None = None
    department_id: str | None = None
    department_name: str | None = Field(None, description="科室名称")
    capacity: int = 1
    status: int = 1
    remark: str | None = None
    created_at: object = None
    updated_at: object = None

def _to_response(room) -> ScheduleRoomResponse:
    data = ScheduleRoomResponse.model_validate(room)
    if room.store:
        data.store_name = room.store.name
    if room.department:
        data.department_name = room.department.name
    return data

# ==================== Routes ====================

@router.get("", response_model=PageResponse[ScheduleRoomResponse], summary="获取诊室列表")
async def get_schedule_rooms(
    name: str | None = None,
    status: int | None = None,
    store_id: str | None = None,
    department_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    service = ScheduleRoomService(db)

    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter

    rooms, total = await service.get_list(
        name=name, status=status, store_id=store_id,
        department_id=department_id, page=page, page_size=page_size,
    )

    return PageResponse(
        data=[_to_response(r) for r in rooms],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.get("/{room_id}", response_model=ScheduleRoomResponse, summary="获取诊室详情")
async def get_schedule_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    service = ScheduleRoomService(db)
    room = await service.get_by_id(room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊室不存在，请检查后重试")

    if not check_store_access(current_admin, room.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此诊室")

    return _to_response(room)

@router.post("", response_model=ScheduleRoomResponse, summary="创建诊室")
async def create_schedule_room(
    data: ScheduleRoomCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:room")),
):
    store_filter = get_store_filter(current_admin)
    if store_filter:
        if data.store_id and data.store_id != store_filter:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能在本门店创建诊室")
        data.store_id = store_filter

    service = ScheduleRoomService(db)
    try:
        room = await service.create(data)
    except Exception as e:
        # 唯一约束冲突
        if "unique" in str(e).lower() or "uix" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="同门店下已存在同名诊室")
        raise
    return _to_response(room)

@router.put("/{room_id}", response_model=ScheduleRoomResponse, summary="更新诊室")
async def update_schedule_room(
    room_id: str,
    data: ScheduleRoomUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:room")),
):
    service = ScheduleRoomService(db)
    room = await service.get_by_id(room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊室不存在，请检查后重试")

    if not check_store_access(current_admin, room.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权修改此诊室")

    store_filter = get_store_filter(current_admin)
    if store_filter and data.store_id and data.store_id != store_filter:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权修改诊室的门店归属")

    try:
        room = await service.update(room_id, data)
    except Exception as e:
        if "unique" in str(e).lower() or "uix" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="同门店下已存在同名诊室")
        raise
    return _to_response(room)

@router.delete("/{room_id}", summary="删除诊室")
async def delete_schedule_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:room")),
):
    service = ScheduleRoomService(db)
    room = await service.get_by_id(room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊室不存在，请检查后重试")

    if not check_store_access(current_admin, room.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权删除此诊室")

    try:
        success = await service.delete(room_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊室不存在，请检查后重试")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"message": "删除成功"}
