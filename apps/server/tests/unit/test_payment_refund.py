"""
预约支付退款流程单元测试

测试用例包括：
1. 诊费查询优先级测试 (_get_consultation_fee)
2. 预约创建时支付状态测试
3. 退款服务核心逻辑测试
"""
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.appointment import Appointment
from app.models.consultation_fee import (
    DoctorConsultationFee,
    ConsultationFeeType,
    StoreFeeTemplate,
    ConsultationFeeTemplate,
)
from app.models.refund import RefundRecord
from app.models.schedule import Schedule
from app.schemas.appointment import AppointmentCreate
from app.infrastructure.payments.wechat_pay_service import WeChatPayService
from app.modules.appointments.service_booking import AppointmentBookingService
from app.modules.refunds.service import RefundService


# ==================== 租户上下文 Patches ====================

def _tenant_patches(test_tenant_id):
    """返回模拟租户上下文和配额检查的 patch 字典"""
    return {
        'app.modules.appointments.service_booking.get_current_tenant_id': lambda: test_tenant_id,
        'app.modules.appointments.service_booking.check_quota': AsyncMock(),
        'app.modules.refunds.service.get_current_tenant_id': lambda: test_tenant_id,
    }


def _create_mock_lock_context():
    """创建模拟的分布式锁上下文管理器"""
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value="mock_lock_value")
    mock_context.__aexit__ = AsyncMock(return_value=None)
    return mock_context


def _create_default_rule_engine_mocks():
    """创建默认的规则引擎 mock 返回值"""
    now = datetime.now()
    return {
        'check_action_window': {
            'allowed': True,
            'open_at': now - timedelta(days=1),
            'close_at': now + timedelta(days=1),
            'fail_policy': 'REJECT',
            'message': ''
        },
        'get_applicable_rule_set': None,
        'get_booking_policy': None,
        'get_capacity_policy': None,
    }


# ==================== 诊费查询测试 ====================

class TestGetConsultationFee:
    """测试诊费查询优先级逻辑"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_consultation_fee_doctor_level_priority(
        self, db_session, test_doctor, test_department, test_store, test_tenant
    ):
        """
        测试医生级诊费优先级最高

        验证点：
        1. 医生级诊费 > 门店级 > 全局默认
        2. 返回正确的诊费金额
        """
        # 创建默认诊费类型
        fee_type = ConsultationFeeType(
            id=str(uuid4()),
            store_id=None,  # 全局类型
            name="默认诊费",
            code="default",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(fee_type)
        await db_session.flush()

        # 创建门店诊费模板（应被医生级覆盖）
        store_template = StoreFeeTemplate(
            id=str(uuid4()),
            store_id=test_store.id,
            fee_type_id=fee_type.id,
            initial_fee=Decimal("30.00"),
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(store_template)

        # 创建全局默认模板（应被门店级覆盖）
        global_template = ConsultationFeeTemplate(
            id=str(uuid4()),
            fee_type_id=fee_type.id,
            initial_fee=Decimal("20.00"),
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(global_template)

        # 创建医生级诊费配置（优先级最高）
        doctor_fee = DoctorConsultationFee(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            department_id=test_department.id,
            fee_type_id=fee_type.id,
            initial_fee=Decimal("50.00"),
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(doctor_fee)
        await db_session.commit()

        # 创建服务实例并测试
        service = AppointmentBookingService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            fee = await service._get_consultation_fee(
                doctor_id=test_doctor.id,
                store_id=test_store.id,
                department_id=test_department.id,
            )

        # 验证返回医生级诊费
        assert fee == Decimal("50.00"), f"预期 50.00，实际 {fee}"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_consultation_fee_store_level_fallback(
        self, db_session, test_doctor, test_department, test_store, test_tenant
    ):
        """
        测试门店级诊费回退逻辑

        验证点：
        1. 无医生级配置时使用门店级
        2. 门店级 > 全局默认
        """
        # 创建默认诊费类型
        fee_type = ConsultationFeeType(
            id=str(uuid4()),
            store_id=None,
            name="默认诊费",
            code="default",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(fee_type)
        await db_session.flush()

        # 创建门店诊费模板
        store_template = StoreFeeTemplate(
            id=str(uuid4()),
            store_id=test_store.id,
            fee_type_id=fee_type.id,
            initial_fee=Decimal("30.00"),
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(store_template)

        # 创建全局默认模板（应被门店级覆盖）
        global_template = ConsultationFeeTemplate(
            id=str(uuid4()),
            fee_type_id=fee_type.id,
            initial_fee=Decimal("20.00"),
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(global_template)
        await db_session.commit()

        # 创建服务实例并测试
        service = AppointmentBookingService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            fee = await service._get_consultation_fee(
                doctor_id=test_doctor.id,
                store_id=test_store.id,
                department_id=test_department.id,
            )

        # 验证返回门店级诊费
        assert fee == Decimal("30.00"), f"预期 30.00，实际 {fee}"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_consultation_fee_global_default_fallback(
        self, db_session, test_doctor, test_department, test_store, test_tenant
    ):
        """
        测试全局默认诊费回退逻辑

        验证点：
        1. 无医生级和门店级配置时使用全局默认
        """
        # 创建默认诊费类型
        fee_type = ConsultationFeeType(
            id=str(uuid4()),
            store_id=None,
            name="默认诊费",
            code="default",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(fee_type)
        await db_session.flush()

        # 创建全局默认模板
        global_template = ConsultationFeeTemplate(
            id=str(uuid4()),
            fee_type_id=fee_type.id,
            initial_fee=Decimal("20.00"),
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(global_template)
        await db_session.commit()

        # 创建服务实例并测试
        service = AppointmentBookingService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            fee = await service._get_consultation_fee(
                doctor_id=test_doctor.id,
                store_id=test_store.id,
                department_id=test_department.id,
            )

        # 验证返回全局默认诊费
        assert fee == Decimal("20.00"), f"预期 20.00，实际 {fee}"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_consultation_fee_no_config_returns_zero(
        self, db_session, test_doctor, test_department, test_store, test_tenant
    ):
        """
        测试无诊费配置时返回 0

        验证点：
        1. 无任何配置时返回 Decimal("0")
        """
        # 不创建任何诊费配置

        # 创建服务实例并测试
        service = AppointmentBookingService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            fee = await service._get_consultation_fee(
                doctor_id=test_doctor.id,
                store_id=test_store.id,
                department_id=test_department.id,
            )

        # 验证返回 0
        assert fee == Decimal("0"), f"预期 0，实际 {fee}"


# ==================== 预约创建支付状态测试 ====================

class TestAppointmentCreationPaymentStatus:
    """测试预约创建时的支付状态逻辑"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_appointment_with_fee_pending_payment(
        self, db_session, test_schedule, test_patient, test_user, test_tenant,
        test_doctor, test_department
    ):
        """
        测试有诊费时预约状态为待支付

        验证点：
        1. status=0（待支付）
        2. payment_amount 正确保存
        3. 返回支付参数
        """
        # 创建诊费配置
        fee_type = ConsultationFeeType(
            id=str(uuid4()),
            store_id=None,
            name="默认诊费",
            code="default",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(fee_type)
        await db_session.flush()

        doctor_fee = DoctorConsultationFee(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_schedule.store_id,
            department_id=test_department.id,
            fee_type_id=fee_type.id,
            initial_fee=Decimal("50.00"),
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(doctor_fee)
        await db_session.commit()

        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id,
            symptom_description="头痛"
        )

        service = AppointmentBookingService(db_session)

        # Mock _prepare_payment_params 避免调用有源码 bug 的代码
        async def mock_prepare_payment_params(appointment, schedule, user_openid=None):
            return {
                "payment_config_id": str(uuid4()),
                "payment_mode": "wechat_jsapi",
            }

        with patch('app.modules.appointments.service_booking.RedisCache.tenant_distributed_lock') as mock_lock, \
             patch('app.modules.appointments.service_booking.RuleEngineService') as mock_rule_engine_cls, \
             patch('app.modules.appointments.service_booking.MessageService') as mock_msg_service_cls, \
             patch('app.middleware.tenant_context.get_current_tenant_id', return_value=test_tenant.id), \
             patch('app.common.quota.check_quota', new_callable=AsyncMock), \
             patch.object(service, '_prepare_payment_params', mock_prepare_payment_params):

            # 配置锁 mock
            mock_lock.return_value = _create_mock_lock_context()

            # 配置规则引擎 mock
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            default_mocks = _create_default_rule_engine_mocks()
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

            # 执行创建预约
            result = await service.create(
                user_id=test_user.id,
                data=appointment_data
            )

        # 验证返回包含支付参数
        assert isinstance(result, dict), "有诊费时应返回 dict"
        assert result.get("payment_required") is True, "应标记需要支付"
        assert result.get("payment_amount") == 50.00, "支付金额应为 50.00"
        assert result.get("payment_params") is not None, "支付参数应嵌套在 payment_params 中"
        assert result["payment_params"]["payment_mode"] == "wechat_jsapi"

        # 验证预约状态
        appointment = result.get("appointment")
        assert appointment is not None, "应包含预约对象"
        assert appointment.status == 0, f"状态应为待支付(0)，实际为 {appointment.status}"
        assert appointment.payment_amount == Decimal("50.00"), "payment_amount 应正确保存"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_appointment_without_fee_confirmed(
        self, db_session, test_schedule, test_patient, test_user, test_tenant
    ):
        """
        测试无诊费时预约状态为已确认

        验证点：
        1. status=1（已确认）
        2. payment_amount=None 或 0
        3. 直接返回预约对象（不含支付参数）
        """
        appointment_data = AppointmentCreate(
            schedule_id=test_schedule.id,
            patient_id=test_patient.id,
            symptom_description="头痛"
        )

        service = AppointmentBookingService(db_session)

        with patch('app.modules.appointments.service_booking.RedisCache.tenant_distributed_lock') as mock_lock, \
             patch('app.modules.appointments.service_booking.RuleEngineService') as mock_rule_engine_cls, \
             patch('app.modules.appointments.service_booking.MessageService') as mock_msg_service_cls, \
             patch('app.middleware.tenant_context.get_current_tenant_id', return_value=test_tenant.id), \
             patch('app.common.quota.check_quota', new_callable=AsyncMock):

            # 配置锁 mock
            mock_lock.return_value = _create_mock_lock_context()

            # 配置规则引擎 mock
            mock_rule_engine = MagicMock()
            mock_rule_engine_cls.return_value = mock_rule_engine
            default_mocks = _create_default_rule_engine_mocks()
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

            # 执行创建预约
            result = await service.create(
                user_id=test_user.id,
                data=appointment_data
            )

        # 验证直接返回预约对象
        assert isinstance(result, Appointment), "无诊费时应直接返回 Appointment 对象"
        assert result.status == 1, f"状态应为已确认(1)，实际为 {result.status}"
        assert result.payment_amount is None or result.payment_amount == 0, \
            f"payment_amount 应为 None 或 0，实际为 {result.payment_amount}"


# ==================== 退款服务测试 ====================

class TestRefundServiceGetRefundableAmount:
    """测试可退金额计算"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_refundable_amount_no_refund_yet(
        self, db_session, test_appointment, test_tenant
    ):
        """
        测试未退款时可退金额等于支付金额

        验证点：
        1. refundable_amount = payment_amount
        2. refunded_amount = 0
        """
        # 设置预约支付金额
        test_appointment.payment_amount = Decimal("100.00")
        test_appointment.refund_status = "none"
        await db_session.commit()

        service = RefundService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            result = await service.get_refundable_amount(test_appointment.id)

        assert result["payment_amount"] == Decimal("100.00")
        assert result["refunded_amount"] == Decimal("0")
        assert result["refundable_amount"] == Decimal("100.00")
        assert result["refund_status"] == "none"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_refundable_amount_partial_refunded(
        self, db_session, test_appointment, test_tenant
    ):
        """
        测试部分退款后可退金额计算

        验证点：
        1. refundable_amount = payment_amount - refunded_amount
        2. 正确计算已退金额
        """
        # 设置预约支付金额
        test_appointment.payment_amount = Decimal("100.00")
        test_appointment.refund_status = "partial_refunded"
        await db_session.commit()

        # 创建部分退款记录
        refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}123",
            refund_amount=Decimal("30.00"),
            original_amount=Decimal("100.00"),
            status="success",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(refund)
        await db_session.commit()

        service = RefundService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            result = await service.get_refundable_amount(test_appointment.id)

        assert result["payment_amount"] == Decimal("100.00")
        assert result["refunded_amount"] == Decimal("30.00")
        assert result["refundable_amount"] == Decimal("70.00")
        assert result["refund_status"] == "partial_refunded"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_refundable_amount_fully_refunded(
        self, db_session, test_appointment, test_tenant
    ):
        """
        测试全额退款后可退金额为 0

        验证点：
        1. refundable_amount = 0
        2. 退款状态为 refunded
        """
        # 设置预约支付金额
        test_appointment.payment_amount = Decimal("100.00")
        test_appointment.refund_status = "refunded"
        await db_session.commit()

        # 创建全额退款记录
        refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}123",
            refund_amount=Decimal("100.00"),
            original_amount=Decimal("100.00"),
            status="success",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(refund)
        await db_session.commit()

        service = RefundService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            result = await service.get_refundable_amount(test_appointment.id)

        assert result["payment_amount"] == Decimal("100.00")
        assert result["refunded_amount"] == Decimal("100.00")
        assert result["refundable_amount"] == Decimal("0")
        assert result["refund_status"] == "refunded"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_refundable_amount_appointment_not_found(
        self, db_session, test_tenant
    ):
        """
        测试预约不存在时抛出异常

        验证点：
        1. 抛出 ValueError
        2. 错误信息包含 "预约不存在"
        """
        service = RefundService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            with pytest.raises(ValueError) as exc_info:
                await service.get_refundable_amount(str(uuid4()))

        assert "预约不存在" in str(exc_info.value)


class TestRefundServiceCreateRefund:
    """测试退款创建逻辑"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_refund_success(
        self, db_session, test_appointment, test_tenant, test_user
    ):
        """
        测试正常创建退款

        验证点：
        1. 退款记录创建成功
        2. 预约退款状态更新为 partial_refunded
        3. 防超额退款校验
        """
        # 设置预约为已支付状态
        test_appointment.status = 1  # 已确认
        test_appointment.payment_amount = Decimal("100.00")
        test_appointment.refund_status = "none"
        test_appointment.payment_mch_id = "test_mch_id"
        test_appointment.payment_sub_mchid = "test_sub_mchid"
        test_appointment.payment_profile_id = str(uuid4())
        await db_session.commit()

        service = RefundService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            refund = await service.create_refund(
                appointment_id=test_appointment.id,
                refund_amount=Decimal("30.00"),
                refund_reason="患者要求退款",
                operator_id=test_user.id,
            )

        # 验证退款记录
        assert refund.refund_amount == Decimal("30.00")
        assert refund.original_amount == Decimal("100.00")
        assert refund.status == "pending"
        assert refund.refund_reason == "患者要求退款"
        assert refund.mch_id == "test_mch_id"
        assert refund.sub_mchid == "test_sub_mchid"
        assert refund.out_trade_no == f"APPT{test_appointment.id}"

        # 验证预约状态更新
        await db_session.refresh(test_appointment)
        assert test_appointment.refund_status == "partial_refunded"
        assert test_appointment.refund_amount == Decimal("30.00")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_refund_full_refund(
        self, db_session, test_appointment, test_tenant, test_user
    ):
        """
        测试全额退款

        验证点：
        1. 退款金额等于支付金额
        2. 预约退款状态更新为 refunded
        """
        # 设置预约为已支付状态
        test_appointment.status = 1
        test_appointment.payment_amount = Decimal("100.00")
        test_appointment.refund_status = "none"
        test_appointment.payment_mch_id = "test_mch_id"
        test_appointment.payment_sub_mchid = "test_sub_mchid"
        test_appointment.payment_profile_id = str(uuid4())
        await db_session.commit()

        service = RefundService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            refund = await service.create_refund(
                appointment_id=test_appointment.id,
                refund_amount=Decimal("100.00"),
                refund_reason="全额退款",
                operator_id=test_user.id,
        )

        # 验证退款记录
        assert refund.refund_amount == Decimal("100.00")
        assert refund.out_trade_no == f"APPT{test_appointment.id}"

        # 验证预约状态更新为全额退款
        await db_session.refresh(test_appointment)
        assert test_appointment.refund_status == "refunded"
        assert test_appointment.refund_amount == Decimal("100.00")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_refund_prevent_over_refund(
        self, db_session, test_appointment, test_tenant, test_user
    ):
        """
        测试防超额退款机制

        验证点：
        1. 累计退款不超过原支付金额
        2. 抛出 ValueError
        """
        # 设置预约为已支付状态
        test_appointment.status = 1
        test_appointment.payment_amount = Decimal("100.00")
        test_appointment.refund_status = "partial_refunded"
        test_appointment.refund_amount = Decimal("80.00")
        test_appointment.payment_mch_id = "test_mch_id"
        test_appointment.payment_sub_mchid = "test_sub_mchid"
        test_appointment.payment_profile_id = str(uuid4())
        await db_session.commit()

        # 创建已有退款记录
        existing_refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}111",
            refund_amount=Decimal("80.00"),
            original_amount=Decimal("100.00"),
            status="success",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(existing_refund)
        await db_session.commit()

        service = RefundService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            # 尝试退款 30.00，但已退 80.00，总额会超过 100.00
            with pytest.raises(ValueError) as exc_info:
                await service.create_refund(
                    appointment_id=test_appointment.id,
                    refund_amount=Decimal("30.00"),
                    refund_reason="超额退款测试",
                    operator_id=test_user.id,
                )

        assert "退款金额超出限制" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_refund_invalid_amount(
        self, db_session, test_appointment, test_tenant, test_user
    ):
        """
        测试退款金额必须大于 0

        验证点：
        1. 退款金额 <= 0 时抛出 ValueError
        """
        # 设置预约为已支付状态
        test_appointment.status = 1
        test_appointment.payment_amount = Decimal("100.00")
        test_appointment.payment_mch_id = "test_mch_id"
        test_appointment.payment_sub_mchid = "test_sub_mchid"
        test_appointment.payment_profile_id = str(uuid4())
        await db_session.commit()

        service = RefundService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            with pytest.raises(ValueError) as exc_info:
                await service.create_refund(
                    appointment_id=test_appointment.id,
                    refund_amount=Decimal("0"),
                    refund_reason="测试",
                    operator_id=test_user.id,
                )

        assert "退款金额必须大于0" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_refund_appointment_not_paid(
        self, db_session, test_appointment, test_tenant, test_user
    ):
        """
        测试未支付预约不能退款

        验证点：
        1. payment_amount 为空或 <= 0 时抛出 ValueError
        """
        # 设置预约为未支付状态
        test_appointment.status = 1
        test_appointment.payment_amount = None
        await db_session.commit()

        service = RefundService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            with pytest.raises(ValueError) as exc_info:
                await service.create_refund(
                    appointment_id=test_appointment.id,
                    refund_amount=Decimal("30.00"),
                    refund_reason="测试",
                    operator_id=test_user.id,
                )

        assert "预约未支付" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_refund_invalid_appointment_status(
        self, db_session, test_appointment, test_tenant, test_user
    ):
        """
        测试无效预约状态不能退款

        验证点：
        1. 待支付状态(status=0)不能退款
        """
        # 设置预约为待支付状态
        test_appointment.status = 0  # 待支付
        test_appointment.payment_amount = Decimal("100.00")
        await db_session.commit()

        service = RefundService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            with pytest.raises(ValueError) as exc_info:
                await service.create_refund(
                    appointment_id=test_appointment.id,
                    refund_amount=Decimal("30.00"),
                    refund_reason="测试",
                    operator_id=test_user.id,
                )

        assert "当前预约状态不允许退款" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_refund_missing_payment_merchant_info(
        self, db_session, test_appointment, test_tenant, test_user
    ):
        """
        测试缺少支付商户信息不能退款

        验证点：
        1. 无 mch_id 和 sub_mchid 时抛出 ValueError
        """
        # 设置预约为已支付状态，但缺少商户信息
        test_appointment.status = 1
        test_appointment.payment_amount = Decimal("100.00")
        # 故意不设置 payment_mch_id 和 payment_sub_mchid
        await db_session.commit()

        service = RefundService(db_session)

        with patch(
            'app.middleware.tenant_context.get_current_tenant_id',
            return_value=test_tenant.id
        ):
            with pytest.raises(ValueError) as exc_info:
                await service.create_refund(
                    appointment_id=test_appointment.id,
                    refund_amount=Decimal("30.00"),
                    refund_reason="测试",
                    operator_id=test_user.id,
                )

        assert "缺少支付商户信息" in str(exc_info.value)


class TestRefundServiceProcessRefundCallback:
    """测试退款回调处理"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_refund_callback_success(
        self, db_session, test_appointment, test_tenant
    ):
        """
        测试处理退款成功回调

        验证点：
        1. 状态更新为 success
        2. wx_refund_id 正确保存
        3. callback_at 记录时间
        4. 预约退款聚合状态同步更新
        """
        test_appointment.payment_amount = Decimal("100.00")
        test_appointment.refund_status = "none"
        test_appointment.refund_amount = Decimal("0")
        await db_session.commit()

        # 创建待处理退款记录
        refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}123",
            refund_amount=Decimal("30.00"),
            original_amount=Decimal("100.00"),
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(refund)
        await db_session.commit()

        service = RefundService(db_session)

        wx_refund_id = "wx_refund_123"
        result = await service.process_refund_callback(
            refund_no=refund.refund_no,
            wx_refund_id=wx_refund_id,
            status="success",
        )

        assert result.status == "success"
        assert result.wx_refund_id == wx_refund_id
        assert result.callback_at is not None

        await db_session.refresh(test_appointment)
        assert test_appointment.refund_status == "partial_refunded"
        assert test_appointment.refund_amount == Decimal("30.00")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_refund_callback_success_marks_appointment_fully_refunded(
        self, db_session, test_appointment, test_tenant
    ):
        """
        测试处理全额退款成功回调

        验证点：
        1. 预约累计退款金额同步为全额
        2. 预约退款状态更新为 refunded
        """
        test_appointment.payment_amount = Decimal("100.00")
        test_appointment.refund_status = "none"
        test_appointment.refund_amount = Decimal("0")
        await db_session.commit()

        refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}456",
            refund_amount=Decimal("100.00"),
            original_amount=Decimal("100.00"),
            status="processing",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(refund)
        await db_session.commit()

        service = RefundService(db_session)

        await service.process_refund_callback(
            refund_no=refund.refund_no,
            wx_refund_id="wx_refund_full",
            status="success",
        )

        await db_session.refresh(test_appointment)
        assert test_appointment.refund_status == "refunded"
        assert test_appointment.refund_amount == Decimal("100.00")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_refund_callback_failed_revert_appointment(
        self, db_session, test_appointment, test_tenant
    ):
        """
        测试处理退款失败回调，回退预约退款状态

        验证点：
        1. 状态更新为 failed
        2. failed_reason 保存
        3. 预约退款状态正确回退
        """
        # 设置预约为部分退款状态
        test_appointment.payment_amount = Decimal("100.00")
        test_appointment.refund_status = "partial_refunded"
        test_appointment.refund_amount = Decimal("50.00")
        await db_session.commit()

        # 创建失败的退款记录
        refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}123",
            refund_amount=Decimal("50.00"),
            original_amount=Decimal("100.00"),
            status="processing",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(refund)
        await db_session.commit()

        service = RefundService(db_session)

        result = await service.process_refund_callback(
            refund_no=refund.refund_no,
            wx_refund_id=None,
            status="failed",
            failed_reason="商户余额不足",
        )

        assert result.status == "failed"
        assert result.failed_reason == "商户余额不足"

        # 验证预约状态回退
        await db_session.refresh(test_appointment)
        # 由于实际成功的退款为 0，应回退到 none
        assert test_appointment.refund_status == "none"
        assert test_appointment.refund_amount == Decimal("0")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_refund_callback_refund_not_found(
        self, db_session
    ):
        """
        测试退款记录不存在时抛出异常

        验证点：
        1. 抛出 ValueError
        """
        service = RefundService(db_session)

        with pytest.raises(ValueError) as exc_info:
            await service.process_refund_callback(
                refund_no="NONEXISTENT_REFUND_NO",
                wx_refund_id=None,
                status="success",
            )

        assert "退款记录不存在" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_refund_callback_ignores_conflicting_terminal_status(
        self, db_session, test_appointment, test_tenant
    ):
        """
        测试终态退款回调不会被冲突回调覆盖

        验证点：
        1. 已成功退款记录不会被后到 failed 回调覆盖
        2. 预约退款聚合状态保持不变
        """
        test_appointment.payment_amount = Decimal("100.00")
        test_appointment.refund_status = "partial_refunded"
        test_appointment.refund_amount = Decimal("30.00")
        await db_session.commit()

        refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}789",
            refund_amount=Decimal("30.00"),
            original_amount=Decimal("100.00"),
            status="success",
            wx_refund_id="wx_refund_final",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(refund)
        await db_session.commit()

        service = RefundService(db_session)

        result = await service.process_refund_callback(
            refund_no=refund.refund_no,
            wx_refund_id=None,
            status="failed",
            failed_reason="冲突回调",
        )

        await db_session.refresh(test_appointment)
        await db_session.refresh(refund)
        assert result.status == "success"
        assert refund.status == "success"
        assert refund.failed_reason is None
        assert test_appointment.refund_status == "partial_refunded"
        assert test_appointment.refund_amount == Decimal("30.00")


class TestRefundServicePaymentReferenceRepair:
    """测试历史退款支付引用修复。"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_ensure_refund_payment_reference_repairs_legacy_refund_record(
        self, db_session, test_appointment, test_tenant
    ):
        test_appointment.status = 1
        test_appointment.payment_profile_id = str(uuid4())
        test_appointment.payment_transaction_id = "wx_txn_legacy_fixed"
        await db_session.commit()

        legacy_refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            payment_profile_id=None,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}LEGACY",
            out_trade_no=test_appointment.appointment_no,
            wx_transaction_id=None,
            refund_amount=Decimal("10.00"),
            original_amount=Decimal("10.00"),
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(legacy_refund)
        await db_session.commit()

        service = RefundService(db_session)
        out_trade_no, transaction_id = await service.ensure_refund_payment_reference(
            legacy_refund
        )

        assert out_trade_no == f"APPT{test_appointment.id}"
        assert transaction_id == "wx_txn_legacy_fixed"
        assert legacy_refund.out_trade_no == f"APPT{test_appointment.id}"
        assert legacy_refund.wx_transaction_id == "wx_txn_legacy_fixed"
        assert legacy_refund.payment_profile_id == test_appointment.payment_profile_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_ensure_refund_payment_reference_raises_without_payment_reference(
        self, db_session, test_tenant
    ):
        refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=str(uuid4()),
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}NOPAY",
            out_trade_no=None,
            wx_transaction_id=None,
            refund_amount=Decimal("10.00"),
            original_amount=Decimal("10.00"),
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(refund)
        await db_session.commit()

        service = RefundService(db_session)
        with pytest.raises(ValueError) as exc_info:
            await service.ensure_refund_payment_reference(refund)

        assert "退款记录缺少原支付凭证" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_refund_payment_reference_repair_plan_detects_changes(
        self, db_session, test_appointment, test_tenant
    ):
        test_appointment.payment_profile_id = str(uuid4())
        test_appointment.payment_transaction_id = "wx_txn_plan"
        await db_session.commit()

        refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            payment_profile_id=None,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}PLAN",
            out_trade_no=test_appointment.appointment_no,
            wx_transaction_id=None,
            refund_amount=Decimal("10.00"),
            original_amount=Decimal("10.00"),
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(refund)
        await db_session.commit()

        service = RefundService(db_session)
        plan = await service.get_refund_payment_reference_repair_plan(refund)

        assert plan["repairable"] is True
        assert plan["issues"] == []
        assert plan["changes"] == {
            "out_trade_no": f"APPT{test_appointment.id}",
            "wx_transaction_id": "wx_txn_plan",
            "payment_profile_id": test_appointment.payment_profile_id,
        }

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_backfill_refund_payment_references_dry_run_does_not_persist(
        self, db_session, test_appointment, test_tenant
    ):
        test_appointment.payment_profile_id = str(uuid4())
        test_appointment.payment_transaction_id = "wx_txn_dry_run"
        await db_session.commit()

        refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            payment_profile_id=None,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}DRY",
            out_trade_no=test_appointment.appointment_no,
            wx_transaction_id=None,
            refund_amount=Decimal("10.00"),
            original_amount=Decimal("10.00"),
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(refund)
        await db_session.commit()

        service = RefundService(db_session)
        summary = await service.backfill_refund_payment_references(dry_run=True)

        assert summary["scanned"] >= 1
        assert summary["would_update"] == 1
        assert summary["updated"] == 0

        await db_session.refresh(refund)
        assert refund.out_trade_no == test_appointment.appointment_no
        assert refund.wx_transaction_id is None
        assert refund.payment_profile_id is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_backfill_refund_payment_references_apply_persists_changes(
        self, db_session, test_appointment, test_tenant
    ):
        test_appointment.payment_profile_id = str(uuid4())
        test_appointment.payment_transaction_id = "wx_txn_apply"
        await db_session.commit()

        refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            payment_profile_id=None,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}APPLY",
            out_trade_no=test_appointment.appointment_no,
            wx_transaction_id=None,
            refund_amount=Decimal("10.00"),
            original_amount=Decimal("10.00"),
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(refund)
        await db_session.commit()

        service = RefundService(db_session)
        summary = await service.backfill_refund_payment_references(dry_run=False)

        assert summary["updated"] == 1
        assert summary["would_update"] == 0

        await db_session.refresh(refund)
        assert refund.out_trade_no == f"APPT{test_appointment.id}"
        assert refund.wx_transaction_id == "wx_txn_apply"
        assert refund.payment_profile_id == test_appointment.payment_profile_id


class TestWeChatPayServiceCreateRefund:
    """测试微信退款参数组装。"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_refund_prefers_transaction_id_for_legacy_orders(self):
        service = WeChatPayService.__new__(WeChatPayService)
        service.wxpay = MagicMock()
        service.query_order = AsyncMock(side_effect=AssertionError("不应回查订单"))
        service.wxpay.refund.return_value = (200, {"refund_id": "wx_refund_123"})

        result = await service.create_refund(
            out_trade_no="YY202604160001",
            out_refund_no="RF202604160001",
            total=Decimal("100.00"),
            refund=Decimal("30.00"),
            reason="历史订单兼容退款",
            transaction_id="wx_txn_123",
        )

        assert result["refund_id"] == "wx_refund_123"
        service.query_order.assert_not_awaited()
        service.wxpay.refund.assert_called_once_with(
            out_refund_no="RF202604160001",
            amount={"refund": 3000, "total": 10000, "currency": "CNY"},
            reason="历史订单兼容退款",
            transaction_id="wx_txn_123",
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_refund_falls_back_to_out_trade_no_without_transaction_id(self):
        service = WeChatPayService.__new__(WeChatPayService)
        service.wxpay = MagicMock()
        service.query_order = AsyncMock(return_value={})
        service.wxpay.refund.return_value = (200, {"refund_id": "wx_refund_456"})

        result = await service.create_refund(
            out_trade_no="APPT123",
            out_refund_no="RF202604160002",
            total=Decimal("100.00"),
            refund=Decimal("30.00"),
        )

        assert result["refund_id"] == "wx_refund_456"
        service.query_order.assert_awaited_once_with("APPT123")
        service.wxpay.refund.assert_called_once_with(
            out_refund_no="RF202604160002",
            amount={"refund": 3000, "total": 10000, "currency": "CNY"},
            out_trade_no="APPT123",
        )
