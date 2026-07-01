"""
支付服务核心逻辑单元测试

覆盖 PaymentService 的以下功能:
1. create_payment_order - 创建支付订单完整流程（happy path + 错误路径）
2. _get_appointment_by_out_trade_no - 商户订单号反查预约（新格式 + 历史 APPT 格式）
3. generate_out_trade_no - 商户订单号生成（payment_ordering 模块级纯函数）
4. handle_payment_callback 边界场景 - 非成功事件、金额不一致、out_trade_no 缺失

不覆盖（已在其他测试文件中覆盖）:
- _resolve_payment_config 优先级链 → test_payment_config_priority.py
- 回调幂等/过期自动退款 → test_payment_timeout.py
- 多租户隔离 → test_payment_tenant_isolation.py
- 退款服务 → test_payment_refund.py
"""
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.appointment import APPOINTMENT_STATUS
from app.infrastructure.payments.config_resolver import PaymentRoutingConfig
from app.models.appointment import Appointment
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.miniapp_platform import (
    PaymentProfile,
)
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.tenant import Tenant
from app.models.user import Patient, User
from app.modules.payments.payment_ordering import generate_out_trade_no
from app.modules.payments.service import PaymentService


# ==================== 辅助函数 ====================


def _make_tenant(db, code="test-tenant"):
    """创建租户和订阅计划"""
    from app.models.tenant import SubscriptionPlan

    plan = SubscriptionPlan(
        id=str(uuid4()),
        plan_code=f"plan_{uuid4().hex[:8]}",
        name="测试计划",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(plan)
    tenant = Tenant(
        id=str(uuid4()),
        tenant_code=code,
        name="测试租户",
        status=1,
        subscription_plan_id=plan.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(tenant)
    return tenant


def _make_store(db, tenant_id):
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant_id,
        name="测试门店",
        address="测试地址",
        phone="13800138000",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(store)
    return store


def _make_doctor(db, tenant_id, store_id, dept_id):
    doctor = Doctor(
        id=str(uuid4()),
        name="测试医生",
        title="主治医师",
        department_id=dept_id,
        store_id=store_id,
        tenant_id=tenant_id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(doctor)
    return doctor


def _make_department(db, tenant_id, store_id):
    dept = Department(
        id=str(uuid4()),
        name="测试科室",
        store_id=store_id,
        tenant_id=tenant_id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(dept)
    return dept


def _make_user(db, tenant_id):
    user = User(
        id=str(uuid4()),
        phone=f"138{uuid4().hex[:8]}",
        password_hash="$2b$12$test_hash",
        nickname="测试用户",
        tenant_id=tenant_id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(user)
    return user


def _make_patient(db, tenant_id, user_id):
    patient = Patient(
        id=str(uuid4()),
        user_id=user_id,
        name="测试就诊人",
        phone="13800138002",
        id_card="110101199001011234",
        is_default=True,
        tenant_id=tenant_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(patient)
    return patient


def _make_schedule(db, tenant_id, doctor_id, store_id):
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=doctor_id,
        store_id=store_id,
        tenant_id=tenant_id,
        schedule_date=date.today() + timedelta(days=1),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(schedule)
    return schedule


def _make_payment_profile(db, tenant_id, **overrides):
    defaults = dict(
        id=str(uuid4()),
        tenant_id=tenant_id,
        name="测试支付配置",
        code="test-pay-profile",
        mode="direct",
        app_id="wx_app_id",
        mch_id="1234567890",
        api_v3_key_ref="test_api_v3_key",
        private_key_ref="test_private_key",
        cert_serial_no="CERT_SERIAL_123",
        notify_url="https://example.com/notify",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    defaults.update(overrides)
    profile = PaymentProfile(**defaults)
    db.add(profile)
    return profile


def _make_appointment(db, tenant_id, schedule_id, user_id, patient_id, doctor_id, **overrides):
    appointment_no = overrides.pop("appointment_no", f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:4].upper()}")
    defaults = dict(
        id=str(uuid4()),
        appointment_no=appointment_no,
        user_id=user_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        schedule_id=schedule_id,
        tenant_id=tenant_id,
        queue_number=1,
        status=0,
        patient_name="测试就诊人",
        patient_phone="13800138002",
        doctor_name="测试医生",
        doctor_title="主治医师",
        department_name="测试科室",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=user_id,
    )
    defaults.update(overrides)
    appointment = Appointment(**defaults)
    db.add(appointment)
    return appointment


# ==================== TestPaymentService - create_payment_order ====================


class TestPaymentServiceCreatePaymentOrder:
    """测试 create_payment_order 的各种场景"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_payment_order_success(self, db_session: AsyncSession):
        """正常路径：完整创建支付订单流程"""
        tenant = _make_tenant(db_session, "tenant-create-ok")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)
        profile = _make_payment_profile(db_session, tenant.id)

        appointment = _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            status=0,
            payment_amount=Decimal("50.00"),
        )
        await db_session.commit()

        routing_config = PaymentRoutingConfig(
            payment_profile_id=profile.id,
            mode="direct",
            app_id="wx_app_id",
            mch_id="1234567890",
            sub_mchid=None,
            notify_url="https://example.com/notify",
            source="store_route",
        )

        service = PaymentService(db_session)

        fake_sign_params = {
            "timeStamp": "1700000000",
            "nonceStr": "abc123",
            "package": "prepay_id=wx_prepay_123",
            "signType": "RSA",
            "paySign": "fake_signature",
        }

        with patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id), \
             patch("app.modules.payments.service.WeChatPayService") as mock_wx_cls, \
             patch.object(service, "_resolve_payment_config", new_callable=AsyncMock, return_value=routing_config), \
             patch.object(service, "_generate_miniapp_pay_sign", return_value=fake_sign_params):
            mock_wx = MagicMock()
            mock_wx_cls.return_value = mock_wx
            mock_wx._load_secret.return_value = None
            mock_wx.create_order = AsyncMock(return_value={"prepay_id": "wx_prepay_123"})

            result = await service.create_payment_order(
                appointment_id=appointment.id,
                openid="test_openid",
            )

        assert result["appointment_id"] == appointment.id
        assert result["payment_amount"] == 50.0
        assert result["time_stamp"] == "1700000000"
        assert result["nonce_str"] == "abc123"
        assert result["package"] == "prepay_id=wx_prepay_123"
        assert result["sign_type"] == "RSA"
        assert result["pay_sign"] == "fake_signature"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_payment_order_appointment_not_found(self, db_session: AsyncSession):
        """预约不存在时应抛出 ValueError"""
        tenant = _make_tenant(db_session, "tenant-create-nf")
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            with pytest.raises(ValueError, match="预约不存在"):
                await service.create_payment_order(
                    appointment_id=str(uuid4()),
                    openid="test_openid",
                )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_payment_order_wrong_status(self, db_session: AsyncSession):
        """预约状态不是待支付(0)时应抛出 ValueError"""
        tenant = _make_tenant(db_session, "tenant-create-ws")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)

        appointment = _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            status=1,  # 已确认，非待支付
            payment_amount=Decimal("50.00"),
        )
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            with pytest.raises(ValueError, match="预约状态不正确"):
                await service.create_payment_order(
                    appointment_id=appointment.id,
                    openid="test_openid",
                )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_payment_order_zero_amount(self, db_session: AsyncSession):
        """预约金额为 0 时应抛出 ValueError"""
        tenant = _make_tenant(db_session, "tenant-create-za")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)

        appointment = _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            status=0,
            payment_amount=Decimal("0.00"),
        )
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            with pytest.raises(ValueError, match="预约金额无效"):
                await service.create_payment_order(
                    appointment_id=appointment.id,
                    openid="test_openid",
                )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_payment_order_no_payment_config(self, db_session: AsyncSession):
        """无法获取支付配置时应抛出 ValueError"""
        tenant = _make_tenant(db_session, "tenant-create-noconf")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)

        # 排班没有 store_id，且无其他支付配置来源
        schedule_no_store = Schedule(
            id=str(uuid4()),
            doctor_id=doctor.id,
            tenant_id=tenant.id,
            schedule_date=date.today() + timedelta(days=2),  # 不同日期避免 UNIQUE 冲突
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=0,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule_no_store)

        appointment = _make_appointment(
            db_session, tenant.id, schedule_no_store.id, user.id, patient.id, doctor.id,
            status=0,
            payment_amount=Decimal("50.00"),
        )
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            with pytest.raises(ValueError, match="无法获取支付配置"):
                await service.create_payment_order(
                    appointment_id=appointment.id,
                    openid="test_openid",
                )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_payment_order_no_prepay_id(self, db_session: AsyncSession):
        """微信下单未返回 prepay_id 时应抛出异常"""
        tenant = _make_tenant(db_session, "tenant-create-noprepay")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)
        profile = _make_payment_profile(db_session, tenant.id)

        appointment = _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            status=0,
            payment_amount=Decimal("50.00"),
        )
        await db_session.commit()

        routing_config = PaymentRoutingConfig(
            payment_profile_id=profile.id,
            mode="direct",
            app_id="wx_app_id",
            mch_id="1234567890",
            sub_mchid=None,
            notify_url="https://example.com/notify",
            source="store_route",
        )

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id), \
             patch("app.modules.payments.service.WeChatPayService") as mock_wx_cls, \
             patch.object(service, "_resolve_payment_config", new_callable=AsyncMock, return_value=routing_config):
            mock_wx = MagicMock()
            mock_wx_cls.return_value = mock_wx
            mock_wx._load_secret.return_value = None
            # 模拟微信下单返回中没有 prepay_id
            mock_wx.create_order = AsyncMock(return_value={"prepay_id": None})

            with pytest.raises(Exception, match="微信下单失败"):
                await service.create_payment_order(
                    appointment_id=appointment.id,
                    openid="test_openid",
                )


# ==================== TestPaymentServiceGetAppointmentByOutTradeNo ====================


class TestPaymentServiceGetAppointmentByOutTradeNo:
    """测试 _get_appointment_by_out_trade_no 的各种查找路径"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_by_appointment_no(self, db_session: AsyncSession):
        """通过 appointment_no 正常查找预约"""
        tenant = _make_tenant(db_session, "tenant-find-by-no")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)

        appointment = _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            appointment_no="YY20260101120000ABCD",
        )
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            result = await service._get_appointment_by_out_trade_no("YY20260101120000ABCD")

        assert result is not None
        assert result.id == appointment.id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_by_legacy_appt_prefix(self, db_session: AsyncSession):
        """通过历史 APPT{uuid} 格式查找预约"""
        tenant = _make_tenant(db_session, "tenant-find-legacy")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)

        appointment = _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            appointment_no="YY20260101120000EFXX",
        )
        await db_session.commit()

        legacy_trade_no = f"APPT{appointment.id}"
        service = PaymentService(db_session)

        with patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            result = await service._get_appointment_by_out_trade_no(legacy_trade_no)

        assert result is not None
        assert result.id == appointment.id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_not_found(self, db_session: AsyncSession):
        """不存在的订单号应返回 None"""
        tenant = _make_tenant(db_session, "tenant-find-nf")
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            result = await service._get_appointment_by_out_trade_no("NONEXISTENT_ORDER")

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_legacy_prefix_not_found(self, db_session: AsyncSession):
        """APPT{不存在的uuid} 应返回 None"""
        tenant = _make_tenant(db_session, "tenant-find-leg-nf")
        await db_session.commit()

        fake_id = str(uuid4())
        service = PaymentService(db_session)

        with patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            result = await service._get_appointment_by_out_trade_no(f"APPT{fake_id}")

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_find_tenant_isolation(self, db_session: AsyncSession):
        """跨租户查找应返回 None（租户隔离）"""
        tenant_a = _make_tenant(db_session, "tenant-a-iso")
        tenant_b = _make_tenant(db_session, "tenant-b-iso")

        store_b = _make_store(db_session, tenant_b.id)
        dept_b = _make_department(db_session, tenant_b.id, store_b.id)
        doctor_b = _make_doctor(db_session, tenant_b.id, store_b.id, dept_b.id)
        user_b = _make_user(db_session, tenant_b.id)
        patient_b = _make_patient(db_session, tenant_b.id, user_b.id)
        schedule_b = _make_schedule(db_session, tenant_b.id, doctor_b.id, store_b.id)

        _make_appointment(
            db_session, tenant_b.id, schedule_b.id, user_b.id, patient_b.id, doctor_b.id,
            appointment_no="YY20260101120000TNTB",
        )
        await db_session.commit()

        # 用租户A的上下文去查租户B的预约
        service = PaymentService(db_session)

        with patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant_a.id):
            result = await service._get_appointment_by_out_trade_no("YY20260101120000TNTB")

        assert result is None


# ==================== TestPaymentServiceGenerateOutTradeNo ====================


class TestPaymentServiceGenerateOutTradeNo:
    """测试 generate_out_trade_no 的生成逻辑"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_out_trade_no_uses_appointment_no(self, db_session: AsyncSession):
        """商户订单号应使用 appointment_no"""
        tenant = _make_tenant(db_session, "tenant-gen-ok")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)

        appointment = _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            appointment_no="YY20260401120000QRST",
        )
        await db_session.commit()

        result = generate_out_trade_no(appointment)

        assert result == "YY20260401120000QRST"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_out_trade_no_missing_appointment_no(self, db_session: AsyncSession):
        """缺少 appointment_no 时应抛出 ValueError

        注意：Appointment.appointment_no 是 nullable=False，
        无法在 DB 层创建 None 值的记录。使用 SimpleNamespace 模拟。
        """
        from types import SimpleNamespace

        fake_appointment = SimpleNamespace(
            id=str(uuid4()),
            appointment_no=None,  # 缺少 appointment_no
        )

        with pytest.raises(ValueError, match="预约缺少 appointment_no"):
            generate_out_trade_no(fake_appointment)


# ==================== TestPaymentServiceCallbackEdgeCases ====================


class TestPaymentServiceCallbackEdgeCases:
    """测试 handle_payment_callback 的边界场景"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_callback_non_success_event_ignored(self, db_session: AsyncSession):
        """非成功事件应被忽略并返回 SUCCESS"""
        tenant = _make_tenant(db_session, "tenant-cb-nsevt")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)
        _make_payment_profile(db_session, tenant.id, cert_serial_no="SERIAL_NSEVT")

        appointment = _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            status=0,
            payment_amount=Decimal("50.00"),
        )
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.WeChatPayService") as mock_wx_cls, \
             patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            mock_wx_cls.return_value.verify_callback.return_value = {
                "event_type": "REFUND.SUCCESS",  # 非支付成功事件
                "resource": {},
            }

            result = await service.handle_payment_callback(
                headers={"Wechatpay-Serial": "SERIAL_NSEVT"},
                body=b"{}",
            )

        assert result == {"code": "SUCCESS", "message": "忽略非成功事件"}
        # 预约状态不变
        await db_session.refresh(appointment)
        assert appointment.status == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_callback_amount_mismatch_raises(self, db_session: AsyncSession):
        """回调金额与预约金额不一致时应抛出 ValueError"""
        tenant = _make_tenant(db_session, "tenant-cb-amtmis")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)
        _make_payment_profile(db_session, tenant.id, cert_serial_no="SERIAL_AMTMIS")

        appointment = _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            status=0,
            payment_amount=Decimal("50.00"),
        )
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.WeChatPayService") as mock_wx_cls, \
             patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            mock_wx_cls.return_value.verify_callback.return_value = {
                "event_type": "TRANSACTION.SUCCESS",
                "resource": {
                    "out_trade_no": appointment.appointment_no,
                    "transaction_id": "wx_txn_mismatch",
                    "amount": {"total": 9999},  # 金额不一致：应为 5000 分
                },
            }

            with pytest.raises(ValueError, match="回调金额与预约金额不一致"):
                await service.handle_payment_callback(
                    headers={"Wechatpay-Serial": "SERIAL_AMTMIS"},
                    body=b"{}",
                )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_callback_missing_out_trade_no_raises(self, db_session: AsyncSession):
        """回调数据缺少 out_trade_no 时应抛出 ValueError"""
        tenant = _make_tenant(db_session, "tenant-cb-notradeno")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)
        _make_payment_profile(db_session, tenant.id, cert_serial_no="SERIAL_NOTRADE")

        _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            status=0,
            payment_amount=Decimal("50.00"),
        )
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.WeChatPayService") as mock_wx_cls, \
             patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            mock_wx_cls.return_value.verify_callback.return_value = {
                "event_type": "TRANSACTION.SUCCESS",
                "resource": {
                    # 缺少 out_trade_no
                    "transaction_id": "wx_txn_notrade",
                    "amount": {"total": 5000},
                },
            }

            with pytest.raises(ValueError, match="缺少 out_trade_no"):
                await service.handle_payment_callback(
                    headers={"Wechatpay-Serial": "SERIAL_NOTRADE"},
                    body=b"{}",
                )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_callback_appointment_not_found_raises(self, db_session: AsyncSession):
        """回调中 out_trade_no 对应的预约不存在时应抛出 ValueError"""
        tenant = _make_tenant(db_session, "tenant-cb-aptnf")
        _make_payment_profile(db_session, tenant.id, cert_serial_no="SERIAL_APTNF")
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.WeChatPayService") as mock_wx_cls, \
             patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            mock_wx_cls.return_value.verify_callback.return_value = {
                "event_type": "TRANSACTION.SUCCESS",
                "resource": {
                    "out_trade_no": "NONEXISTENT_ORDER_NO",
                    "transaction_id": "wx_txn_aptnf",
                    "amount": {"total": 5000},
                },
            }

            with pytest.raises(ValueError, match="未找到预约"):
                await service.handle_payment_callback(
                    headers={"Wechatpay-Serial": "SERIAL_APTNF"},
                    body=b"{}",
                )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_callback_idempotent_metadata_backfill(self, db_session: AsyncSession):
        """幂等回调补齐缺失的 transaction_id 和 paid_at 元数据"""
        tenant = _make_tenant(db_session, "tenant-cb-meta")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)
        _make_payment_profile(db_session, tenant.id, cert_serial_no="SERIAL_META")

        # 已确认但缺少 transaction_id 和 paid_at 的预约（模拟早期数据）
        appointment = _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            status=APPOINTMENT_STATUS["CONFIRMED"],
            payment_amount=Decimal("50.00"),
            payment_transaction_id=None,
            paid_at=None,
        )
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.WeChatPayService") as mock_wx_cls, \
             patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            mock_wx_cls.return_value.verify_callback.return_value = {
                "event_type": "TRANSACTION.SUCCESS",
                "resource": {
                    "out_trade_no": appointment.appointment_no,
                    "transaction_id": "wx_txn_backfill",
                    "amount": {"total": 5000},
                },
            }

            result = await service.handle_payment_callback(
                headers={"Wechatpay-Serial": "SERIAL_META"},
                body=b"{}",
            )

        assert result == {"code": "SUCCESS", "message": "成功"}
        await db_session.refresh(appointment)
        assert appointment.payment_transaction_id == "wx_txn_backfill"
        assert appointment.paid_at is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_callback_preserves_existing_paid_at_on_idempotent(
        self, db_session: AsyncSession
    ):
        """幂等回调不应覆盖已有的 paid_at 时间"""
        tenant = _make_tenant(db_session, "tenant-cb-pa")
        store = _make_store(db_session, tenant.id)
        dept = _make_department(db_session, tenant.id, store.id)
        doctor = _make_doctor(db_session, tenant.id, store.id, dept.id)
        user = _make_user(db_session, tenant.id)
        patient = _make_patient(db_session, tenant.id, user.id)
        schedule = _make_schedule(db_session, tenant.id, doctor.id, store.id)
        _make_payment_profile(db_session, tenant.id, cert_serial_no="SERIAL_PA")

        original_paid_at = datetime(2026, 1, 15, 10, 30, 0)
        appointment = _make_appointment(
            db_session, tenant.id, schedule.id, user.id, patient.id, doctor.id,
            status=APPOINTMENT_STATUS["CONFIRMED"],
            payment_amount=Decimal("50.00"),
            payment_transaction_id="wx_txn_existing",
            paid_at=original_paid_at,
        )
        await db_session.commit()

        service = PaymentService(db_session)

        with patch("app.modules.payments.service.WeChatPayService") as mock_wx_cls, \
             patch("app.modules.payments.service.get_current_tenant_id", return_value=tenant.id):
            mock_wx_cls.return_value.verify_callback.return_value = {
                "event_type": "TRANSACTION.SUCCESS",
                "resource": {
                    "out_trade_no": appointment.appointment_no,
                    "transaction_id": "wx_txn_existing",
                    "amount": {"total": 5000},
                },
            }

            result = await service.handle_payment_callback(
                headers={"Wechatpay-Serial": "SERIAL_PA"},
                body=b"{}",
            )

        assert result == {"code": "SUCCESS", "message": "成功"}
        await db_session.refresh(appointment)
        # paid_at 保持原值，不被覆盖
        assert appointment.paid_at == original_paid_at
