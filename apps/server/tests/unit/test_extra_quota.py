"""
加号申请/审批服务单元测试

测试 ExtraQuotaService 的核心方法：
1. create_request - 创建加号申请（自动批准 / 需审批）
2. approve - 审批通过
3. reject - 拒绝
4. get_list / get_by_id - 查询
5. 多租户隔离
6. 边界情况和错误处理
"""
import pytest
from datetime import datetime, date, time, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.models.extra_quota_request import ExtraQuotaRequest
from app.models.schedule import Schedule
from app.modules.schedules.service_extra_quota import ExtraQuotaService, AUTO_APPROVE_THRESHOLD


# ==================== 辅助函数 ====================


def _make_schedule(db_session, tenant, doctor, store, **overrides):
    """创建排班的辅助函数。"""
    tomorrow = date.today() + timedelta(days=1)
    defaults = dict(
        id=str(uuid4()),
        doctor_id=doctor.id,
        store_id=store.id,
        tenant_id=tenant.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        online_quota=5,
        offline_quota=3,
        reserved_quota=0,
        extra_quota=2,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    defaults.update(overrides)
    schedule = Schedule(**defaults)
    db_session.add(schedule)
    return schedule


# ==================== 创建申请测试 ====================


class TestCreateRequest:
    """测试创建加号申请"""

    @pytest.mark.asyncio
    async def test_create_auto_approved(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """加号数量 <= 阈值时自动批准"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        with patch('app.core.redis.RedisCache.tenant_distributed_lock') as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            service = ExtraQuotaService(db_session)
            request = await service.create_request(
                tenant_id=test_tenant.id,
                store_id=test_store.id,
                applicant_id="admin-001",
                schedule_id=schedule.id,
                quantity=3,  # <= AUTO_APPROVE_THRESHOLD
                quota_type="normal",
                open_to_public=True,
                reason="患者紧急加号",
            )

        assert request.approval_status == "approved"
        assert request.quantity == 3
        assert request.applicant_id == "admin-001"
        assert request.approver_id == "admin-001"
        assert request.approved_at is not None
        assert request.approval_remark is not None

        # 排班号源应已更新
        await db_session.refresh(schedule)
        assert schedule.extra_quota == 2 + 3  # 原有 2 + 新增 3
        assert schedule.total_slots == schedule.computed_total_slots

    @pytest.mark.asyncio
    async def test_create_needs_approval(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """加号数量 > 阈值时需要审批"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        with patch('app.core.redis.RedisCache.tenant_distributed_lock') as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            service = ExtraQuotaService(db_session)
            request = await service.create_request(
                tenant_id=test_tenant.id,
                store_id=test_store.id,
                applicant_id="admin-001",
                schedule_id=schedule.id,
                quantity=AUTO_APPROVE_THRESHOLD + 5,  # 超过阈值
                quota_type="special",
                open_to_public=False,
                patient_id="patient-999",
                reason="VIP 患者特批",
            )

        assert request.approval_status == "pending"
        assert request.approver_id is None
        assert request.approved_at is None

        # 排班号源不应变化
        await db_session.refresh(schedule)
        assert schedule.extra_quota == 2  # 保持原值

    @pytest.mark.asyncio
    async def test_create_exact_threshold(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """加号数量正好等于阈值时自动批准"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        with patch('app.core.redis.RedisCache.tenant_distributed_lock') as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            service = ExtraQuotaService(db_session)
            request = await service.create_request(
                tenant_id=test_tenant.id,
                store_id=test_store.id,
                applicant_id="admin-001",
                schedule_id=schedule.id,
                quantity=AUTO_APPROVE_THRESHOLD,  # 正好等于阈值
            )

        assert request.approval_status == "approved"


# ==================== 审批测试 ====================


class TestApprove:
    """测试审批通过"""

    @pytest.mark.asyncio
    async def test_approve_success(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """审批通过后更新号源"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        # 创建一个待审批的申请
        pending_request = ExtraQuotaRequest(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            schedule_id=schedule.id,
            doctor_id=test_doctor.id,
            schedule_date=str(schedule.schedule_date),
            time_slot="morning",
            quantity=10,
            quota_type="normal",
            open_to_public=1,
            approval_status="pending",
            applicant_id="admin-001",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(pending_request)
        await db_session.commit()
        await db_session.refresh(pending_request)

        original_extra = schedule.extra_quota

        with patch('app.core.redis.RedisCache.tenant_distributed_lock') as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            service = ExtraQuotaService(db_session)
            result = await service.approve(
                tenant_id=test_tenant.id,
                request_id=pending_request.id,
                approver_id="approver-001",
                remark="同意加号",
            )

        assert result.approval_status == "approved"
        assert result.approver_id == "approver-001"
        assert result.approval_remark == "同意加号"
        assert result.approved_at is not None

        # 排班号源应增加
        await db_session.refresh(schedule)
        assert schedule.extra_quota == original_extra + 10

    @pytest.mark.asyncio
    async def test_approve_not_pending(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """非 pending 状态无法审批"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        approved_request = ExtraQuotaRequest(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            schedule_id=schedule.id,
            doctor_id=test_doctor.id,
            schedule_date=str(schedule.schedule_date),
            time_slot="morning",
            quantity=5,
            quota_type="normal",
            approval_status="approved",  # 已批准
            applicant_id="admin-001",
            approver_id="approver-001",
            approved_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(approved_request)
        await db_session.commit()
        await db_session.refresh(approved_request)

        service = ExtraQuotaService(db_session)
        with pytest.raises(ValueError, match="只有待审批状态可以操作"):
            await service.approve(
                tenant_id=test_tenant.id,
                request_id=approved_request.id,
                approver_id="approver-002",
            )


# ==================== 拒绝测试 ====================


class TestReject:
    """测试拒绝加号"""

    @pytest.mark.asyncio
    async def test_reject_success(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """拒绝后不更新号源"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        pending_request = ExtraQuotaRequest(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            schedule_id=schedule.id,
            doctor_id=test_doctor.id,
            schedule_date=str(schedule.schedule_date),
            time_slot="morning",
            quantity=10,
            quota_type="normal",
            approval_status="pending",
            applicant_id="admin-001",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(pending_request)
        await db_session.commit()
        await db_session.refresh(pending_request)

        original_extra = schedule.extra_quota

        service = ExtraQuotaService(db_session)
        result = await service.reject(
            tenant_id=test_tenant.id,
            request_id=pending_request.id,
            approver_id="approver-001",
            remark="号源不足，暂不批准",
        )

        assert result.approval_status == "rejected"
        assert result.approver_id == "approver-001"
        assert result.approval_remark == "号源不足，暂不批准"

        # 排班号源不应变化
        await db_session.refresh(schedule)
        assert schedule.extra_quota == original_extra

    @pytest.mark.asyncio
    async def test_reject_not_pending(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """非 pending 状态无法拒绝"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        rejected_request = ExtraQuotaRequest(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            schedule_id=schedule.id,
            doctor_id=test_doctor.id,
            schedule_date=str(schedule.schedule_date),
            time_slot="morning",
            quantity=5,
            quota_type="normal",
            approval_status="rejected",  # 已拒绝
            applicant_id="admin-001",
            approver_id="approver-001",
            approved_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(rejected_request)
        await db_session.commit()
        await db_session.refresh(rejected_request)

        service = ExtraQuotaService(db_session)
        with pytest.raises(ValueError, match="只有待审批状态可以操作"):
            await service.reject(
                tenant_id=test_tenant.id,
                request_id=rejected_request.id,
                approver_id="approver-002",
            )


# ==================== 租户隔离测试 ====================


class TestTenantIsolation:
    """测试多租户隔离"""

    @pytest.mark.asyncio
    async def test_cross_tenant_schedule_rejected(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """跨租户访问排班应被拒绝"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        with patch('app.core.redis.RedisCache.tenant_distributed_lock') as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            service = ExtraQuotaService(db_session)
            with pytest.raises(ValueError, match="排班不存在或不属于当前租户"):
                await service.create_request(
                    tenant_id="other-tenant-id",
                    store_id=test_store.id,
                    applicant_id="admin-001",
                    schedule_id=schedule.id,
                    quantity=3,
                )

    @pytest.mark.asyncio
    async def test_cross_tenant_request_not_found(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """跨租户访问申请应返回 None"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        request = ExtraQuotaRequest(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            schedule_id=schedule.id,
            doctor_id=test_doctor.id,
            schedule_date=str(schedule.schedule_date),
            time_slot="morning",
            quantity=5,
            approval_status="pending",
            applicant_id="admin-001",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(request)
        await db_session.commit()

        service = ExtraQuotaService(db_session)
        result = await service.get_by_id("other-tenant-id", request.id)
        assert result is None


# ==================== 无效输入测试 ====================


class TestInvalidInput:
    """测试无效输入"""

    @pytest.mark.asyncio
    async def test_invalid_schedule_id(
        self,
        db_session,
        test_tenant,
    ):
        """不存在的排班 ID"""
        with patch('app.core.redis.RedisCache.tenant_distributed_lock') as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            service = ExtraQuotaService(db_session)
            with pytest.raises(ValueError, match="排班不存在"):
                await service.create_request(
                    tenant_id=test_tenant.id,
                    store_id="store-001",
                    applicant_id="admin-001",
                    schedule_id="non-existent-id",
                    quantity=3,
                )

    @pytest.mark.asyncio
    async def test_store_mismatch(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """门店不匹配"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        with patch('app.core.redis.RedisCache.tenant_distributed_lock') as mock_lock:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value="lock_value")
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_lock.return_value = mock_ctx

            service = ExtraQuotaService(db_session)
            with pytest.raises(ValueError, match="排班不属于指定门店"):
                await service.create_request(
                    tenant_id=test_tenant.id,
                    store_id="wrong-store-id",
                    applicant_id="admin-001",
                    schedule_id=schedule.id,
                    quantity=3,
                )

    @pytest.mark.asyncio
    async def test_approve_nonexistent_request(
        self,
        db_session,
        test_tenant,
    ):
        """审批不存在的申请"""
        service = ExtraQuotaService(db_session)
        with pytest.raises(ValueError, match="加号申请不存在"):
            await service.approve(
                tenant_id=test_tenant.id,
                request_id="non-existent-id",
                approver_id="approver-001",
            )


# ==================== 查询测试 ====================


class TestQuery:
    """测试查询功能"""

    @pytest.mark.asyncio
    async def test_get_list_with_filters(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """带筛选条件查询列表"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        # 创建多条申请
        for i in range(3):
            req = ExtraQuotaRequest(
                id=str(uuid4()),
                tenant_id=test_tenant.id,
                store_id=test_store.id,
                schedule_id=schedule.id,
                doctor_id=test_doctor.id,
                schedule_date=str(schedule.schedule_date),
                time_slot="morning",
                quantity=i + 1,
                approval_status="pending" if i < 2 else "approved",
                applicant_id="admin-001",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(req)
        await db_session.commit()

        service = ExtraQuotaService(db_session)

        # 查询所有
        items, total = await service.get_list(tenant_id=test_tenant.id)
        assert total == 3

        # 按状态筛选
        items, total = await service.get_list(
            tenant_id=test_tenant.id, approval_status="pending"
        )
        assert total == 2

        # 按门店筛选
        items, total = await service.get_list(
            tenant_id=test_tenant.id, store_id=test_store.id
        )
        assert total == 3

    @pytest.mark.asyncio
    async def test_get_by_id(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """按 ID 查询单条"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()
        await db_session.refresh(schedule)

        req = ExtraQuotaRequest(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            schedule_id=schedule.id,
            doctor_id=test_doctor.id,
            schedule_date=str(schedule.schedule_date),
            time_slot="morning",
            quantity=5,
            approval_status="pending",
            applicant_id="admin-001",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(req)
        await db_session.commit()

        service = ExtraQuotaService(db_session)
        result = await service.get_by_id(test_tenant.id, req.id)
        assert result is not None
        assert result.id == req.id
        assert result.quantity == 5
