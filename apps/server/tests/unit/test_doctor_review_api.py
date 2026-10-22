"""患者端医生评价接口单元测试（内存 SQLite）

覆盖 GET/POST /api/v1/doctor-reviews：
- 列表分页（创建时间倒序）与就诊人姓名脱敏
- 患者登录态创建评价（body: doctor_id / rating / content）
- rating 越界拒绝（422）
- 未登录拒绝（401）
- 同一预约重复评价返回 409（依赖 appointment_id 唯一约束）
- 公开接口 fail-closed：缺少租户上下文返回 400
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.doctor_review import DoctorReview
from app.models.tenant import Tenant


async def _create_appointment(
    db_session: AsyncSession,
    tenant: Tenant,
    user,
    patient,
    doctor,
    schedule,
    created_at: datetime,
) -> Appointment:
    """创建一条最小可用的预约记录（评价必须挂预约）"""
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:14].upper()}",
        user_id=user.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=5,
        patient_name=patient.name,
        patient_phone=patient.phone,
        doctor_name=doctor.name,
        created_at=created_at,
        updated_at=created_at,
        created_by=user.id,
    )
    db_session.add(appointment)
    await db_session.commit()
    return appointment


async def _seed_review(
    db_session: AsyncSession,
    appointment: Appointment,
    user,
    doctor,
    rating: int,
    content: str,
    created_at: datetime,
) -> DoctorReview:
    """直接落一条评价记录（用于列表分页用例）"""
    review = DoctorReview(
        id=str(uuid4()),
        tenant_id=appointment.tenant_id,
        appointment_id=appointment.id,
        doctor_id=doctor.id,
        user_id=user.id,
        patient_id=appointment.patient_id,
        rating=rating,
        content=content,
        status=1,
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(review)
    await db_session.commit()
    return review


@pytest.mark.asyncio
class TestDoctorReviewPatientApi:
    """患者端医生评价接口"""

    async def test_list_pagination_desc_order_and_masked_name(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user,
        test_patient,
        test_doctor,
        test_schedule,
    ):
        """列表按创建时间倒序分页，就诊人姓名保留姓氏脱敏"""
        test_patient.name = "雷先生"
        db_session.add(test_patient)
        await db_session.commit()

        base = datetime(2026, 1, 1, 10, 0, 0)
        seeded = []
        for i in range(3):
            appointment = await _create_appointment(
                db_session, test_tenant, test_user, test_patient,
                test_doctor, test_schedule, base + timedelta(days=i),
            )
            seeded.append(
                await _seed_review(
                    db_session, appointment, test_user, test_doctor,
                    rating=5, content=f"第{i}次评价",
                    created_at=appointment.created_at + timedelta(minutes=5),
                )
            )

        # 第 1 页：最新 2 条（公开接口 fail-closed，必须携带租户上下文）
        tenant_headers = {"X-Tenant-ID": test_tenant.id}
        resp = await async_client.get(
            f"/api/v1/doctor-reviews?doctor_id={test_doctor.id}&page=1&page_size=2",
            headers=tenant_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()["data"]
        assert body["total"] == 3
        assert len(body["items"]) == 2
        assert body["items"][0]["id"] == seeded[-1].id
        assert body["items"][1]["id"] == seeded[-2].id
        # 脱敏：雷先生 -> 雷**（BaseSchema 按 camelCase 序列化）
        assert body["items"][0]["patientName"] == "雷**"

        # 第 2 页：剩余 1 条（最早的）
        resp_page2 = await async_client.get(
            f"/api/v1/doctor-reviews?doctor_id={test_doctor.id}&page=2&page_size=2",
            headers=tenant_headers,
        )
        assert resp_page2.status_code == status.HTTP_200_OK
        body_page2 = resp_page2.json()["data"]
        assert body_page2["total"] == 3
        assert len(body_page2["items"]) == 1
        assert body_page2["items"][0]["id"] == seeded[0].id

    async def test_list_requires_tenant_context(self, async_client: AsyncClient):
        """公开接口 fail-closed：缺少租户上下文（无 X-Tenant 头）返回 400"""
        resp = await async_client.get("/api/v1/doctor-reviews?doctor_id=any-doctor")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "租户" in resp.json()["detail"]

    async def test_list_requires_doctor_id(self, async_client: AsyncClient, test_tenant: Tenant):
        """缺少必填 doctor_id 时返回 422"""
        resp = await async_client.get(
            "/api/v1/doctor-reviews",
            headers={"X-Tenant-ID": test_tenant.id},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_review_success(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        test_user,
        test_appointment: Appointment,
    ):
        """患者登录后按 {doctor_id, rating, content} 创建评价成功"""
        token = create_access_token({"sub": test_user.id, "type": "user"})
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": test_tenant.id,
        }
        resp = await async_client.post(
            "/api/v1/doctor-reviews",
            headers=headers,
            json={
                "doctor_id": test_appointment.doctor_id,
                "rating": 5,
                "content": "医生很耐心，讲解清楚",
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert data["rating"] == 5
        assert data["content"] == "医生很耐心，讲解清楚"
        # 自动关联该患者在目标医生下的最近一次预约
        assert data["appointmentId"] == test_appointment.id

        # 创建后可从患者端列表查到
        resp_list = await async_client.get(
            f"/api/v1/doctor-reviews?doctor_id={test_appointment.doctor_id}",
            headers={"X-Tenant-ID": test_tenant.id},
        )
        assert resp_list.status_code == status.HTTP_200_OK
        assert resp_list.json()["data"]["total"] == 1

    async def test_create_review_duplicate_appointment_conflict(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        test_user,
        test_appointment: Appointment,
    ):
        """同一预约重复评价返回 409（appointment_id 唯一约束）"""
        token = create_access_token({"sub": test_user.id, "type": "user"})
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": test_tenant.id,
        }
        payload = {
            "doctor_id": test_appointment.doctor_id,
            "rating": 4,
            "content": "第一次评价",
        }
        first = await async_client.post("/api/v1/doctor-reviews", headers=headers, json=payload)
        assert first.status_code == status.HTTP_200_OK

        duplicate = await async_client.post(
            "/api/v1/doctor-reviews",
            headers=headers,
            json={**payload, "content": "第二次评价"},
        )
        assert duplicate.status_code == status.HTTP_409_CONFLICT

    async def test_create_review_rating_out_of_range(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        test_user,
        test_appointment: Appointment,
    ):
        """rating 越界（0/6）返回 422"""
        token = create_access_token({"sub": test_user.id, "type": "user"})
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": test_tenant.id,
        }
        for rating in (0, 6):
            resp = await async_client.post(
                "/api/v1/doctor-reviews",
                headers=headers,
                json={
                    "doctor_id": test_appointment.doctor_id,
                    "rating": rating,
                    "content": "评分越界",
                },
            )
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_review_requires_login(
        self,
        async_client: AsyncClient,
        test_tenant: Tenant,
        test_appointment: Appointment,
    ):
        """未携带登录态创建评价返回 401"""
        resp = await async_client.post(
            "/api/v1/doctor-reviews",
            headers={"X-Tenant-ID": test_tenant.id},
            json={
                "doctor_id": test_appointment.doctor_id,
                "rating": 5,
                "content": "未登录",
            },
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
