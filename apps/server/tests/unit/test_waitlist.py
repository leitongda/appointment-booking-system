"""
候补队列服务单元测试

测试用例包括：
1. 添加候补 - add_to_waitlist
2. 取消候补 - cancel_waitlist
3. 查询候补位置 - get_waitlist_position
4. 查询候补队列 - get_waitlist_for_schedule
5. 手动递补 - promote_next
6. 自动递补 - auto_promote
7. 清理过期候补 - cleanup_expired
"""
import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from sqlalchemy import select

from app.models.waitlist import WaitlistEntry
from app.models.schedule import Schedule
from app.modules.waitlist.service import WaitlistService
from app.modules.appointments.service import AppointmentService


class TestAddToWaitlist:
    """测试添加候补功能"""

    @pytest.mark.asyncio
    async def test_add_to_waitlist_success(
        self,
        db_session,
        test_schedule_full,
        test_patient,
        test_user,
        test_tenant,
    ):
        """测试正常添加候补"""
        service = WaitlistService(db_session)

        # Mock 规则引擎
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            entry = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule_full.id,
                symptom_description="头痛",
                priority=100,
            )

        assert entry is not None
        assert entry.user_id == test_user.id
        assert entry.patient_id == test_patient.id
        assert entry.schedule_id == test_schedule_full.id
        assert entry.status == 'WAITING'
        assert entry.position == 1
        assert entry.symptom_description == "头痛"

    @pytest.mark.asyncio
    async def test_add_to_waitlist_duplicate(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试重复添加候补被拒绝"""
        service = WaitlistService(db_session)

        # Mock 规则引擎
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            # 第一次添加
            await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )

        # 第二次添加相同候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="您已在候补队列中"):
                await service.add_to_waitlist(
                    user_id=test_user.id,
                    patient_id=test_patient.id,
                    schedule_id=test_schedule.id,
                )

    @pytest.mark.asyncio
    async def test_add_to_waitlist_schedule_not_found(
        self,
        db_session,
        test_patient,
        test_user,
    ):
        """测试排班不存在时添加候补失败"""
        service = WaitlistService(db_session)

        with pytest.raises(ValueError, match="排班不存在"):
            await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=str(uuid4()),
            )

    @pytest.mark.asyncio
    async def test_add_to_waitlist_queue_full(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
        test_tenant,
    ):
        """测试候补队列已满时添加失败"""
        # 设置排班的 shift_type_id
        test_schedule.shift_type_id = str(uuid4())
        await db_session.commit()

        # 创建多个患者
        from app.models.user import Patient
        patients = []
        for i in range(6):
            patient = Patient(
                id=str(uuid4()),
                user_id=test_user.id,
                name=f"就诊人{i}",
                phone=f"1380013899{i}",
                is_default=False,
                tenant_id=test_tenant.id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(patient)
            patients.append(patient)
        await db_session.commit()

        service = WaitlistService(db_session)

        # Mock 规则引擎返回容量策略（队列最大5人）
        mock_policy = MagicMock()
        mock_policy.waitlist_max_size = 5

        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=mock_policy)

            # 添加5个候补
            for i in range(5):
                await service.add_to_waitlist(
                    user_id=test_user.id,
                    patient_id=patients[i].id,
                    schedule_id=test_schedule.id,
                )

        # 第6个应该失败
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=mock_policy)

            with pytest.raises(ValueError, match="候补队列已满"):
                await service.add_to_waitlist(
                    user_id=test_user.id,
                    patient_id=patients[5].id,
                    schedule_id=test_schedule.id,
                )

    @pytest.mark.asyncio
    async def test_add_to_waitlist_position_increment(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
        test_tenant,
    ):
        """测试队列位置正确递增"""
        # 创建另一个患者以避免重复
        from app.models.user import Patient
        patient2 = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="另一个就诊人",
            phone="13800138999",
            is_default=False,
            tenant_id=test_tenant.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(patient2)
        await db_session.commit()

        service = WaitlistService(db_session)

        # Mock 规则引擎
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            # 添加多个候补
            entry1 = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )
            assert entry1.position == 1

            entry2 = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=patient2.id,
                schedule_id=test_schedule.id,
            )
            assert entry2.position == 2


class TestCancelWaitlist:
    """测试取消候补功能"""

    @pytest.mark.asyncio
    async def test_cancel_waitlist_success(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试正常取消候补"""
        service = WaitlistService(db_session)

        # 先添加候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            entry = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )

        # 取消候补
        result = await service.cancel_waitlist(
            entry_id=entry.id,
            user_id=test_user.id,
            is_admin=False,
        )

        assert result is not None
        assert result.status == 'CANCELLED'
        assert result.cancelled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_waitlist_not_found(
        self,
        db_session,
        test_user,
    ):
        """测试取消不存在的候补"""
        service = WaitlistService(db_session)

        result = await service.cancel_waitlist(
            entry_id=str(uuid4()),
            user_id=test_user.id,
            is_admin=False,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_waitlist_wrong_user(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试非本人取消候补失败"""
        service = WaitlistService(db_session)

        # 添加候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            entry = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )

        # 使用其他用户ID取消
        result = await service.cancel_waitlist(
            entry_id=entry.id,
            user_id="other_user_id",
            is_admin=False,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_waitlist_admin_bypass(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试管理员可以取消任何候补"""
        service = WaitlistService(db_session)

        # 添加候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            entry = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )

        # 管理员取消
        result = await service.cancel_waitlist(
            entry_id=entry.id,
            user_id="admin_user_id",
            is_admin=True,
        )

        assert result is not None
        assert result.status == 'CANCELLED'

    @pytest.mark.asyncio
    async def test_cancel_waitlist_invalid_status(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试取消非等待状态的候补失败"""
        service = WaitlistService(db_session)

        # 添加候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            entry = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )

        # 修改状态为已转预约
        entry.status = 'PROMOTED'
        await db_session.commit()

        # 尝试取消
        with pytest.raises(ValueError, match="只能取消等待中的候补"):
            await service.cancel_waitlist(
                entry_id=entry.id,
                user_id=test_user.id,
                is_admin=False,
            )


class TestGetWaitlistPosition:
    """测试查询候补位置功能"""

    @pytest.mark.asyncio
    async def test_get_waitlist_position_found(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试正常查询候补位置"""
        service = WaitlistService(db_session)

        # 添加候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            entry = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )

        # 查询位置
        position = await service.get_waitlist_position(
            schedule_id=test_schedule.id,
            user_id=test_user.id,
        )

        assert position == 1

    @pytest.mark.asyncio
    async def test_get_waitlist_position_not_found(
        self,
        db_session,
        test_schedule,
        test_user,
    ):
        """测试查询不存在的候补位置"""
        service = WaitlistService(db_session)

        position = await service.get_waitlist_position(
            schedule_id=test_schedule.id,
            user_id=test_user.id,
        )

        assert position is None

    @pytest.mark.asyncio
    async def test_get_waitlist_position_cancelled(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试已取消的候补不返回位置"""
        service = WaitlistService(db_session)

        # 添加并取消候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            entry = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )

        await service.cancel_waitlist(
            entry_id=entry.id,
            user_id=test_user.id,
        )

        # 查询位置
        position = await service.get_waitlist_position(
            schedule_id=test_schedule.id,
            user_id=test_user.id,
        )

        assert position is None


class TestGetWaitlistForSchedule:
    """测试查询排班候补队列功能"""

    @pytest.mark.asyncio
    async def test_get_waitlist_for_schedule_empty(
        self,
        db_session,
        test_schedule,
    ):
        """测试查询空队列"""
        service = WaitlistService(db_session)

        waitlist = await service.get_waitlist_for_schedule(
            schedule_id=test_schedule.id,
        )

        assert waitlist == []

    @pytest.mark.asyncio
    async def test_get_waitlist_for_schedule_with_entries(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
        test_tenant,
    ):
        """测试查询有候补的队列"""
        # 创建另一个患者
        from app.models.user import Patient
        patient2 = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="另一个就诊人",
            phone="13800138999",
            is_default=False,
            tenant_id=test_tenant.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(patient2)
        await db_session.commit()

        service = WaitlistService(db_session)

        # 添加多个候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            entry1 = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )
            entry2 = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=patient2.id,
                schedule_id=test_schedule.id,
            )

        # 查询队列
        waitlist = await service.get_waitlist_for_schedule(
            schedule_id=test_schedule.id,
        )

        assert len(waitlist) == 2
        assert waitlist[0].position == 1
        assert waitlist[1].position == 2

    @pytest.mark.asyncio
    async def test_get_waitlist_for_schedule_status_filter(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
        test_tenant,
    ):
        """测试按状态筛选候补队列"""
        # 创建另一个患者
        from app.models.user import Patient
        patient2 = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="另一个就诊人",
            phone="13800138999",
            is_default=False,
            tenant_id=test_tenant.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(patient2)
        await db_session.commit()

        service = WaitlistService(db_session)

        # 添加候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            entry1 = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )
            entry2 = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=patient2.id,
                schedule_id=test_schedule.id,
            )

        # 取消第一个
        await service.cancel_waitlist(
            entry_id=entry1.id,
            user_id=test_user.id,
        )

        # 查询等待中的候补
        waitlist = await service.get_waitlist_for_schedule(
            schedule_id=test_schedule.id,
            status='WAITING',
        )

        assert len(waitlist) == 1
        assert waitlist[0].id == entry2.id


class TestPromoteNext:
    """测试手动递补功能"""

    @pytest.mark.asyncio
    async def test_promote_next_success(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
        test_tenant,
        test_doctor,
    ):
        """测试正常递补下一个候补"""
        service = WaitlistService(db_session)

        # 添加候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            entry = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )

        # Mock 预约服务
        with patch('app.modules.waitlist.service_promotion.AppointmentService') as mock_appt_service_cls:
            mock_appt_service = MagicMock()
            mock_appt_service_cls.return_value = mock_appt_service

            # 创建一个预约对象作为返回值
            from app.models.appointment import Appointment
            mock_appointment = Appointment(
                id=str(uuid4()),
                appointment_no="TEST001",
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
                tenant_id=test_tenant.id,
                queue_number=1,
                status=1,
            )
            mock_appt_service.create = AsyncMock(return_value=mock_appointment)

            # 执行递补
            appointment = await service.promote_next(
                schedule_id=test_schedule.id,
                operator_id="admin_id",
            )

        assert appointment is not None
        assert appointment.id == mock_appointment.id

        # 验证候补状态更新
        await db_session.refresh(entry)
        assert entry.status == 'PROMOTED'
        assert entry.promoted_at is not None

    @pytest.mark.asyncio
    async def test_promote_next_no_waitlist(
        self,
        db_session,
        test_schedule,
    ):
        """测试队列为空时递补返回 None"""
        service = WaitlistService(db_session)

        appointment = await service.promote_next(
            schedule_id=test_schedule.id,
        )

        assert appointment is None

    @pytest.mark.asyncio
    async def test_promote_next_appointment_create_fails(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试预约创建失败时回滚候补状态"""
        service = WaitlistService(db_session)

        # 添加候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            entry = await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )

        # Mock 预约服务返回失败
        with patch('app.modules.waitlist.service_promotion.AppointmentService') as mock_appt_service_cls:
            mock_appt_service = MagicMock()
            mock_appt_service_cls.return_value = mock_appt_service
            mock_appt_service.create = AsyncMock(
                side_effect=ValueError("预约创建失败")
            )

            # 执行递补，应该抛出异常
            with pytest.raises(ValueError, match="候补转预约失败"):
                await service.promote_next(
                    schedule_id=test_schedule.id,
                )

        # 验证候补状态恢复为等待中
        await db_session.refresh(entry)
        assert entry.status == 'WAITING'
        assert entry.promoted_at is None


class TestAutoPromote:
    """测试自动递补功能"""

    @pytest.mark.asyncio
    async def test_auto_promote_success(
        self,
        db_session,
        test_schedule_full,
        test_patient,
        test_user,
        test_tenant,
    ):
        """测试自动递补成功"""
        # 将排班设为有2个空位
        test_schedule_full.booked_slots = 8  # total_slots=10
        await db_session.commit()

        # 创建多个患者
        from app.models.user import Patient
        patients = []
        for i in range(3):
            patient = Patient(
                id=str(uuid4()),
                user_id=test_user.id,
                name=f"就诊人{i}",
                phone=f"1380013899{i}",
                is_default=False,
                tenant_id=test_tenant.id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(patient)
            patients.append(patient)
        await db_session.commit()

        service = WaitlistService(db_session)

        # 添加3个候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            for patient in patients:
                await service.add_to_waitlist(
                    user_id=test_user.id,
                    patient_id=patient.id,
                    schedule_id=test_schedule_full.id,
                )

        # Mock 预约服务
        with patch('app.modules.waitlist.service_promotion.AppointmentService') as mock_appt_service_cls:
            mock_appt_service = MagicMock()
            mock_appt_service_cls.return_value = mock_appt_service

            # 创建预约对象
            from app.models.appointment import Appointment
            mock_appointment = Appointment(
                id=str(uuid4()),
                appointment_no="TEST001",
                user_id=test_user.id,
                patient_id=patients[0].id,
                schedule_id=test_schedule_full.id,
                tenant_id=test_tenant.id,
                queue_number=1,
                status=1,
            )
            mock_appt_service.create = AsyncMock(return_value=mock_appointment)

            # 执行自动递补
            promoted = await service.auto_promote(
                schedule_id=test_schedule_full.id,
                reason='APPOINTMENT_CANCELLED',
            )

        # 应该递补2个（剩余容量=2）
        assert len(promoted) == 2

    @pytest.mark.asyncio
    async def test_auto_promote_no_capacity(
        self,
        db_session,
        test_schedule_full,
        test_patient,
        test_user,
    ):
        """测试无剩余容量时不递补"""
        service = WaitlistService(db_session)

        # 添加候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule_full.id,
            )

        # 执行自动递补（号源已满）
        promoted = await service.auto_promote(
            schedule_id=test_schedule_full.id,
        )

        assert len(promoted) == 0

    @pytest.mark.asyncio
    async def test_auto_promote_disabled_by_policy(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试容量策略禁用自动递补"""
        # 设置排班的 shift_type_id
        test_schedule.shift_type_id = str(uuid4())
        await db_session.commit()

        service = WaitlistService(db_session)

        # Mock 规则引擎返回禁用自动递补的容量策略
        mock_policy = MagicMock()
        mock_policy.waitlist_enabled = False

        with patch('app.modules.waitlist.service_promotion.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=mock_policy)

            promoted = await service.auto_promote(
                schedule_id=test_schedule.id,
            )

        assert len(promoted) == 0

    @pytest.mark.asyncio
    async def test_auto_promote_manual_mode(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试手动递补模式下不自动递补"""
        # 设置排班的 shift_type_id
        test_schedule.shift_type_id = str(uuid4())
        await db_session.commit()

        service = WaitlistService(db_session)

        # Mock 规则引擎返回手动递补策略
        mock_policy = MagicMock()
        mock_policy.waitlist_enabled = True
        mock_policy.waitlist_promote_policy = 'MANUAL'

        with patch('app.modules.waitlist.service_promotion.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=mock_policy)

            promoted = await service.auto_promote(
                schedule_id=test_schedule.id,
            )

        assert len(promoted) == 0


class TestCleanupExpired:
    """测试清理过期候补功能"""

    @pytest.mark.asyncio
    async def test_cleanup_expired(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
    ):
        """测试清理已结束排班的候补"""
        service = WaitlistService(db_session)

        # 添加候补
        with patch('app.modules.waitlist.service_mutation.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            await service.add_to_waitlist(
                user_id=test_user.id,
                patient_id=test_patient.id,
                schedule_id=test_schedule.id,
            )

        # 将排班设为已结束
        test_schedule.status = 0
        await db_session.commit()

        # 执行清理
        await service.cleanup_expired()

        # 验证候补状态更新为过期
        result = await db_session.execute(
            select(WaitlistEntry).where(
                WaitlistEntry.schedule_id == test_schedule.id
            )
        )
        entry = result.scalar_one_or_none()

        assert entry is not None
        assert entry.status == 'EXPIRED'
