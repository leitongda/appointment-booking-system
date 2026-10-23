"""预约医助确认到店状态流单元测试（内存 SQLite）

覆盖 PATCH /api/v1/appointments/{id}/assistant-confirm 与患者端响应字段：
- 新预约默认 assistant_confirm_status=1（患者下单 service 路径 + ORM 默认）
- 管理端 PATCH 2→3 流转成功且落库，note 仅回显不落库
- 非法 status（如 5）返回 422
- 患者端详情响应包含 assistantConfirmStatus（camelCase）
- 列表接口支持 assistant_confirm_status 查询参数过滤
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.tenant import Tenant
from app.modules.appointments.service import AppointmentService
from app.schemas.appointment import AppointmentCreate


async def _create_appointment(
    db_session: AsyncSession,
    tenant: Tenant,
    user,
    patient,
    doctor,
    schedule,
    assistant_confirm_status: int = 1,
) -> Appointment:
    """创建一条最小可用的预约记录，可指定医助确认状态"""
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:14].upper()}",
        user_id=user.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=1,
        assistant_confirm_status=assistant_confirm_status,
        patient_name=patient.name,
        patient_phone=patient.phone,
        doctor_name=doctor.name,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user.id,
    )
    db_session.add(appointment)
    await db_session.commit()
    return appointment


class TestBookingDefaultAssistantConfirmStatus:
    """新预约默认医助确认状态"""

    @pytest.mark.asyncio
    async def test_create_appointment_defaults_to_pending_contact(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
        test_tenant,
    ):
        """患者下单 service 路径创建预约后 assistant_confirm_status=1（待联系）"""
        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id,
            symptom_description="头痛三天",
        )
        service = AppointmentService(db_session)

        with patch('app.modules.appointments.service.RedisCache.tenant_distributed_lock') as mock_lock, \
             patch('app.modules.appointments.service.RuleEngineService') as mock_rule_engine_cls, \
             patch('app.modules.appointments.service.MessageService') as mock_msg_service_cls, \
             patch('app.modules.appointments.service.dispatch_event_email') as mock_dispatch, \
             patch('app.middleware.tenant_context.get_current_tenant_id', return_value=test_tenant.id), \
             patch('app.common.quota.check_quota', new_callable=AsyncMock):

            # 分布式锁 mock
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value="mock_lock_value")
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_context

            # 规则引擎 mock（时间窗全部放行、无规则组）
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            window = {
                'allowed': True,
                'open_at': datetime.now(),
                'close_at': datetime.now(),
                'fail_policy': 'REJECT',
                'message': '',
            }
            mock_rule_engine.check_action_window = AsyncMock(return_value=window)
            mock_rule_engine.get_applicable_rule_set = AsyncMock(return_value=None)

            # 消息服务 mock（避免实际发送）
            mock_msg_service = MagicMock()
            mock_msg_service_cls.return_value = mock_msg_service
            mock_msg_service.send_appointment_notification = AsyncMock()

            mock_dispatch.return_value = None

            appointment = await service.create(
                user_id=test_user.id,
                data=appointment_data,
            )

        assert appointment.assistant_confirm_status == 1, "新预约医助确认状态应为 1（待联系）"

    @pytest.mark.asyncio
    async def test_orm_default_is_pending_contact(
        self,
        db_session,
        test_tenant: Tenant,
        test_user,
        test_patient,
        test_doctor,
        test_schedule,
    ):
        """ORM 层默认值：未显式指定时落库为 1（待联系）"""
        appointment = await _create_appointment(
            db_session, test_tenant, test_user, test_patient,
            test_doctor, test_schedule,
        )
        assert appointment.assistant_confirm_status == 1


@pytest.mark.asyncio
class TestAssistantConfirmAdminApi:
    """管理端医助确认接口"""

    async def test_patch_confirm_flow_persists(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user,
        test_patient,
        test_doctor,
        test_schedule,
        super_admin_token: str,
    ):
        """PATCH 2→3 流转成功、响应回显 note、变更落库"""
        appointment = await _create_appointment(
            db_session, test_tenant, test_user, test_patient,
            test_doctor, test_schedule, assistant_confirm_status=2,
        )
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "X-Tenant-ID": test_tenant.id,
        }
        resp = await async_client.patch(
            f"/api/v1/appointments/{appointment.id}/assistant-confirm",
            headers=headers,
            json={"status": 3, "note": "已电话确认，患者明天上午到店"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert data["appointment"]["assistantConfirmStatus"] == 3
        # appointments 表无 note 列，note 仅在响应中回显
        assert data["note"] == "已电话确认，患者明天上午到店"

        # 重新查询数据库，确认变更已落库
        result = await db_session.execute(
            select(Appointment).where(Appointment.id == appointment.id)
        )
        persisted = result.scalar_one()
        assert persisted.assistant_confirm_status == 3

    async def test_patch_rejects_invalid_status(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user,
        test_patient,
        test_doctor,
        test_schedule,
        super_admin_token: str,
    ):
        """非法 status（如 5）返回 422，且不修改落库值"""
        appointment = await _create_appointment(
            db_session, test_tenant, test_user, test_patient,
            test_doctor, test_schedule, assistant_confirm_status=2,
        )
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "X-Tenant-ID": test_tenant.id,
        }
        resp = await async_client.patch(
            f"/api/v1/appointments/{appointment.id}/assistant-confirm",
            headers=headers,
            json={"status": 5},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        result = await db_session.execute(
            select(Appointment).where(Appointment.id == appointment.id)
        )
        persisted = result.scalar_one()
        assert persisted.assistant_confirm_status == 2, "非法请求不应修改医助确认状态"

    async def test_patch_requires_admin(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user,
        test_patient,
        test_doctor,
        test_schedule,
    ):
        """患者登录态调用管理端确认接口返回 403"""
        appointment = await _create_appointment(
            db_session, test_tenant, test_user, test_patient,
            test_doctor, test_schedule,
        )
        token = create_access_token({"sub": test_user.id, "type": "user"})
        resp = await async_client.patch(
            f"/api/v1/appointments/{appointment.id}/assistant-confirm",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": test_tenant.id,
            },
            json={"status": 3},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    async def test_list_filter_by_assistant_confirm_status(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user,
        test_patient,
        test_doctor,
        test_schedule,
        super_admin_token: str,
    ):
        """列表接口支持 assistant_confirm_status 过滤"""
        contacted = await _create_appointment(
            db_session, test_tenant, test_user, test_patient,
            test_doctor, test_schedule, assistant_confirm_status=2,
        )
        await _create_appointment(
            db_session, test_tenant, test_user, test_patient,
            test_doctor, test_schedule, assistant_confirm_status=1,
        )
        headers = {
            "Authorization": f"Bearer {super_admin_token}",
            "X-Tenant-ID": test_tenant.id,
        }
        resp = await async_client.get(
            "/api/v1/appointments/query?assistant_confirm_status=2",
            headers=headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["total"] == 1
        assert len(body["data"]) == 1
        assert body["data"][0]["id"] == contacted.id
        assert body["data"][0]["assistantConfirmStatus"] == 2


@pytest.mark.asyncio
class TestPatientAppointmentResponse:
    """患者端预约响应字段"""

    async def test_detail_response_includes_assistant_confirm_status(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user,
        test_patient,
        test_doctor,
        test_schedule,
    ):
        """患者详情响应包含 assistantConfirmStatus（camelCase 序列化）"""
        appointment = await _create_appointment(
            db_session, test_tenant, test_user, test_patient,
            test_doctor, test_schedule, assistant_confirm_status=3,
        )
        token = create_access_token({"sub": test_user.id, "type": "user"})
        resp = await async_client.get(
            f"/api/v1/appointments/query/{appointment.id}",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-ID": test_tenant.id,
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert "assistantConfirmStatus" in data
        assert data["assistantConfirmStatus"] == 3
