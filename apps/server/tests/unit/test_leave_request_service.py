"""停诊/调班申请服务单元测试

覆盖:
- get_by_id() 租户隔离
- get_list() 过滤
- create_stop_clinic() / create_schedule_change() 基本路径
- review() 状态校验
- cancel() 权限校验
"""
from datetime import datetime, date, timedelta
from uuid import uuid4

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.models.leave_request import LeaveRequest, RequestType, RequestStatus
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.models.department import Department
from app.models.store import Store
from app.models.tenant import Tenant, SubscriptionPlan
from app.models.user import User, Patient
from app.schemas.leave_request import (
    StopClinicCreate, ScheduleChangeCreate, ReviewRequest, LeaveRequestQuery,
    Period, RequestType as SchemaRequestType, RequestStatus as SchemaRequestStatus,
)
from app.modules.leave_requests.service import LeaveRequestService


@pytest.mark.unit
class TestLeaveRequestGetById:
    """测试按 ID 查询"""

    async def _create_request(self, db_session, tenant_id, doctor_id, **kwargs):
        defaults = dict(
            id=str(uuid4()),
            tenant_id=tenant_id,
            doctor_id=doctor_id,
            request_type=RequestType.STOP_CLINIC.value,
            stop_date=date.today() + timedelta(days=7),
            stop_period="morning",
            reason="测试停诊",
            status=RequestStatus.PENDING.value,
            affected_appointments=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        defaults.update(kwargs)
        req = LeaveRequest(**defaults)
        db_session.add(req)
        await db_session.commit()
        await db_session.refresh(req)
        return req

    async def test_found(self, db_session, test_tenant, test_doctor):
        req = await self._create_request(db_session, test_tenant.id, test_doctor.id)
        service = LeaveRequestService(db_session)

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.get_by_id(req.id)
        assert result is not None
        assert result.id == req.id

    async def test_not_found(self, db_session, test_tenant):
        service = LeaveRequestService(db_session)
        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.get_by_id("nonexistent")
        assert result is None

    async def test_tenant_isolation(self, db_session, test_tenant, test_doctor):
        req = await self._create_request(db_session, test_tenant.id, test_doctor.id)
        service = LeaveRequestService(db_session)

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value="other_tenant"):
            result = await service.get_by_id(req.id)
        assert result is None


@pytest.mark.unit
class TestLeaveRequestGetList:
    """测试列表查询"""

    async def _create_request(self, db_session, tenant_id, doctor_id, **kwargs):
        defaults = dict(
            id=str(uuid4()),
            tenant_id=tenant_id,
            doctor_id=doctor_id,
            request_type=RequestType.STOP_CLINIC.value,
            stop_date=date.today() + timedelta(days=7),
            stop_period="morning",
            reason="测试",
            status=RequestStatus.PENDING.value,
            affected_appointments=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        defaults.update(kwargs)
        req = LeaveRequest(**defaults)
        db_session.add(req)
        await db_session.commit()
        await db_session.refresh(req)
        return req

    async def test_basic_list(self, db_session, test_tenant, test_doctor):
        await self._create_request(db_session, test_tenant.id, test_doctor.id)
        service = LeaveRequestService(db_session)

        query = LeaveRequestQuery(page=1, page_size=10)
        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            items, total = await service.get_list(query)
        assert total == 1
        assert len(items) == 1

    async def test_filter_by_request_type(self, db_session, test_tenant, test_doctor):
        await self._create_request(
            db_session, test_tenant.id, test_doctor.id,
            request_type=RequestType.STOP_CLINIC.value,
        )
        await self._create_request(
            db_session, test_tenant.id, test_doctor.id,
            request_type=RequestType.SCHEDULE_CHANGE.value,
            original_date=date.today() + timedelta(days=3),
            original_period="morning",
            target_date=date.today() + timedelta(days=5),
            target_period="afternoon",
        )
        service = LeaveRequestService(db_session)

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            query = LeaveRequestQuery(request_type=SchemaRequestType.STOP_CLINIC, page=1, page_size=10)
            items, total = await service.get_list(query)
            assert total == 1

    async def test_filter_by_status(self, db_session, test_tenant, test_doctor):
        await self._create_request(
            db_session, test_tenant.id, test_doctor.id,
            status=RequestStatus.PENDING.value,
        )
        await self._create_request(
            db_session, test_tenant.id, test_doctor.id,
            status=RequestStatus.APPROVED.value,
        )
        service = LeaveRequestService(db_session)

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            query = LeaveRequestQuery(status=SchemaRequestStatus.PENDING, page=1, page_size=10)
            items, total = await service.get_list(query)
            assert total == 1


@pytest.mark.unit
class TestLeaveRequestCreate:
    """测试创建申请"""

    @pytest.fixture(autouse=True)
    def _mock_approval_engine(self):
        """Mock 掉 ApprovalEngine 避免依赖审批流配置"""
        with patch("app.modules.approval_flows.engine.ApprovalEngine") as mock_engine_cls:
            mock_engine = MagicMock()
            mock_engine.start_instance = AsyncMock()
            mock_engine_cls.return_value = mock_engine
            yield

    async def test_create_stop_clinic(self, db_session, test_tenant, test_doctor):
        service = LeaveRequestService(db_session)

        data = StopClinicCreate(
            doctor_id=test_doctor.id,
            stop_date=date.today() + timedelta(days=7),
            stop_period=Period.MORNING,
            reason="个人原因",
        )

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            req = await service.create_stop_clinic(data)

        assert req.id is not None
        assert req.tenant_id == test_tenant.id
        assert req.doctor_id == test_doctor.id
        assert req.request_type == RequestType.STOP_CLINIC.value
        assert req.status == RequestStatus.PENDING.value
        assert req.reason == "个人原因"

    async def test_create_schedule_change(self, db_session, test_tenant, test_doctor):
        service = LeaveRequestService(db_session)

        data = ScheduleChangeCreate(
            doctor_id=test_doctor.id,
            original_date=date.today() + timedelta(days=3),
            original_period=Period.MORNING,
            target_date=date.today() + timedelta(days=5),
            target_period=Period.AFTERNOON,
            reason="个人安排",
        )

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            req = await service.create_schedule_change(data)

        assert req.id is not None
        assert req.request_type == RequestType.SCHEDULE_CHANGE.value
        assert req.original_date == date.today() + timedelta(days=3)
        assert req.target_date == date.today() + timedelta(days=5)


@pytest.mark.unit
class TestLeaveRequestReview:
    """测试审核"""

    async def _create_pending(self, db_session, tenant_id, doctor_id):
        req = LeaveRequest(
            id=str(uuid4()),
            tenant_id=tenant_id,
            doctor_id=doctor_id,
            request_type=RequestType.STOP_CLINIC.value,
            stop_date=date.today() + timedelta(days=7),
            stop_period="morning",
            reason="test",
            status=RequestStatus.PENDING.value,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(req)
        await db_session.commit()
        await db_session.refresh(req)
        return req

    async def test_approve(self, db_session, test_tenant, test_doctor):
        req = await self._create_pending(db_session, test_tenant.id, test_doctor.id)
        service = LeaveRequestService(db_session)

        data = ReviewRequest(status=SchemaRequestStatus.APPROVED, review_comment="同意")

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.review(req.id, "reviewer_id", data)

        assert result is not None
        assert result.status == RequestStatus.APPROVED.value
        assert result.reviewer_id == "reviewer_id"
        assert result.review_comment == "同意"

    async def test_reject(self, db_session, test_tenant, test_doctor):
        req = await self._create_pending(db_session, test_tenant.id, test_doctor.id)
        service = LeaveRequestService(db_session)

        data = ReviewRequest(status=SchemaRequestStatus.REJECTED, review_comment="不同意")

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.review(req.id, "reviewer_id", data)

        assert result.status == RequestStatus.REJECTED.value

    async def test_review_already_processed(self, db_session, test_tenant, test_doctor):
        req = await self._create_pending(db_session, test_tenant.id, test_doctor.id)
        service = LeaveRequestService(db_session)

        data = ReviewRequest(status=SchemaRequestStatus.APPROVED)
        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            await service.review(req.id, "r1", data)

            with pytest.raises(ValueError, match="该申请已处理"):
                await service.review(req.id, "r2", data)

    async def test_review_not_found(self, db_session, test_tenant):
        service = LeaveRequestService(db_session)
        data = ReviewRequest(status=SchemaRequestStatus.APPROVED)

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.review("nonexistent", "r1", data)
        assert result is None


@pytest.mark.unit
class TestLeaveRequestCancel:
    """测试取消"""

    async def _create_pending(self, db_session, tenant_id, doctor_id):
        req = LeaveRequest(
            id=str(uuid4()),
            tenant_id=tenant_id,
            doctor_id=doctor_id,
            request_type=RequestType.STOP_CLINIC.value,
            stop_date=date.today() + timedelta(days=7),
            stop_period="morning",
            reason="test",
            status=RequestStatus.PENDING.value,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(req)
        await db_session.commit()
        await db_session.refresh(req)
        return req

    async def test_cancel_success(self, db_session, test_tenant, test_doctor):
        req = await self._create_pending(db_session, test_tenant.id, test_doctor.id)
        service = LeaveRequestService(db_session)

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.cancel(req.id, test_doctor.id)
        assert result is True

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            refreshed = await service.get_by_id(req.id)
        assert refreshed.status == RequestStatus.CANCELLED.value

    async def test_cancel_wrong_doctor(self, db_session, test_tenant, test_doctor):
        req = await self._create_pending(db_session, test_tenant.id, test_doctor.id)
        service = LeaveRequestService(db_session)

        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            with pytest.raises(ValueError, match="无权取消"):
                await service.cancel(req.id, "other_doctor")

    async def test_cancel_already_processed(self, db_session, test_tenant, test_doctor):
        req = await self._create_pending(db_session, test_tenant.id, test_doctor.id)
        req.status = RequestStatus.APPROVED.value
        await db_session.commit()

        service = LeaveRequestService(db_session)
        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            with pytest.raises(ValueError, match="该申请已处理"):
                await service.cancel(req.id, test_doctor.id)

    async def test_cancel_not_found(self, db_session, test_tenant):
        service = LeaveRequestService(db_session)
        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.cancel("nonexistent", "d1")
        assert result is False


@pytest.mark.unit
class TestLeaveRequestGetPendingCount:
    """测试待审核计数"""

    async def _create_request(self, db_session, tenant_id, doctor_id, status_val):
        req = LeaveRequest(
            id=str(uuid4()),
            tenant_id=tenant_id,
            doctor_id=doctor_id,
            request_type=RequestType.STOP_CLINIC.value,
            stop_date=date.today() + timedelta(days=7),
            stop_period="morning",
            reason="test",
            status=status_val,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(req)
        await db_session.commit()

    async def test_count(self, db_session, test_tenant, test_doctor):
        await self._create_request(db_session, test_tenant.id, test_doctor.id, RequestStatus.PENDING.value)
        await self._create_request(db_session, test_tenant.id, test_doctor.id, RequestStatus.APPROVED.value)
        await self._create_request(db_session, test_tenant.id, test_doctor.id, RequestStatus.PENDING.value)

        service = LeaveRequestService(db_session)
        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            count = await service.get_pending_count()
        assert count == 2


@pytest.mark.unit
class TestLeaveRequestGetDoctorRequests:
    """测试医生申请列表"""

    async def _create_request(self, db_session, tenant_id, doctor_id, **kwargs):
        defaults = dict(
            id=str(uuid4()),
            tenant_id=tenant_id,
            doctor_id=doctor_id,
            request_type=RequestType.STOP_CLINIC.value,
            stop_date=date.today() + timedelta(days=7),
            stop_period="morning",
            reason="test",
            status=RequestStatus.PENDING.value,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        defaults.update(kwargs)
        req = LeaveRequest(**defaults)
        db_session.add(req)
        await db_session.commit()

    async def test_doctor_requests(self, db_session, test_tenant, test_doctor):
        await self._create_request(db_session, test_tenant.id, test_doctor.id)
        await self._create_request(db_session, test_tenant.id, test_doctor.id, status=RequestStatus.APPROVED.value)

        service = LeaveRequestService(db_session)
        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            items = await service.get_doctor_requests(test_doctor.id)
        assert len(items) == 2

    async def test_doctor_requests_filter_status(self, db_session, test_tenant, test_doctor):
        await self._create_request(db_session, test_tenant.id, test_doctor.id)
        await self._create_request(db_session, test_tenant.id, test_doctor.id, status=RequestStatus.APPROVED.value)

        service = LeaveRequestService(db_session)
        with patch("app.modules.leave_requests.service.get_current_tenant_id", return_value=test_tenant.id):
            items = await service.get_doctor_requests(test_doctor.id, status="pending")
        assert len(items) == 1
