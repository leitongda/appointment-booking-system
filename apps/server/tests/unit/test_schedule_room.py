"""ScheduleRoom 服务单元测试"""
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule_room import ScheduleRoom
from app.models.schedule import Schedule
from app.models.tenant import Tenant
from app.models.store import Store
from app.models.department import Department
from app.models.doctor import Doctor
from app.modules.schedule_rooms.service import ScheduleRoomService


# ==================== Fixtures ====================

class FakeRoomCreate:
    """模拟 ScheduleRoomCreate 请求体"""
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', '测试诊室')
        self.store_id = kwargs.get('store_id')
        self.room_number = kwargs.get('room_number', '101')
        self.floor = kwargs.get('floor', '1楼')
        self.department_id = kwargs.get('department_id')
        self.capacity = kwargs.get('capacity', 1)
        self.status = kwargs.get('status', 1)
        self.remark = kwargs.get('remark')


class FakeRoomUpdate:
    """模拟 ScheduleRoomUpdate 请求体"""
    def __init__(self, **kwargs):
        self._data = kwargs

    def model_dump(self, exclude_unset=True):
        return self._data


@pytest_asyncio.fixture
async def test_room(db_session: AsyncSession, test_tenant: Tenant, test_store: Store, test_department: Department) -> ScheduleRoom:
    """创建测试诊室"""
    room = ScheduleRoom(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        store_id=test_store.id,
        name="测试诊室A",
        room_number="101",
        floor="1楼",
        department_id=test_department.id,
        capacity=2,
        status=1,
        remark="测试备注",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)
    return room


@pytest_asyncio.fixture
def room_service(db_session: AsyncSession) -> ScheduleRoomService:
    return ScheduleRoomService(db_session)


# ==================== 测试用例 ====================

@pytest.mark.asyncio
async def test_create_room_success(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    room_service: ScheduleRoomService,
):
    """测试创建诊室成功"""
    with patch('app.modules.schedule_rooms.service.get_current_tenant_id', return_value=test_tenant.id):
        data = FakeRoomCreate(name="新诊室", store_id=test_store.id)
        room = await room_service.create(data)

        assert room.id is not None
        assert room.name == "新诊室"
        assert room.store_id == test_store.id
        assert room.tenant_id == test_tenant.id
        assert room.capacity == 1
        assert room.status == 1


@pytest.mark.asyncio
async def test_create_room_duplicate_name_raises_error(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_room: ScheduleRoom,
    room_service: ScheduleRoomService,
):
    """测试创建同名诊室触发唯一约束"""
    with patch('app.modules.schedule_rooms.service.get_current_tenant_id', return_value=test_tenant.id):
        data = FakeRoomCreate(name=test_room.name, store_id=test_store.id)
        with pytest.raises(Exception):
            await room_service.create(data)


@pytest.mark.asyncio
async def test_get_list_with_pagination(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_room: ScheduleRoom,
    room_service: ScheduleRoomService,
):
    """测试分页列表"""
    # 再创建一个诊室
    room2 = ScheduleRoom(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        store_id=test_store.id,
        name="测试诊室B",
        capacity=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(room2)
    await db_session.commit()

    with patch('app.modules.schedule_rooms.service.get_current_tenant_id', return_value=test_tenant.id):
        rooms, total = await room_service.get_list(page=1, page_size=10)
        assert total == 2
        assert len(rooms) == 2

        # 分页测试
        rooms_page1, total1 = await room_service.get_list(page=1, page_size=1)
        assert total1 == 2
        assert len(rooms_page1) == 1


@pytest.mark.asyncio
async def test_get_list_filters_by_store(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_room: ScheduleRoom,
    room_service: ScheduleRoomService,
):
    """测试按门店过滤"""
    other_store_id = str(uuid4())

    with patch('app.modules.schedule_rooms.service.get_current_tenant_id', return_value=test_tenant.id):
        rooms, total = await room_service.get_list(store_id=test_store.id)
        assert total >= 1
        for room in rooms:
            assert room.store_id == test_store.id

        rooms, total = await room_service.get_list(store_id=other_store_id)
        assert total == 0


@pytest.mark.asyncio
async def test_get_list_tenant_isolation(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_room: ScheduleRoom,
    room_service: ScheduleRoomService,
):
    """测试租户隔离"""
    other_tenant_id = str(uuid4())

    # 用其他租户上下文查询，应返回空
    with patch('app.modules.schedule_rooms.service.get_current_tenant_id', return_value=other_tenant_id):
        rooms, total = await room_service.get_list()
        assert total == 0

    # 用正确租户上下文查询
    with patch('app.modules.schedule_rooms.service.get_current_tenant_id', return_value=test_tenant.id):
        rooms, total = await room_service.get_list()
        assert total >= 1


@pytest.mark.asyncio
async def test_update_room_success(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_room: ScheduleRoom,
    room_service: ScheduleRoomService,
):
    """测试更新诊室成功"""
    with patch('app.modules.schedule_rooms.service.get_current_tenant_id', return_value=test_tenant.id):
        data = FakeRoomUpdate(name="更新后的诊室", capacity=5)
        updated = await room_service.update(test_room.id, data)

        assert updated is not None
        assert updated.name == "更新后的诊室"
        assert updated.capacity == 5


@pytest.mark.asyncio
async def test_delete_room_success(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_department: Department,
    room_service: ScheduleRoomService,
):
    """测试删除诊室成功（无关联排班）"""
    # 创建一个无关联排班的诊室
    room = ScheduleRoom(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        store_id=test_store.id,
        name="待删除诊室",
        capacity=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(room)
    await db_session.commit()

    with patch('app.modules.schedule_rooms.service.get_current_tenant_id', return_value=test_tenant.id):
        success = await room_service.delete(room.id)
        assert success is True

        # 确认已删除
        deleted = await room_service.get_by_id(room.id)
        assert deleted is None


@pytest.mark.asyncio
async def test_delete_room_with_schedules_blocked(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_department: Department,
    test_doctor: Doctor,
    room_service: ScheduleRoomService,
):
    """测试删除有排班关联的诊室被阻止"""
    from datetime import date, time as dt_time

    # 创建诊室
    room = ScheduleRoom(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        store_id=test_store.id,
        name="有排班诊室",
        capacity=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(room)
    await db_session.flush()

    # 给诊室关联排班
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        store_id=test_store.id,
        tenant_id=test_tenant.id,
        room_id=room.id,
        schedule_date=date.today(),
        time_slot="morning",
        start_time=dt_time(8, 0),
        end_time=dt_time(12, 0),
        total_slots=10,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule)
    await db_session.commit()

    with patch('app.modules.schedule_rooms.service.get_current_tenant_id', return_value=test_tenant.id):
        with pytest.raises(ValueError, match="存在排班记录"):
            await room_service.delete(room.id)
