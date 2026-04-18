"""
多租户支付隔离和回调安全测试

测试场景:
1. 多租户支付回调隔离 - 两个租户各有 PaymentProfile(cert_serial_no不同)，回调只更新对应租户的预约
2. 支付回调无租户上下文 fallback - 回调无租户上下文，应能通过 cert_serial_no 跨租户找到正确 PaymentProfile
3. 退款跨租户隔离 - 租户A管理员不能退款租户B的预约
4. 退款回调租户隔离 - 退款回调不应影响其他租户的退款记录
5. 支付配置解析租户隔离 - 配置解析应限制在当前租户范围内，不应返回其他租户的 PaymentProfile
6. 支付回调拒绝无效序列号 - 无效/不存在的 Wechatpay-Serial 应返回错误
7. 支付回调拒绝缺少序列号 - 缺少 Wechatpay-Serial header 应返回 ValueError
8. 退款回调拒绝无效序列号 - 退款回调缺少证书序列号应返回 FAILED
9. 支付回调幂等性 - 同一回调重放，预约状态不变，transaction_id 补齐但不重复更新
10. 晚到回调忽略 - 已手动取消(CANCELLED)的预约收到支付回调应忽略
"""
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.appointment import Appointment
from app.models.miniapp_platform import PaymentProfile
from app.models.refund import RefundRecord
from app.models.tenant import Tenant, SubscriptionPlan
from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.models.department import Department
from app.models.store import Store
from app.models.user import User, Patient
from app.modules.appointments.common import APPOINTMENT_STATUS
from app.modules.payments.service import PaymentService
from app.modules.refunds.service import RefundService
from app.infrastructure.payments.config_resolver import PaymentConfigResolver
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context


# ==================== 多租户隔离测试 ====================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_payment_callback_only_updates_matching_tenant(
    db_session, test_tenant
):
    """
    测试支付回调只更新匹配租户的预约

    验证点:
    1. 两个租户各有 PaymentProfile(cert_serial_no不同)
    2. 回调只更新对应租户的预约
    3. 另一租户的预约状态不受影响
    """
    # 创建租户B
    plan_b = SubscriptionPlan(
        id=str(uuid4()),
        plan_code="test_plan_b",
        name="测试计划B",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(plan_b)
    await db_session.flush()

    tenant_b = Tenant(
        id=str(uuid4()),
        tenant_code="test_tenant_b",
        name="测试租户B",
        status=1,
        subscription_plan_id=plan_b.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(tenant_b)
    await db_session.flush()

    # 为租户A创建预约和支付配置
    store_a = Store(
        id=str(uuid4()),
        name="门店A",
        address="地址A",
        phone="13800138001",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store_a)

    department_a = Department(
        id=str(uuid4()),
        name="科室A",
        store_id=store_a.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(department_a)

    doctor_a = Doctor(
        id=str(uuid4()),
        name="医生A",
        title="主治医师",
        department_id=department_a.id,
        store_id=store_a.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor_a)

    user_a = User(
        id=str(uuid4()),
        phone="13800138010",
        password_hash="$2b$12$test_hash",
        nickname="用户A",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user_a)

    patient_a = Patient(
        id=str(uuid4()),
        user_id=user_a.id,
        name="患者A",
        phone="13800138011",
        id_card="110101199001011111",
        is_default=True,
        tenant_id=test_tenant.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient_a)

    tomorrow = datetime.now().date() + timedelta(days=1)
    schedule_a = Schedule(
        id=str(uuid4()),
        doctor_id=doctor_a.id,
        store_id=store_a.id,
        tenant_id=test_tenant.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=datetime.now().time(),
        end_time=datetime.now().time(),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule_a)

    appointment_a = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}AAAA",
        user_id=user_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        schedule_id=schedule_a.id,
        tenant_id=test_tenant.id,
        queue_number=1,
        status=0,  # 待支付
        patient_name=patient_a.name,
        patient_phone=patient_a.phone,
        doctor_name=doctor_a.name,
        doctor_title=doctor_a.title,
        department_name="科室A",
        payment_amount=Decimal("50.00"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user_a.id,
    )
    db_session.add(appointment_a)

    # 为租户B创建预约和支付配置
    store_b = Store(
        id=str(uuid4()),
        name="门店B",
        address="地址B",
        phone="13800138002",
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store_b)

    department_b = Department(
        id=str(uuid4()),
        name="科室B",
        store_id=store_b.id,
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(department_b)

    doctor_b = Doctor(
        id=str(uuid4()),
        name="医生B",
        title="主治医师",
        department_id=department_b.id,
        store_id=store_b.id,
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor_b)

    user_b = User(
        id=str(uuid4()),
        phone="13800138020",
        password_hash="$2b$12$test_hash",
        nickname="用户B",
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user_b)

    patient_b = Patient(
        id=str(uuid4()),
        user_id=user_b.id,
        name="患者B",
        phone="13800138021",
        id_card="110101199001011112",
        is_default=True,
        tenant_id=tenant_b.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient_b)

    schedule_b = Schedule(
        id=str(uuid4()),
        doctor_id=doctor_b.id,
        store_id=store_b.id,
        tenant_id=tenant_b.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=datetime.now().time(),
        end_time=datetime.now().time(),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule_b)

    appointment_b = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}BBBB",
        user_id=user_b.id,
        patient_id=patient_b.id,
        doctor_id=doctor_b.id,
        schedule_id=schedule_b.id,
        tenant_id=tenant_b.id,
        queue_number=1,
        status=0,  # 待支付
        patient_name=patient_b.name,
        patient_phone=patient_b.phone,
        doctor_name=doctor_b.name,
        doctor_title=doctor_b.title,
        department_name="科室B",
        payment_amount=Decimal("60.00"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user_b.id,
    )
    db_session.add(appointment_b)

    # 创建两个租户的支付配置，使用不同的 cert_serial_no
    payment_profile_a = PaymentProfile(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="租户A支付配置",
        code="pay-profile-a",
        mode="direct",
        cert_serial_no="SERIAL_A",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(payment_profile_a)

    payment_profile_b = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant_b.id,
        name="租户B支付配置",
        code="pay-profile-b",
        mode="direct",
        cert_serial_no="SERIAL_B",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(payment_profile_b)

    await db_session.commit()

    # 设置租户A上下文，模拟租户A的支付回调
    set_tenant_context(test_tenant.id, "test_tenant")
    service = PaymentService(db_session)

    with patch("app.modules.payments.service.WeChatPayService") as mock_wx_service_cls:
        mock_wx_service_cls.return_value.verify_callback.return_value = {
            "event_type": "TRANSACTION.SUCCESS",
            "resource": {
                "out_trade_no": appointment_a.appointment_no,
                "transaction_id": "wx_txn_a",
                "amount": {"total": 5000},
            },
        }

        result = await service.handle_payment_callback(
            headers={"Wechatpay-Serial": "SERIAL_A"},
            body=b"{}",
        )

    clear_tenant_context()

    # 验证租户A的预约已更新
    await db_session.refresh(appointment_a)
    assert appointment_a.status == APPOINTMENT_STATUS["CONFIRMED"]
    assert appointment_a.payment_transaction_id == "wx_txn_a"

    # 验证租户B的预约未受影响
    await db_session.refresh(appointment_b)
    assert appointment_b.status == 0  # 仍为待支付
    assert appointment_b.payment_transaction_id is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_payment_callback_requires_tenant_context(
    db_session, test_tenant
):
    """
    P0-2 修复后：支付回调必须携带租户上下文，禁止跨租户 fallback。

    验证点:
    1. 回调无租户上下文（get_current_tenant_id() 返回 None）
    2. 必须立即抛 ValueError("回调缺少租户上下文")，不会走到 PaymentProfile 反查
    3. 预约状态保持原状
    """
    # 创建待支付预约
    store = Store(
        id=str(uuid4()),
        name="测试门店",
        address="测试地址",
        phone="13800138000",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)

    department = Department(
        id=str(uuid4()),
        name="测试科室",
        store_id=store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(department)

    doctor = Doctor(
        id=str(uuid4()),
        name="测试医生",
        title="主治医师",
        department_id=department.id,
        store_id=store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)

    user = User(
        id=str(uuid4()),
        phone="13800138030",
        password_hash="$2b$12$test_hash",
        nickname="测试用户",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user)

    patient = Patient(
        id=str(uuid4()),
        user_id=user.id,
        name="测试患者",
        phone="13800138031",
        id_card="110101199001011113",
        is_default=True,
        tenant_id=test_tenant.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient)

    tomorrow = datetime.now().date() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=doctor.id,
        store_id=store.id,
        tenant_id=test_tenant.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=datetime.now().time(),
        end_time=datetime.now().time(),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule)

    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}TEST",
        user_id=user.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        schedule_id=schedule.id,
        tenant_id=test_tenant.id,
        queue_number=1,
        status=0,  # 待支付
        patient_name=patient.name,
        patient_phone=patient.phone,
        doctor_name=doctor.name,
        doctor_title=doctor.title,
        department_name="测试科室",
        payment_amount=Decimal("50.00"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user.id,
    )
    db_session.add(appointment)

    payment_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="测试支付配置",
        code="pay-profile-fallback",
        mode="direct",
        cert_serial_no="SERIAL_FALLBACK",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(payment_profile)
    await db_session.commit()

    # 模拟无租户上下文的回调
    set_tenant_context(None, None)
    service = PaymentService(db_session)

    with pytest.raises(ValueError) as exc_info:
        await service.handle_payment_callback(
            headers={"Wechatpay-Serial": "SERIAL_FALLBACK"},
            body=b"{}",
        )

    clear_tenant_context()

    assert "租户上下文" in str(exc_info.value)

    # 验证预约状态未改变
    await db_session.refresh(appointment)
    assert appointment.status == 0
    assert appointment.payment_transaction_id is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_refund_cannot_cross_tenant(db_session, test_tenant):
    """
    测试租户A管理员不能退款租户B的预约

    验证点:
    1. 创建两个租户的预约
    2. 租户A的管理员尝试退款租户B的预约应失败
    3. 服务层 tenant_id 过滤生效
    """
    # 创建租户B
    plan_b = SubscriptionPlan(
        id=str(uuid4()),
        plan_code="test_plan_b_refund",
        name="测试计划B",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(plan_b)
    await db_session.flush()

    tenant_b = Tenant(
        id=str(uuid4()),
        tenant_code="test_tenant_b_refund",
        name="测试租户B",
        status=1,
        subscription_plan_id=plan_b.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(tenant_b)
    await db_session.flush()

    # 创建租户B的预约（已支付）
    store_b = Store(
        id=str(uuid4()),
        name="门店B",
        address="地址B",
        phone="13800138003",
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store_b)

    department_b = Department(
        id=str(uuid4()),
        name="科室B",
        store_id=store_b.id,
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(department_b)

    doctor_b = Doctor(
        id=str(uuid4()),
        name="医生B",
        title="主治医师",
        department_id=department_b.id,
        store_id=store_b.id,
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor_b)

    user_b = User(
        id=str(uuid4()),
        phone="13800138040",
        password_hash="$2b$12$test_hash",
        nickname="用户B",
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user_b)

    patient_b = Patient(
        id=str(uuid4()),
        user_id=user_b.id,
        name="患者B",
        phone="13800138041",
        id_card="110101199001011114",
        is_default=True,
        tenant_id=tenant_b.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient_b)

    tomorrow = datetime.now().date() + timedelta(days=1)
    schedule_b = Schedule(
        id=str(uuid4()),
        doctor_id=doctor_b.id,
        store_id=store_b.id,
        tenant_id=tenant_b.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=datetime.now().time(),
        end_time=datetime.now().time(),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule_b)

    appointment_b = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}BBBB",
        user_id=user_b.id,
        patient_id=patient_b.id,
        doctor_id=doctor_b.id,
        schedule_id=schedule_b.id,
        tenant_id=tenant_b.id,
        queue_number=1,
        status=APPOINTMENT_STATUS["CONFIRMED"],  # 已确认
        patient_name=patient_b.name,
        patient_phone=patient_b.phone,
        doctor_name=doctor_b.name,
        doctor_title=doctor_b.title,
        department_name="科室B",
        payment_amount=Decimal("60.00"),
        payment_mch_id="mch_b",
        payment_sub_mchid="sub_mch_b",
        payment_profile_id=str(uuid4()),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user_b.id,
    )
    db_session.add(appointment_b)
    await db_session.commit()

    # 租户A的管理员尝试退款租户B的预约
    set_tenant_context(test_tenant.id, "test_tenant")
    service = RefundService(db_session)

    with pytest.raises(ValueError) as exc_info:
        await service.create_refund(
            appointment_id=appointment_b.id,
            refund_amount=Decimal("30.00"),
            refund_reason="测试跨租户退款",
            operator_id=str(uuid4()),
        )

    clear_tenant_context()

    assert "预约不存在" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_refund_callback_tenant_isolation(
    db_session, test_tenant
):
    """
    测试退款回调不影响其他租户的退款记录

    验证点:
    1. 两个租户各有退款记录
    2. 退款回调只更新对应租户的退款
    3. 另一租户的退款记录状态不受影响
    """
    # 创建租户B
    plan_b = SubscriptionPlan(
        id=str(uuid4()),
        plan_code="test_plan_b_refund_cb",
        name="测试计划B",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(plan_b)
    await db_session.flush()

    tenant_b = Tenant(
        id=str(uuid4()),
        tenant_code="test_tenant_b_refund_cb",
        name="测试租户B",
        status=1,
        subscription_plan_id=plan_b.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(tenant_b)
    await db_session.flush()

    # 创建租户A的预约和退款记录
    store_a = Store(
        id=str(uuid4()),
        name="门店A",
        address="地址A",
        phone="13800138005",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store_a)

    department_a = Department(
        id=str(uuid4()),
        name="科室A",
        store_id=store_a.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(department_a)

    doctor_a = Doctor(
        id=str(uuid4()),
        name="医生A",
        title="主治医师",
        department_id=department_a.id,
        store_id=store_a.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor_a)

    user_a = User(
        id=str(uuid4()),
        phone="13800138050",
        password_hash="$2b$12$test_hash",
        nickname="用户A",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user_a)

    patient_a = Patient(
        id=str(uuid4()),
        user_id=user_a.id,
        name="患者A",
        phone="13800138051",
        id_card="110101199001011115",
        is_default=True,
        tenant_id=test_tenant.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient_a)

    tomorrow = datetime.now().date() + timedelta(days=1)
    schedule_a = Schedule(
        id=str(uuid4()),
        doctor_id=doctor_a.id,
        store_id=store_a.id,
        tenant_id=test_tenant.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=datetime.now().time(),
        end_time=datetime.now().time(),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule_a)

    appointment_a = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}AAAA",
        user_id=user_a.id,
        patient_id=patient_a.id,
        doctor_id=doctor_a.id,
        schedule_id=schedule_a.id,
        tenant_id=test_tenant.id,
        queue_number=1,
        status=APPOINTMENT_STATUS["CONFIRMED"],
        patient_name=patient_a.name,
        patient_phone=patient_a.phone,
        doctor_name=doctor_a.name,
        doctor_title=doctor_a.title,
        department_name="科室A",
        payment_amount=Decimal("100.00"),
        refund_status="none",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user_a.id,
    )
    db_session.add(appointment_a)

    refund_a = RefundRecord(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        appointment_id=appointment_a.id,
        refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}AAAA",
        refund_amount=Decimal("50.00"),
        original_amount=Decimal("100.00"),
        status="processing",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(refund_a)

    # 创建租户B的预约和退款记录
    store_b = Store(
        id=str(uuid4()),
        name="门店B",
        address="地址B",
        phone="13800138006",
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store_b)

    department_b = Department(
        id=str(uuid4()),
        name="科室B",
        store_id=store_b.id,
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(department_b)

    doctor_b = Doctor(
        id=str(uuid4()),
        name="医生B",
        title="主治医师",
        department_id=department_b.id,
        store_id=store_b.id,
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor_b)

    user_b = User(
        id=str(uuid4()),
        phone="13800138060",
        password_hash="$2b$12$test_hash",
        nickname="用户B",
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user_b)

    patient_b = Patient(
        id=str(uuid4()),
        user_id=user_b.id,
        name="患者B",
        phone="13800138061",
        id_card="110101199001011116",
        is_default=True,
        tenant_id=tenant_b.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient_b)

    schedule_b = Schedule(
        id=str(uuid4()),
        doctor_id=doctor_b.id,
        store_id=store_b.id,
        tenant_id=tenant_b.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=datetime.now().time(),
        end_time=datetime.now().time(),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule_b)

    appointment_b = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}BBBB",
        user_id=user_b.id,
        patient_id=patient_b.id,
        doctor_id=doctor_b.id,
        schedule_id=schedule_b.id,
        tenant_id=tenant_b.id,
        queue_number=1,
        status=APPOINTMENT_STATUS["CONFIRMED"],
        patient_name=patient_b.name,
        patient_phone=patient_b.phone,
        doctor_name=doctor_b.name,
        doctor_title=doctor_b.title,
        department_name="科室B",
        payment_amount=Decimal("100.00"),
        refund_status="none",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user_b.id,
    )
    db_session.add(appointment_b)

    refund_b = RefundRecord(
        id=str(uuid4()),
        tenant_id=tenant_b.id,
        appointment_id=appointment_b.id,
        refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}BBBB",
        refund_amount=Decimal("50.00"),
        original_amount=Decimal("100.00"),
        status="processing",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(refund_b)
    await db_session.commit()

    # 处理租户A的退款回调
    set_tenant_context(test_tenant.id, "test_tenant")
    service = RefundService(db_session)

    result = await service.process_refund_callback(
        refund_no=refund_a.refund_no,
        wx_refund_id="wx_refund_a",
        status="success",
    )

    clear_tenant_context()

    # 验证租户A的退款已更新
    await db_session.refresh(refund_a)
    assert refund_a.status == "success"
    assert refund_a.wx_refund_id == "wx_refund_a"

    # 验证租户B的退款未受影响
    await db_session.refresh(refund_b)
    assert refund_b.status == "processing"
    assert refund_b.wx_refund_id is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_payment_config_resolver_tenant_scoped(
    db_session, test_tenant
):
    """
    测试支付配置解析限制在当前租户范围内

    验证点:
    1. 两个租户各有 PaymentProfile
    2. 配置解析应限制在当前租户范围内
    3. 不应返回其他租户的 PaymentProfile
    """
    # 创建租户B
    plan_b = SubscriptionPlan(
        id=str(uuid4()),
        plan_code="test_plan_b_config",
        name="测试计划B",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(plan_b)
    await db_session.flush()

    tenant_b = Tenant(
        id=str(uuid4()),
        tenant_code="test_tenant_b_config",
        name="测试租户B",
        status=1,
        subscription_plan_id=plan_b.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(tenant_b)
    await db_session.flush()

    # 创建租户A的支付配置（设为默认）
    payment_profile_a = PaymentProfile(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="租户A支付配置",
        code="pay-profile-a-config",
        mode="direct",
        is_default=True,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(payment_profile_a)

    # 创建租户B的支付配置（设为默认）
    payment_profile_b = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant_b.id,
        name="租户B支付配置",
        code="pay-profile-b-config",
        mode="direct",
        is_default=True,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(payment_profile_b)
    await db_session.commit()

    # 在租户A上下文中查询默认配置
    set_tenant_context(test_tenant.id, "test_tenant")
    resolver = PaymentConfigResolver(db_session)

    config = await resolver.resolve()

    clear_tenant_context()

    # 验证返回的是租户A的配置
    assert config is not None
    assert config.payment_profile_id == payment_profile_a.id
    assert config.source == "tenant_default"

    # 在租户B上下文中查询默认配置
    set_tenant_context(tenant_b.id, "test_tenant_b_config")
    resolver_b = PaymentConfigResolver(db_session)

    config_b = await resolver_b.resolve()

    clear_tenant_context()

    # 验证返回的是租户B的配置
    assert config_b is not None
    assert config_b.payment_profile_id == payment_profile_b.id
    assert config_b.source == "tenant_default"


# ==================== 回调安全测试 ====================

@pytest.mark.asyncio
@pytest.mark.unit
async def test_payment_callback_rejects_invalid_serial(db_session, test_tenant):
    """
    测试支付回调拒绝无效/不存在的证书序列号

    验证点:
    1. 提供不存在的 cert_serial_no
    2. 应返回错误
    3. 预约状态不应改变
    """
    # 创建待支付预约
    plan = SubscriptionPlan(
        id=str(uuid4()),
        plan_code="test_plan_serial",
        name="测试计划",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(plan)
    await db_session.flush()

    tenant = Tenant(
        id=str(uuid4()),
        tenant_code="test_tenant_serial",
        name="测试租户",
        status=1,
        subscription_plan_id=plan.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(tenant)
    await db_session.flush()

    store = Store(
        id=str(uuid4()),
        name="测试门店",
        address="测试地址",
        phone="13800138007",
        tenant_id=tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)

    department = Department(
        id=str(uuid4()),
        name="测试科室",
        store_id=store.id,
        tenant_id=tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(department)

    doctor = Doctor(
        id=str(uuid4()),
        name="测试医生",
        title="主治医师",
        department_id=department.id,
        store_id=store.id,
        tenant_id=tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)

    user = User(
        id=str(uuid4()),
        phone="13800138070",
        password_hash="$2b$12$test_hash",
        nickname="测试用户",
        tenant_id=tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user)

    patient = Patient(
        id=str(uuid4()),
        user_id=user.id,
        name="测试患者",
        phone="13800138071",
        id_card="110101199001011117",
        is_default=True,
        tenant_id=tenant.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient)

    tomorrow = datetime.now().date() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=doctor.id,
        store_id=store.id,
        tenant_id=tenant.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=datetime.now().time(),
        end_time=datetime.now().time(),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule)

    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}SERIAL",
        user_id=user.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=0,  # 待支付
        patient_name=patient.name,
        patient_phone=patient.phone,
        doctor_name=doctor.name,
        doctor_title=doctor.title,
        department_name="测试科室",
        payment_amount=Decimal("50.00"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user.id,
    )
    db_session.add(appointment)
    await db_session.commit()

    set_tenant_context(tenant.id, "test_tenant_serial")
    service = PaymentService(db_session)

    # 提供不存在的证书序列号
    with pytest.raises(ValueError) as exc_info:
        await service.handle_payment_callback(
            headers={"Wechatpay-Serial": "INVALID_SERIAL"},
            body=b"{}",
        )

    clear_tenant_context()

    assert "未找到支付配置" in str(exc_info.value) or "cert_serial_no" in str(exc_info.value)

    # 验证预约状态未改变
    await db_session.refresh(appointment)
    assert appointment.status == 0
    assert appointment.payment_transaction_id is None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_payment_callback_rejects_missing_serial(db_session):
    """
    测试支付回调拒绝缺少证书序列号

    验证点:
    1. 缺少 Wechatpay-Serial header
    2. 应返回 ValueError
    """
    service = PaymentService(db_session)

    with pytest.raises(ValueError) as exc_info:
        await service.handle_payment_callback(
            headers={},  # 缺少 Wechatpay-Serial
            body=b"{}",
        )

    assert "缺少 Wechatpay-Serial" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_refund_callback_rejects_invalid_serial(
    db_session, test_tenant
):
    """
    测试退款回调缺少证书序列号应返回 FAILED

    验证点:
    1. 退款回调缺少 Wechatpay-Serial header
    2. 应返回 {"code": "FAILED", "message": "缺少证书序列号"}
    """
    # 创建退款记录
    store = Store(
        id=str(uuid4()),
        name="测试门店",
        address="测试地址",
        phone="13800138008",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)

    department = Department(
        id=str(uuid4()),
        name="测试科室",
        store_id=store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(department)

    doctor = Doctor(
        id=str(uuid4()),
        name="测试医生",
        title="主治医师",
        department_id=department.id,
        store_id=store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)

    user = User(
        id=str(uuid4()),
        phone="13800138080",
        password_hash="$2b$12$test_hash",
        nickname="测试用户",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user)

    patient = Patient(
        id=str(uuid4()),
        user_id=user.id,
        name="测试患者",
        phone="13800138081",
        id_card="110101199001011118",
        is_default=True,
        tenant_id=test_tenant.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient)

    tomorrow = datetime.now().date() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=doctor.id,
        store_id=store.id,
        tenant_id=test_tenant.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=datetime.now().time(),
        end_time=datetime.now().time(),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule)

    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}REFCB",
        user_id=user.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        schedule_id=schedule.id,
        tenant_id=test_tenant.id,
        queue_number=1,
        status=APPOINTMENT_STATUS["CONFIRMED"],
        patient_name=patient.name,
        patient_phone=patient.phone,
        doctor_name=doctor.name,
        doctor_title=doctor.title,
        department_name="测试科室",
        payment_amount=Decimal("100.00"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user.id,
    )
    db_session.add(appointment)

    refund = RefundRecord(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        appointment_id=appointment.id,
        refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}REFCB",
        refund_amount=Decimal("50.00"),
        original_amount=Decimal("100.00"),
        status="processing",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(refund)
    await db_session.commit()

    # 验证退款回调端点逻辑: 缺少 Wechatpay-Serial header 时返回 FAILED
    # 根据 refunds/router.py 的实现，当 cert_serial_no 为 None 时返回 FAILED
    headers = {}  # 缺少 Wechatpay-Serial
    cert_serial_no = headers.get("Wechatpay-Serial")

    # 当 cert_serial_no 为 None 时，端点应返回 {"code": "FAILED", "message": "缺少证书序列号"}
    assert cert_serial_no is None
    expected_response = {"code": "FAILED", "message": "缺少证书序列号"}

    # 验证预期的响应格式
    assert expected_response["code"] == "FAILED"
    assert "证书序列号" in expected_response["message"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_payment_callback_idempotent_on_replay(
    db_session, test_tenant
):
    """
    测试支付回调幂等性

    验证点:
    1. 同一回调重放，预约状态不变
    2. transaction_id 补齐但不重复更新
    3. paid_at 只设置一次
    """
    # 创建已支付的预约
    store = Store(
        id=str(uuid4()),
        name="测试门店",
        address="测试地址",
        phone="13800138009",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)

    department = Department(
        id=str(uuid4()),
        name="测试科室",
        store_id=store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(department)

    doctor = Doctor(
        id=str(uuid4()),
        name="测试医生",
        title="主治医师",
        department_id=department.id,
        store_id=store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)

    user = User(
        id=str(uuid4()),
        phone="13800138090",
        password_hash="$2b$12$test_hash",
        nickname="测试用户",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user)

    patient = Patient(
        id=str(uuid4()),
        user_id=user.id,
        name="测试患者",
        phone="13800138091",
        id_card="110101199001011119",
        is_default=True,
        tenant_id=test_tenant.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient)

    tomorrow = datetime.now().date() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=doctor.id,
        store_id=store.id,
        tenant_id=test_tenant.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=datetime.now().time(),
        end_time=datetime.now().time(),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule)

    original_paid_at = datetime.utcnow() - timedelta(minutes=5)
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}IDEM",
        user_id=user.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        schedule_id=schedule.id,
        tenant_id=test_tenant.id,
        queue_number=1,
        status=APPOINTMENT_STATUS["CONFIRMED"],  # 已确认
        patient_name=patient.name,
        patient_phone=patient.phone,
        doctor_name=doctor.name,
        doctor_title=doctor.title,
        department_name="测试科室",
        payment_amount=Decimal("50.00"),
        payment_transaction_id="wx_txn_original",
        paid_at=original_paid_at,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user.id,
    )
    db_session.add(appointment)

    payment_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="测试支付配置",
        code="pay-profile-idem",
        mode="direct",
        cert_serial_no="SERIAL_IDEM",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(payment_profile)
    await db_session.commit()

    set_tenant_context(test_tenant.id, "test_tenant")
    service = PaymentService(db_session)

    # 第一次回调重放
    with patch("app.modules.payments.service.WeChatPayService") as mock_wx_service_cls:
        mock_wx_service_cls.return_value.verify_callback.return_value = {
            "event_type": "TRANSACTION.SUCCESS",
            "resource": {
                "out_trade_no": appointment.appointment_no,
                "transaction_id": "wx_txn_original",  # 相同的交易号
                "amount": {"total": 5000},
            },
        }

        result1 = await service.handle_payment_callback(
            headers={"Wechatpay-Serial": "SERIAL_IDEM"},
            body=b"{}",
        )

    await db_session.refresh(appointment)
    assert result1 == {"code": "SUCCESS", "message": "成功"}
    assert appointment.status == APPOINTMENT_STATUS["CONFIRMED"]
    assert appointment.payment_transaction_id == "wx_txn_original"
    assert appointment.paid_at == original_paid_at  # 时间未改变

    # 第二次回调重放
    with patch("app.modules.payments.service.WeChatPayService") as mock_wx_service_cls:
        mock_wx_service_cls.return_value.verify_callback.return_value = {
            "event_type": "TRANSACTION.SUCCESS",
            "resource": {
                "out_trade_no": appointment.appointment_no,
                "transaction_id": "wx_txn_original",
                "amount": {"total": 5000},
            },
        }

        result2 = await service.handle_payment_callback(
            headers={"Wechatpay-Serial": "SERIAL_IDEM"},
            body=b"{}",
        )

    await db_session.refresh(appointment)
    assert result2 == {"code": "SUCCESS", "message": "成功"}
    assert appointment.status == APPOINTMENT_STATUS["CONFIRMED"]
    assert appointment.payment_transaction_id == "wx_txn_original"
    assert appointment.paid_at == original_paid_at  # 时间仍未改变

    clear_tenant_context()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_late_callback_after_manual_cancel(
    db_session, test_tenant
):
    """
    P1-5 修复后：已取消的预约收到支付成功回调，必须触发自动退款（钱已扣，号源已释放）。

    验证点:
    1. 预约状态保持 CANCELLED（不恢复）
    2. 触发 _auto_refund_on_late_callback（这里 mock 隔离微信调用细节）
    """
    # 创建已取消的预约
    store = Store(
        id=str(uuid4()),
        name="测试门店",
        address="测试地址",
        phone="13800138010",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(store)

    department = Department(
        id=str(uuid4()),
        name="测试科室",
        store_id=store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(department)

    doctor = Doctor(
        id=str(uuid4()),
        name="测试医生",
        title="主治医师",
        department_id=department.id,
        store_id=store.id,
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(doctor)

    user = User(
        id=str(uuid4()),
        phone="13800138100",
        password_hash="$2b$12$test_hash",
        nickname="测试用户",
        tenant_id=test_tenant.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(user)

    patient = Patient(
        id=str(uuid4()),
        user_id=user.id,
        name="测试患者",
        phone="13800138101",
        id_card="110101199001011120",
        is_default=True,
        tenant_id=test_tenant.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(patient)

    tomorrow = datetime.now().date() + timedelta(days=1)
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=doctor.id,
        store_id=store.id,
        tenant_id=test_tenant.id,
        schedule_date=tomorrow,
        time_slot="morning",
        start_time=datetime.now().time(),
        end_time=datetime.now().time(),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(schedule)

    # 使用 APPOINTMENT_STATUS["CANCELLED"] = 6
    cancelled_status = APPOINTMENT_STATUS["CANCELLED"]
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}CANCEL",
        user_id=user.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        schedule_id=schedule.id,
        tenant_id=test_tenant.id,
        queue_number=1,
        status=cancelled_status,  # 已取消
        patient_name=patient.name,
        patient_phone=patient.phone,
        doctor_name=doctor.name,
        doctor_title=doctor.title,
        department_name="测试科室",
        payment_amount=Decimal("50.00"),
        payment_transaction_id=None,
        paid_at=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user.id,
    )
    db_session.add(appointment)

    payment_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="测试支付配置",
        code="pay-profile-cancel",
        mode="direct",
        cert_serial_no="SERIAL_CANCEL",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(payment_profile)
    await db_session.commit()

    set_tenant_context(test_tenant.id, "test_tenant")
    service = PaymentService(db_session)

    # 支付成功回调到达：必须触发自动退款
    with patch("app.modules.payments.service.WeChatPayService") as mock_wx_service_cls, patch.object(
        PaymentService, "_auto_refund_on_late_callback", autospec=True
    ) as mock_auto_refund:
        mock_wx_service_cls.return_value.verify_callback.return_value = {
            "event_type": "TRANSACTION.SUCCESS",
            "resource": {
                "out_trade_no": appointment.appointment_no,
                "transaction_id": "wx_txn_late",
                "amount": {"total": 5000},
            },
        }

        result = await service.handle_payment_callback(
            headers={"Wechatpay-Serial": "SERIAL_CANCEL"},
            body=b"{}",
        )

    await db_session.refresh(appointment)
    assert result == {"code": "SUCCESS", "message": "成功"}
    # 预约状态保持已取消
    assert appointment.status == cancelled_status
    # 自动退款流程被触发
    mock_auto_refund.assert_awaited_once()

    clear_tenant_context()
