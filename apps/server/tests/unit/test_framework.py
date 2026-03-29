"""
测试框架验证测试

验证 conftest.py 中的 fixtures 是否正常工作
"""
import pytest
from datetime import datetime

from app.models.user import User
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.appointment import Appointment


class TestFixtures:
    """测试 Fixtures 是否正常工作"""

    @pytest.mark.asyncio
    async def test_db_session_works(self, db_session):
        """验证数据库会话可用"""
        assert db_session is not None

    @pytest.mark.asyncio
    async def test_test_store_created(self, test_store):
        """验证测试门店创建"""
        assert test_store.id is not None
        assert test_store.name == "测试门店"

    @pytest.mark.asyncio
    async def test_test_department_created(self, test_department):
        """验证测试科室创建"""
        assert test_department.id is not None
        assert test_department.name == "测试科室"

    @pytest.mark.asyncio
    async def test_test_doctor_created(self, test_doctor):
        """验证测试医生创建"""
        assert test_doctor.id is not None
        assert test_doctor.name == "测试医生"
        assert test_doctor.title == "主治医师"

    @pytest.mark.asyncio
    async def test_test_user_created(self, test_user):
        """验证测试用户创建"""
        assert test_user.id is not None
        assert test_user.phone == "13800138001"

    @pytest.mark.asyncio
    async def test_test_patient_created(self, test_patient):
        """验证测试就诊人创建"""
        assert test_patient.id is not None
        assert test_patient.name == "测试就诊人"

    @pytest.mark.asyncio
    async def test_test_schedule_created(self, test_schedule):
        """验证测试排班创建"""
        assert test_schedule.id is not None
        assert test_schedule.time_slot == "morning"
        assert test_schedule.total_slots == 10
        assert test_schedule.booked_slots == 0

    @pytest.mark.asyncio
    async def test_test_appointment_created(self, test_appointment):
        """验证测试预约创建"""
        assert test_appointment.id is not None
        assert test_appointment.status == 1  # 已预约
        assert test_appointment.queue_number == 1

    @pytest.mark.asyncio
    async def test_appointment_service_created(self, appointment_service):
        """验证预约服务创建"""
        assert appointment_service is not None
        assert appointment_service.db is not None


class TestDatabaseIsolation:
    """测试数据库隔离"""

    @pytest.mark.asyncio
    async def test_data_isolated_between_tests(self, db_session):
        """验证测试之间数据隔离"""
        # 这个测试不应该看到其他测试的数据
        from sqlalchemy import select

        result = await db_session.execute(select(User))
        users = result.scalars().all()

        # 应该只有 test_user fixture 创建的用户
        # 由于每个测试独立，这里可能是 0 或 1 个
        assert len(users) <= 1
