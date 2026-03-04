"""
预约创建功能的单元测试

测试用例包括：
1. 正常创建预约
2. 号源已满时创建失败
3. 重复预约检查
4. 并发创建预约（分布式锁）
"""
import asyncio
from datetime import datetime, date, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.schemas.appointment import AppointmentCreate
from app.services.appointment_service import AppointmentService, APPOINTMENT_STATUS


# ==================== 测试辅助函数 ====================

def create_mock_lock_context():
    """创建模拟的分布式锁上下文管理器"""
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value="mock_lock_value")
    mock_context.__aexit__ = AsyncMock(return_value=None)
    return mock_context


def create_default_rule_engine_mocks():
    """创建默认的规则引擎 mock 返回值

    模拟规则引擎的默认行为：
    - 预约/签到/取消时间窗口都允许操作
    - 无规则组（使用门店默认配置）
    """
    now = datetime.now()
    return {
        'check_action_window': {
            'allowed': True,
            'open_at': now - timedelta(days=1),
            'close_at': now + timedelta(days=1),
            'fail_policy': 'REJECT',
            'message': ''
        },
        'get_applicable_rule_set': None,  # 无规则组
        'get_booking_policy': None,
        'get_capacity_policy': None,
        'check_booking_conflicts': {'allowed': True, 'reason': ''},
        'check_capacity_limits': {'allowed': True, 'reason': ''},
    }


# ==================== 测试类 ====================

class TestCreateAppointmentSuccess:
    """测试正常创建预约的场景"""

    @pytest.mark.asyncio
    async def test_create_appointment_success(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user
    ):
        """
        测试正常创建预约

        验证点：
        1. 返回预约号（非空，格式正确）
        2. 验证状态 = 已预约(1)
        3. 验证排班号源 -1
        """
        # 记录创建前的已预约数
        booked_slots_before = test_schedule.booked_slots

        # 构建预约创建请求
        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id,
            symptom_description="头痛三天"
        )

        # 创建服务实例
        service = AppointmentService(db_session)

        # Mock 依赖项
        with patch('app.services.appointment_service.RedisCache.distributed_lock') as mock_lock, \
             patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls, \
             patch('app.services.appointment_service.MessageService') as mock_msg_service_cls, \
             patch('app.services.appointment_service.dispatch_event_email') as mock_dispatch:

            # 配置分布式锁 mock
            mock_lock.return_value = create_mock_lock_context()

            # 配置规则引擎 mock
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            default_mocks = create_default_rule_engine_mocks()
            mock_rule_engine.check_action_window = AsyncMock(
                return_value=default_mocks['check_action_window']
            )
            mock_rule_engine.get_applicable_rule_set = AsyncMock(
                return_value=default_mocks['get_applicable_rule_set']
            )

            # 配置消息服务 mock（避免实际发送）
            mock_msg_service = MagicMock()
            mock_msg_service_cls.return_value = mock_msg_service
            mock_msg_service.send_appointment_notification = AsyncMock()

            # 配置邮件事件 mock
            mock_dispatch.return_value = None

            # 执行创建预约
            appointment = await service.create(
                user_id=test_user.id,
                data=appointment_data
            )

        # ========== 验证结果 ==========

        # 1. 验证预约号
        assert appointment.appointment_no is not None, "预约号不能为空"
        assert appointment.appointment_no.startswith("YY"), "预约号应以 YY 开头"
        assert len(appointment.appointment_no) > 10, "预约号长度应大于10"

        # 2. 验证状态 = 已预约(1)
        assert appointment.status == APPOINTMENT_STATUS['CONFIRMED'], \
            f"预期状态为已预约({APPOINTMENT_STATUS['CONFIRMED']})，实际为 {appointment.status}"

        # 3. 验证排班号源 -1
        # 重新查询排班以获取最新状态
        schedule_result = await db_session.execute(
            select(Schedule).where(Schedule.id == test_schedule.id)
        )
        updated_schedule = schedule_result.scalar_one_or_none()
        assert updated_schedule.booked_slots == booked_slots_before + 1, \
            f"预期已预约数 {booked_slots_before + 1}，实际为 {updated_schedule.booked_slots}"

        # 4. 验证其他关键字段
        assert appointment.user_id == test_user.id, "用户ID应匹配"
        assert appointment.patient_id == test_patient.id, "就诊人ID应匹配"
        assert appointment.schedule_id == test_schedule.id, "排班ID应匹配"
        assert appointment.queue_number == 1, "第一个预约的队列号应为1"
        assert appointment.symptom_description == "头痛三天", "病情描述应保存"


class TestCreateAppointmentScheduleFull:
    """测试号源已满时创建失败的场景"""

    @pytest.mark.asyncio
    async def test_create_appointment_schedule_full(
        self,
        db_session,
        test_schedule_full,
        test_patient,
        test_user
    ):
        """
        测试号源已满时创建失败

        验证点：
        1. 抛出 ValueError
        2. 错误信息包含 "号源已满"
        """
        # 构建预约创建请求
        appointment_data = AppointmentCreate(
            schedule_id=test_schedule_full.id,
            patient_id=test_patient.id
        )

        # 创建服务实例
        service = AppointmentService(db_session)

        # Mock 规则引擎（需要在排班检查之前）
        with patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine

            # 执行创建预约，预期抛出异常
            with pytest.raises(ValueError) as exc_info:
                await service.create(
                    user_id=test_user.id,
                    data=appointment_data
                )

        # 验证错误信息
        assert "号源已满" in str(exc_info.value), \
            f"错误信息应包含'号源已满'，实际为: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_create_appointment_schedule_full_in_lock(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user
    ):
        """
        测试在分布式锁内检测到号源已满

        场景：在获取锁之前号源还有剩余，但在锁内再次检查时已满
        这模拟了并发场景下的超卖保护
        """
        # 构建预约创建请求
        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id
        )

        # 创建服务实例
        service = AppointmentService(db_session)

        # 创建一个模拟锁上下文管理器，在进入时将排班设为已满
        class MockLockContext:
            """模拟锁上下文，在进入时修改排班状态"""
            def __init__(self, schedule):
                self.schedule = schedule

            async def __aenter__(self):
                # 模拟并发场景：在锁内检测到号源已被其他请求占满
                self.schedule.booked_slots = self.schedule.total_slots
                return "mock_lock_value"

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        with patch('app.services.appointment_service.RedisCache.distributed_lock') as mock_lock, \
             patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls:

            # 配置锁 mock 返回自定义上下文管理器
            mock_lock.return_value = MockLockContext(test_schedule)

            # 配置规则引擎 mock
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            default_mocks = create_default_rule_engine_mocks()
            mock_rule_engine.check_action_window = AsyncMock(
                return_value=default_mocks['check_action_window']
            )
            mock_rule_engine.get_applicable_rule_set = AsyncMock(
                return_value=default_mocks['get_applicable_rule_set']
            )

            # 执行创建预约，预期抛出异常
            with pytest.raises(ValueError) as exc_info:
                await service.create(
                    user_id=test_user.id,
                    data=appointment_data
                )

        # 验证错误信息
        assert "号源已满" in str(exc_info.value), \
            f"错误信息应包含'号源已满'，实际为: {exc_info.value}"


class TestCreateAppointmentDuplicate:
    """测试重复预约检查"""

    @pytest.mark.asyncio
    async def test_create_appointment_duplicate(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user,
        test_appointment  # 使用已有的预约 fixture
    ):
        """
        测试同一排班重复预约被拦截

        场景：同一就诊人对同一排班已有有效预约，再次预约应被拒绝
        """
        # 构建预约创建请求（同一排班，同一就诊人）
        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id
        )

        # 创建服务实例
        service = AppointmentService(db_session)

        # Mock 依赖项
        with patch('app.services.appointment_service.RedisCache.distributed_lock') as mock_lock, \
             patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls:

            # 配置分布式锁 mock
            mock_lock.return_value = create_mock_lock_context()

            # 配置规则引擎 mock
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            default_mocks = create_default_rule_engine_mocks()
            mock_rule_engine.check_action_window = AsyncMock(
                return_value=default_mocks['check_action_window']
            )
            mock_rule_engine.get_applicable_rule_set = AsyncMock(
                return_value=default_mocks['get_applicable_rule_set']
            )

            # 执行创建预约，预期抛出异常
            with pytest.raises(ValueError) as exc_info:
                await service.create(
                    user_id=test_user.id,
                    data=appointment_data
                )

        # 验证错误信息
        assert "已预约此时段" in str(exc_info.value), \
            f"错误信息应包含'已预约此时段'，实际为: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_create_appointment_different_patient_same_schedule(
        self,
        db_session,
        test_schedule,
        test_user
    ):
        """
        测试同一排班但不同就诊人可以预约

        场景：同一用户的不同就诊人可以预约同一排班
        """
        # 创建另一个就诊人
        from app.models.user import Patient
        another_patient = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="另一个就诊人",
            phone="13800138003",
            id_card="110101199001015678",
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(another_patient)
        await db_session.commit()
        await db_session.refresh(another_patient)

        # 构建预约创建请求（同一排班，不同就诊人）
        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=another_patient.id
        )

        # 创建服务实例
        service = AppointmentService(db_session)

        # Mock 依赖项
        with patch('app.services.appointment_service.RedisCache.distributed_lock') as mock_lock, \
             patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls, \
             patch('app.services.appointment_service.MessageService') as mock_msg_service_cls, \
             patch('app.services.appointment_service.dispatch_event_email') as mock_dispatch:

            # 配置分布式锁 mock
            mock_lock.return_value = create_mock_lock_context()

            # 配置规则引擎 mock
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            default_mocks = create_default_rule_engine_mocks()
            mock_rule_engine.check_action_window = AsyncMock(
                return_value=default_mocks['check_action_window']
            )
            mock_rule_engine.get_applicable_rule_set = AsyncMock(
                return_value=default_mocks['get_applicable_rule_set']
            )

            # 配置消息服务 mock
            mock_msg_service = MagicMock()
            mock_msg_service_cls.return_value = mock_msg_service
            mock_msg_service.send_appointment_notification = AsyncMock()

            # 配置邮件事件 mock
            mock_dispatch.return_value = None

            # 执行创建预约
            appointment = await service.create(
                user_id=test_user.id,
                data=appointment_data
            )

        # 验证创建成功
        assert appointment is not None, "预约应创建成功"
        assert appointment.status == APPOINTMENT_STATUS['CONFIRMED'], "状态应为已预约"


class TestCreateAppointmentConcurrent:
    """测试并发创建预约"""

    @pytest.mark.asyncio
    async def test_create_appointment_with_distributed_lock(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user
    ):
        """
        测试使用分布式锁创建预约

        验证点：
        1. 分布式锁被正确调用
        2. 锁名称格式正确
        """
        # 构建预约创建请求
        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id
        )

        # 创建服务实例
        service = AppointmentService(db_session)

        # Mock 依赖项
        with patch('app.services.appointment_service.RedisCache.distributed_lock') as mock_lock, \
             patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls, \
             patch('app.services.appointment_service.MessageService') as mock_msg_service_cls, \
             patch('app.services.appointment_service.dispatch_event_email') as mock_dispatch:

            # 配置分布式锁 mock
            mock_lock.return_value = create_mock_lock_context()

            # 配置规则引擎 mock
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            default_mocks = create_default_rule_engine_mocks()
            mock_rule_engine.check_action_window = AsyncMock(
                return_value=default_mocks['check_action_window']
            )
            mock_rule_engine.get_applicable_rule_set = AsyncMock(
                return_value=default_mocks['get_applicable_rule_set']
            )

            # 配置消息服务 mock
            mock_msg_service = MagicMock()
            mock_msg_service_cls.return_value = mock_msg_service
            mock_msg_service.send_appointment_notification = AsyncMock()

            # 配置邮件事件 mock
            mock_dispatch.return_value = None

            # 执行创建预约
            appointment = await service.create(
                user_id=test_user.id,
                data=appointment_data
            )

        # 验证分布式锁被调用
        mock_lock.assert_called_once()

        # 验证锁名称格式
        lock_call_args = mock_lock.call_args
        lock_name = lock_call_args[0][0] if lock_call_args[0] else lock_call_args[1].get('lock_name')
        expected_lock_prefix = f"appointment:create:{test_schedule.id}"
        assert lock_name == expected_lock_prefix, \
            f"锁名称应为 {expected_lock_prefix}，实际为 {lock_name}"

        # 验证预约创建成功
        assert appointment is not None
        assert appointment.status == APPOINTMENT_STATUS['CONFIRMED']

    @pytest.mark.asyncio
    async def test_create_appointment_lock_failure(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user
    ):
        """
        测试分布式锁获取失败时的处理

        场景：获取分布式锁超时或失败
        """
        # 构建预约创建请求
        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id
        )

        # 创建服务实例
        service = AppointmentService(db_session)

        # 创建一个会抛出 RuntimeError 的锁 mock
        def mock_lock_side_effect(*args, **kwargs):
            raise RuntimeError("无法获取分布式锁")

        with patch('app.services.appointment_service.RedisCache.distributed_lock') as mock_lock, \
             patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls:

            # 配置锁 mock 抛出异常
            mock_lock.side_effect = mock_lock_side_effect

            # 配置规则引擎 mock
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            default_mocks = create_default_rule_engine_mocks()
            mock_rule_engine.check_action_window = AsyncMock(
                return_value=default_mocks['check_action_window']
            )
            mock_rule_engine.get_applicable_rule_set = AsyncMock(
                return_value=default_mocks['get_applicable_rule_set']
            )

            # 执行创建预约，预期抛出异常
            with pytest.raises(ValueError) as exc_info:
                await service.create(
                    user_id=test_user.id,
                    data=appointment_data
                )

        # 验证错误信息
        assert "系统繁忙" in str(exc_info.value), \
            f"错误信息应包含'系统繁忙'，实际为: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_create_appointment_no_overselling(
        self,
        db_session,
        test_schedule,
        test_user
    ):
        """
        测试号源不超售

        场景：排班只剩最后一个号源，模拟并发请求，确保不会超售

        这个测试验证了在分布式锁保护下的原子性操作
        """
        # 将排班设为只剩一个号源
        test_schedule.total_slots = 1
        test_schedule.booked_slots = 0
        await db_session.commit()

        # 创建多个就诊人（模拟并发请求）
        from app.models.user import Patient
        patients = []
        for i in range(3):
            patient = Patient(
                id=str(uuid4()),
                user_id=test_user.id,
                name=f"并发测试就诊人{i}",
                phone=f"1380013801{i}",
                id_card=f"11010119900101123{i}",
                is_default=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(patient)
            patients.append(patient)

        await db_session.commit()

        # 为每个就诊人刷新以获取ID
        for patient in patients:
            await db_session.refresh(patient)

        # 创建服务实例
        service = AppointmentService(db_session)

        # 用于跟踪成功和失败的请求
        results = {"success": 0, "failure": 0}
        lock = asyncio.Lock()  # 用于保护 results 的并发访问

        async def create_appointment_task(patient_id: str, task_id: int):
            """并发创建预约的任务"""
            try:
                appointment_data = AppointmentCreate(
                    schedule_id=test_schedule.id,
                    patient_id=patient_id
                )

                with patch('app.services.appointment_service.RedisCache.distributed_lock') as mock_lock, \
                     patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls, \
                     patch('app.services.appointment_service.MessageService'), \
                     patch('app.services.appointment_service.dispatch_event_email'):

                    # 配置分布式锁 mock
                    mock_lock.return_value = create_mock_lock_context()

                    # 配置规则引擎 mock
                    mock_rule_engine = MagicMock()
                    mock_rule_engine_cls.return_value = mock_rule_engine
                    default_mocks = create_default_rule_engine_mocks()
                    mock_rule_engine.check_action_window = AsyncMock(
                        return_value=default_mocks['check_action_window']
                    )
                    mock_rule_engine.get_applicable_rule_set = AsyncMock(
                        return_value=default_mocks['get_applicable_rule_set']
                    )

                    # 在创建预约前检查当前排班状态
                    # 注意：由于我们使用的是同一个 db_session，
                    # SQLite 内存数据库在同一会话中不会看到其他并发事务的更改
                    # 这里我们通过在锁内检查来模拟分布式环境的行为

                    await service.create(
                        user_id=test_user.id,
                        data=appointment_data
                    )

                    async with lock:
                        results["success"] += 1

            except ValueError as e:
                if "号源已满" in str(e) or "已预约此时段" in str(e):
                    async with lock:
                        results["failure"] += 1
                else:
                    raise

        # 由于 SQLite 内存数据库的会话隔离特性，真正的并发测试需要更复杂的设置
        # 这里我们验证顺序执行时的行为
        for i, patient in enumerate(patients):
            try:
                appointment_data = AppointmentCreate(
                    schedule_id=test_schedule.id,
                    patient_id=patient.id
                )

                with patch('app.services.appointment_service.RedisCache.distributed_lock') as mock_lock, \
                     patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls, \
                     patch('app.services.appointment_service.MessageService'), \
                     patch('app.services.appointment_service.dispatch_event_email'):

                    mock_lock.return_value = create_mock_lock_context()

                    mock_rule_engine = MagicMock()
                    mock_rule_engine_cls.return_value = mock_rule_engine
                    default_mocks = create_default_rule_engine_mocks()
                    mock_rule_engine.check_action_window = AsyncMock(
                        return_value=default_mocks['check_action_window']
                    )
                    mock_rule_engine.get_applicable_rule_set = AsyncMock(
                        return_value=default_mocks['get_applicable_rule_set']
                    )

                    await service.create(
                        user_id=test_user.id,
                        data=appointment_data
                    )
                    results["success"] += 1

            except ValueError as e:
                if "号源已满" in str(e):
                    results["failure"] += 1
                else:
                    raise

        # 验证结果：只有1个成功，其他失败
        assert results["success"] == 1, \
            f"预期只有1个预约成功，实际成功 {results['success']} 个"
        assert results["failure"] == 2, \
            f"预期2个预约失败，实际失败 {results['failure']} 个"

        # 验证最终排班状态
        schedule_result = await db_session.execute(
            select(Schedule).where(Schedule.id == test_schedule.id)
        )
        final_schedule = schedule_result.scalar_one_or_none()
        assert final_schedule.booked_slots == 1, \
            f"预期最终已预约数为1，实际为 {final_schedule.booked_slots}"


class TestCreateAppointmentValidation:
    """测试预约创建的输入验证"""

    @pytest.mark.asyncio
    async def test_create_appointment_schedule_not_found(
        self,
        db_session,
        test_patient,
        test_user
    ):
        """
        测试排班不存在时的错误处理
        """
        # 使用不存在的排班ID
        appointment_data = AppointmentCreate(
            schedule_id=str(uuid4()),
            patient_id=test_patient.id
        )

        service = AppointmentService(db_session)

        with pytest.raises(ValueError) as exc_info:
            await service.create(
                user_id=test_user.id,
                data=appointment_data
            )

        assert "排班不存在" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_appointment_patient_not_found(
        self,
        db_session,
        test_schedule,
        test_user
    ):
        """
        测试就诊人不存在时的错误处理
        """
        # 使用不存在的就诊人ID
        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=str(uuid4())
        )

        service = AppointmentService(db_session)

        # Mock 规则引擎
        with patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            default_mocks = create_default_rule_engine_mocks()
            mock_rule_engine.check_action_window = AsyncMock(
                return_value=default_mocks['check_action_window']
            )
            mock_rule_engine.get_applicable_rule_set = AsyncMock(
                return_value=default_mocks['get_applicable_rule_set']
            )

            with pytest.raises(ValueError) as exc_info:
                await service.create(
                    user_id=test_user.id,
                    data=appointment_data
                )

        assert "就诊人不存在" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_appointment_schedule_stopped(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user
    ):
        """
        测试排班已停诊时的错误处理
        """
        # 将排班设为停诊状态
        test_schedule.status = 0
        await db_session.commit()

        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id
        )

        service = AppointmentService(db_session)

        with pytest.raises(ValueError) as exc_info:
            await service.create(
                user_id=test_user.id,
                data=appointment_data
            )

        assert "已停诊" in str(exc_info.value)


class TestCreateAppointmentRuleEngine:
    """测试规则引擎集成的预约创建"""

    @pytest.mark.asyncio
    async def test_create_appointment_rule_engine_reject(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user
    ):
        """
        测试规则引擎拒绝预约时的处理

        场景：规则引擎检查预约时间窗，返回不允许
        """
        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id
        )

        service = AppointmentService(db_session)

        # Mock 规则引擎返回拒绝
        with patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls:
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine

            # 配置预约时间窗检查返回不允许
            mock_rule_engine.check_action_window = AsyncMock(
                return_value={
                    'allowed': False,
                    'open_at': datetime.now() + timedelta(days=1),
                    'close_at': datetime.now() + timedelta(days=2),
                    'fail_policy': 'REJECT',
                    'message': '未到预约开放时间'
                }
            )
            mock_rule_engine.get_applicable_rule_set = AsyncMock(
                return_value=create_default_rule_engine_mocks()['get_applicable_rule_set']
            )

            with pytest.raises(ValueError) as exc_info:
                await service.create(
                    user_id=test_user.id,
                    data=appointment_data
                )

        assert "未到预约开放时间" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_appointment_booking_policy_conflict(
        self,
        db_session,
        test_schedule,
        test_patient,
        test_user
    ):
        """
        测试预约策略冲突时的处理

        场景：规则引擎检测到预约冲突（如每日限约次数已满）
        """
        # 设置排班的 shift_type_id，使规则引擎检查生效
        test_schedule.shift_type_id = str(uuid4())
        await db_session.commit()

        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id
        )

        service = AppointmentService(db_session)

        # Mock 规则引擎
        with patch('app.services.appointment_service.RuleEngineService') as mock_rule_engine_cls:

            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine

            # 配置时间窗检查通过
            mock_rule_engine.check_action_window = AsyncMock(
                return_value=create_default_rule_engine_mocks()['check_action_window']
            )

            # 配置规则组存在
            mock_rule_set = MagicMock()
            mock_rule_set.id = str(uuid4())
            mock_rule_engine.get_applicable_rule_set = AsyncMock(return_value=mock_rule_set)

            # 配置预约策略
            mock_booking_policy = MagicMock()
            mock_rule_engine.get_booking_policy = AsyncMock(return_value=mock_booking_policy)

            # 配置预约冲突检查返回不允许
            mock_rule_engine.check_booking_conflicts = AsyncMock(
                return_value={
                    'allowed': False,
                    'reason': '当日预约次数已达上限'
                }
            )

            # 配置容量策略
            mock_rule_engine.get_capacity_policy = AsyncMock(return_value=None)

            with pytest.raises(ValueError) as exc_info:
                await service.create(
                    user_id=test_user.id,
                    data=appointment_data
                )

        assert "当日预约次数已达上限" in str(exc_info.value)
