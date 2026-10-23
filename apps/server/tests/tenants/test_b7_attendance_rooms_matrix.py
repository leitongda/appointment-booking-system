"""B7：考勤与诊室租户锚点矩阵（R1-11 / R1-13）

覆盖计划 B7 验收门：
1. attendance rules/shifts/groups：列表双向断言、跨租户详情 404、
   平台管理员无锚点创建 400、正控创建落库 tenant_id=A；
2. attendance records：管理员列表双向断言、每日统计不混入他租户打卡；
   打卡记录无单条详情接口，跨租户“访问”以列表/统计不可见作为 404 语义等价断言；
3. attendance leave：申请列表双向断言、跨租户审批 404 且 DB 未变、
   假期类型列表隔离、类型创建无锚点 400；
4. schedule-rooms：列表双向断言、跨租户详情/更新 404 且 DB 未变、
   无锚点创建 400、正控创建落库 tenant_id=A；
5. doctor-booking-settings：列表双向断言、跨租户详情/更新 404 且 DB 未变、
   无锚点创建 400、正控创建落库 tenant_id=A。
"""
import uuid
from datetime import date, datetime, timedelta

import pytest
import pytest_asyncio

from app.models.account import Account
from app.models.attendance import (
    AttendanceGroup,
    AttendanceLeaveRequest,
    AttendanceLeaveType,
    AttendanceRecord,
    AttendanceRule,
    AttendanceShift,
)
from app.models.doctor_booking_setting import DoctorBookingSetting
from app.models.schedule_room import ScheduleRoom

pytestmark = [pytest.mark.security, pytest.mark.multi_tenant]

RULES = "/api/v1/attendance/rules"
SHIFTS = "/api/v1/attendance/shifts"
GROUPS = "/api/v1/attendance/groups"
RECORDS = "/api/v1/attendance/records"
LEAVE = "/api/v1/attendance/leave"
ROOMS = "/api/v1/schedule-rooms"
BOOKING = "/api/v1/doctor-booking-settings"


def _auth(token: str, tenant_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    return headers


def _items(payload) -> list:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data") or data.get("items") or []
    return payload.get("items") or []


def _obj(payload) -> dict:
    """解包统一响应外壳 {code,message,data}"""
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else {}


def _ids(payload) -> set[str]:
    return {item.get("id") for item in _items(payload) if isinstance(item, dict)}


async def _add_account(db_session, tenant_id: str, label: str) -> Account:
    row = Account(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        phone=f"137{uuid.uuid4().int % 10**8:08d}",
        username=f"b7_{label}_{uuid.uuid4().hex[:8]}",
        password_hash="$2b$12$test_hash_not_for_production",
        nickname=f"B7账号{label}",
        name=f"B7账号{label}",
        gender=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_rule(db_session, tenant_id: str, name: str) -> AttendanceRule:
    row = AttendanceRule(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        late_policy="flexible",
        early_policy="flexible",
        absent_policy="strict",
        overtime_enabled=False,
        overtime_min_minutes=30,
        enabled=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_shift(db_session, tenant_id: str, name: str, code: str) -> AttendanceShift:
    row = AttendanceShift(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        code=code,
        start_time="09:00",
        end_time="18:00",
        grace_minutes=5,
        late_threshold_minutes=0,
        early_threshold_minutes=0,
        is_flexible=False,
        enabled=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_group(db_session, tenant_id: str, name: str) -> AttendanceGroup:
    row = AttendanceGroup(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        check_method="gps",
        location_radius=300,
        require_device_bind=False,
        enabled=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_record(
    db_session, tenant_id: str, account_id: str, check_date: date
) -> AttendanceRecord:
    row = AttendanceRecord(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        account_id=account_id,
        check_date=check_date,
        check_in_time=datetime.combine(check_date, datetime.min.time()),
        status="normal",
        late_minutes=0,
        early_minutes=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_leave_type(db_session, tenant_id: str, name: str, code: str) -> AttendanceLeaveType:
    row = AttendanceLeaveType(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=name,
        code=code,
        paid=True,
        default_days=5,
        enabled=True,
        sort_order=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_leave_request(
    db_session, tenant_id: str, account_id: str, leave_type_id: str, reason: str
) -> AttendanceLeaveRequest:
    row = AttendanceLeaveRequest(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        account_id=account_id,
        leave_type_id=leave_type_id,
        start_date=date.today() + timedelta(days=10),
        end_date=date.today() + timedelta(days=11),
        duration_days=2,
        reason=reason,
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_room(db_session, tenant_id: str, store_id: str, name: str) -> ScheduleRoom:
    row = ScheduleRoom(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        store_id=store_id,
        name=name,
        room_number="101",
        capacity=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def _add_booking_setting(
    db_session, tenant_id: str, store_id: str, doctor_id: str
) -> DoctorBookingSetting:
    row = DoctorBookingSetting(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        store_id=store_id,
        doctor_id=doctor_id,
        booking_start_offset=0,
        booking_range_days=14,
        release_time="08:00",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


@pytest_asyncio.fixture
async def b7_env(db_session, factory, multi_tenant_env):
    """A/B 两租户各一套考勤与诊室数据"""
    env = multi_tenant_env

    env.doctor_a = await factory.create_doctor(env.tenant_a.id, env.store_a.id, name="B7医生A")
    env.doctor_b = await factory.create_doctor(env.tenant_b.id, env.store_b.id, name="B7医生B")
    env.account_a = await _add_account(db_session, env.tenant_a.id, "A")
    env.account_b = await _add_account(db_session, env.tenant_b.id, "B")

    env.rule_a = await _add_rule(db_session, env.tenant_a.id, "A考勤规则")
    env.rule_b = await _add_rule(db_session, env.tenant_b.id, "B考勤规则")
    env.shift_a = await _add_shift(db_session, env.tenant_a.id, "A班次", "A_SHIFT")
    env.shift_b = await _add_shift(db_session, env.tenant_b.id, "B班次", "B_SHIFT")
    env.group_a = await _add_group(db_session, env.tenant_a.id, "A签到组")
    env.group_b = await _add_group(db_session, env.tenant_b.id, "B签到组")
    env.record_day = date.today()
    env.record_a = await _add_record(
        db_session, env.tenant_a.id, env.account_a.id, env.record_day
    )
    env.record_b = await _add_record(
        db_session, env.tenant_b.id, env.account_b.id, env.record_day
    )
    env.leave_type_a = await _add_leave_type(db_session, env.tenant_a.id, "A年假", "A_ANNUAL")
    env.leave_type_b = await _add_leave_type(db_session, env.tenant_b.id, "B年假", "B_ANNUAL")
    env.leave_a = await _add_leave_request(
        db_session, env.tenant_a.id, env.account_a.id, env.leave_type_a.id, "A请假"
    )
    env.leave_b = await _add_leave_request(
        db_session, env.tenant_b.id, env.account_b.id, env.leave_type_b.id, "B请假"
    )
    env.room_a = await _add_room(db_session, env.tenant_a.id, env.store_a.id, "A诊室")
    env.room_b = await _add_room(db_session, env.tenant_b.id, env.store_b.id, "B诊室")
    env.booking_a = await _add_booking_setting(
        db_session, env.tenant_a.id, env.store_a.id, env.doctor_a.id
    )
    env.booking_b = await _add_booking_setting(
        db_session, env.tenant_b.id, env.store_b.id, env.doctor_b.id
    )
    return env


class TestAttendanceRulesAnchor:
    async def test_list_only_own_tenant(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            RULES, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.rule_a.id in ids
        assert env.rule_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            f"{RULES}/{env.rule_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_create_without_anchor_400(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.post(
            RULES,
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={"name": "无锚点规则"},
        )
        assert response.status_code == 400, response.text

    async def test_create_writes_tenant_anchor(self, async_client, db_session, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.post(
            RULES,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"name": f"锚点规则{uuid.uuid4().hex[:6]}"},
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(AttendanceRule, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id


class TestAttendanceShiftsAnchor:
    async def test_list_only_own_tenant(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            SHIFTS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.shift_a.id in ids
        assert env.shift_b.id not in ids

    async def test_all_only_own_tenant(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            f"{SHIFTS}/all",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.shift_a.id in ids
        assert env.shift_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            f"{SHIFTS}/{env.shift_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_create_without_anchor_400(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.post(
            SHIFTS,
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={
                "name": "无锚点班次",
                "code": f"NO_ANCHOR_{uuid.uuid4().hex[:6]}",
                "start_time": "09:00",
                "end_time": "18:00",
            },
        )
        assert response.status_code == 400, response.text

    async def test_create_writes_tenant_anchor(self, async_client, db_session, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.post(
            SHIFTS,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={
                "name": "锚点班次",
                "code": f"ANCHOR_{uuid.uuid4().hex[:6]}",
                "start_time": "08:00",
                "end_time": "17:00",
            },
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(AttendanceShift, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id


class TestAttendanceGroupsAnchor:
    async def test_list_only_own_tenant(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            GROUPS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.group_a.id in ids
        assert env.group_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            f"{GROUPS}/{env.group_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_cross_tenant_members_404(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            f"{GROUPS}/{env.group_b.id}/members",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_create_without_anchor_400(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.post(
            GROUPS,
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={"name": "无锚点签到组"},
        )
        assert response.status_code == 400, response.text

    async def test_create_writes_tenant_anchor(self, async_client, db_session, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.post(
            GROUPS,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"name": f"锚点签到组{uuid.uuid4().hex[:6]}"},
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(AttendanceGroup, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id


class TestAttendanceRecordsAnchor:
    async def test_admin_list_only_own_tenant(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            RECORDS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.record_a.id in ids
        # 打卡记录无单条详情接口，跨租户“不可访问”以列表不可见断言
        assert env.record_b.id not in ids

    async def test_daily_stats_scoped_to_tenant(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            f"{RECORDS}/daily-stats/{env.record_day.isoformat()}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        body = _obj(response.json())
        # A 租户当天仅 1 条打卡，B 租户同日记录不得计入
        assert body["total"] == 1, body
        assert body["normal"] == 1, body

    async def test_b_record_not_visible_in_export_range(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            f"{RECORDS}/export",
            params={
                "start_date": env.record_day.isoformat(),
                "end_date": env.record_day.isoformat(),
            },
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        from io import BytesIO

        from openpyxl import load_workbook

        sheet = load_workbook(BytesIO(response.content)).active
        # 1 行表头 + A 租户 1 条打卡；B 租户同日记录不得出现在 A 的导出
        assert sheet.max_row == 2, [c.value for c in sheet["A"]]


class TestAttendanceLeaveAnchor:
    async def test_type_list_only_own_tenant(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            f"{LEAVE}/types",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.leave_type_a.id in ids
        assert env.leave_type_b.id not in ids

    async def test_admin_requests_only_own_tenant(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            f"{LEAVE}/requests",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.leave_a.id in ids
        assert env.leave_b.id not in ids

    async def test_cross_tenant_approve_404_and_unchanged(
        self, async_client, db_session, b7_env, admin_token_factory
    ):
        env = b7_env
        response = await async_client.post(
            f"{LEAVE}/requests/{env.leave_b.id}/approve",
            json={"comment": "越权审批"},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(AttendanceLeaveRequest, env.leave_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.status == "pending"

    async def test_cross_tenant_reject_404_and_unchanged(
        self, async_client, db_session, b7_env, admin_token_factory
    ):
        env = b7_env
        response = await async_client.post(
            f"{LEAVE}/requests/{env.leave_b.id}/reject",
            json={"comment": "越权驳回"},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(AttendanceLeaveRequest, env.leave_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.status == "pending"

    async def test_create_type_without_anchor_400(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.post(
            f"{LEAVE}/types",
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={"name": "无锚点假期", "code": "NO_ANCHOR_LEAVE"},
        )
        assert response.status_code == 400, response.text

    async def test_create_type_writes_tenant_anchor(
        self, async_client, db_session, b7_env, admin_token_factory
    ):
        env = b7_env
        response = await async_client.post(
            f"{LEAVE}/types",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"name": "锚点假期", "code": f"ANCHOR_{uuid.uuid4().hex[:6]}"},
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(AttendanceLeaveType, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id


class TestScheduleRoomsAnchor:
    async def test_list_only_own_tenant(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            ROOMS, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.room_a.id in ids
        assert env.room_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            f"{ROOMS}/{env.room_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_cross_tenant_update_404_and_unchanged(
        self, async_client, db_session, b7_env, admin_token_factory
    ):
        env = b7_env
        response = await async_client.put(
            f"{ROOMS}/{env.room_b.id}",
            json={"name": "越权改名"},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(ScheduleRoom, env.room_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.name == "B诊室"

    async def test_create_without_anchor_400(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.post(
            ROOMS,
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={"name": "无锚点诊室", "storeId": env.store_b.id},
        )
        assert response.status_code == 400, response.text

    async def test_create_writes_tenant_anchor(self, async_client, db_session, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.post(
            ROOMS,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"name": f"锚点诊室{uuid.uuid4().hex[:6]}", "storeId": env.store_a.id},
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(ScheduleRoom, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id

    async def test_platform_admin_scoped_by_header(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            ROOMS, headers=_auth(admin_token_factory(env.platform_admin), env.tenant_b.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.room_b.id in ids
        assert env.room_a.id not in ids


class TestDoctorBookingSettingsAnchor:
    async def test_list_only_own_tenant(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            BOOKING, headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.booking_a.id in ids
        assert env.booking_b.id not in ids

    async def test_cross_tenant_detail_404(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            f"{BOOKING}/{env.booking_b.id}",
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

    async def test_cross_tenant_update_404_and_unchanged(
        self, async_client, db_session, b7_env, admin_token_factory
    ):
        env = b7_env
        response = await async_client.put(
            f"{BOOKING}/{env.booking_b.id}",
            json={"bookingRangeDays": 30},
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
        )
        assert response.status_code == 404, response.text

        refreshed = await db_session.get(DoctorBookingSetting, env.booking_b.id)
        await db_session.refresh(refreshed)
        assert refreshed.booking_range_days == 14

    async def test_create_without_anchor_400(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.post(
            BOOKING,
            headers=_auth(admin_token_factory(env.platform_admin)),
            json={"storeId": env.store_b.id, "doctorId": env.doctor_b.id},
        )
        assert response.status_code == 400, response.text

    async def test_create_writes_tenant_anchor(self, async_client, db_session, b7_env, admin_token_factory):
        env = b7_env
        # 每个门店-医生唯一：为 A 再建一位医生，避免与既有设置冲突
        doctor_a2 = await b7_env_doctor(env, db_session)
        response = await async_client.post(
            BOOKING,
            headers=_auth(admin_token_factory(env.admin_a), env.tenant_a.id),
            json={"storeId": env.store_a.id, "doctorId": doctor_a2.id},
        )
        assert response.status_code in (200, 201), response.text
        created = await db_session.get(DoctorBookingSetting, _obj(response.json())["id"])
        assert created is not None
        assert created.tenant_id == env.tenant_a.id

    async def test_platform_admin_scoped_by_header(self, async_client, b7_env, admin_token_factory):
        env = b7_env
        response = await async_client.get(
            BOOKING, headers=_auth(admin_token_factory(env.platform_admin), env.tenant_b.id)
        )
        assert response.status_code == 200, response.text
        ids = _ids(response.json())
        assert env.booking_b.id in ids
        assert env.booking_a.id not in ids


async def b7_env_doctor(env, db_session):
    from app.models.department import Department
    from app.models.doctor import Doctor

    dept = Department(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_a.id,
        store_id=env.store_a.id,
        name=f"B7科室{uuid.uuid4().hex[:6]}",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)
    doctor = Doctor(
        id=str(uuid.uuid4()),
        tenant_id=env.tenant_a.id,
        store_id=env.store_a.id,
        department_id=dept.id,
        name=f"B7医生A2{uuid.uuid4().hex[:6]}",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor

