"""
退款路由端点集成测试。

测试场景：
1. 微信退款回调成功事件
2. 微信退款回调异常事件
3. 微信退款回调关闭事件
4. 微信退款回调忽略非退款事件
5. 微信退款回调缺少证书序列号
6. 微信退款回调支付配置不存在
7. 退款记录列表查询权限校验
8. 按预约ID筛选退款记录
9. 按状态筛选退款记录
10. 退款记录列表分页
11. 获取退款详情
12. 获取退款详情不存在
13. 查询可退款金额
"""
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.core.security import create_access_token
from app.models.appointment import Appointment
from app.models.miniapp_platform import PaymentProfile
from app.models.refund import RefundRecord
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.user import Patient, User


def response_data(response):
    """获取响应数据"""
    payload = response.json()
    return payload.get("data", payload)


def response_message(response):
    """获取响应消息"""
    payload = response.json()
    return payload.get("message") or payload.get("detail")


@pytest.fixture(autouse=True)
def mock_operation_log_task():
    """Mock 操作日志任务"""
    with patch("app.tasks.operation_log_task.save_operation_log.delay") as mock_delay:
        yield mock_delay


# ==================== Fixtures ====================

@pytest_asyncio.fixture
async def paid_appointment(db_session, test_tenant, test_schedule, test_patient, test_doctor, test_user):
    """创建已支付的预约"""
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid4())[:4].upper()}",
        user_id=test_user.id,
        patient_id=test_patient.id,
        doctor_id=test_doctor.id,
        schedule_id=test_schedule.id,
        tenant_id=test_tenant.id,
        queue_number=1,
        status=1,  # 已预约
        patient_name=test_patient.name,
        patient_phone=test_patient.phone,
        doctor_name=test_doctor.name,
        doctor_title=test_doctor.title,
        department_name="测试科室",
        payment_amount=Decimal("30.00"),
        payment_mch_id="1234567890",
        payment_sub_mchid="sub123",
        payment_transaction_id="wx_tx_123",
        payment_profile_id=str(uuid4()),
        paid_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by=test_user.id,
    )
    db_session.add(appointment)
    test_schedule.booked_slots += 1
    await db_session.commit()
    await db_session.refresh(appointment)
    return appointment


@pytest_asyncio.fixture
async def refund_record(db_session, test_tenant, paid_appointment):
    """创建退款记录"""
    refund = RefundRecord(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        appointment_id=paid_appointment.id,
        payment_profile_id=paid_appointment.payment_profile_id,
        refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}ABC123",
        out_trade_no=paid_appointment.appointment_no,
        wx_transaction_id=paid_appointment.payment_transaction_id,
        refund_amount=Decimal("10.00"),
        original_amount=Decimal("30.00"),
        refund_reason="测试退款",
        status="pending",
        mch_id=paid_appointment.payment_mch_id,
        sub_mchid=paid_appointment.payment_sub_mchid,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(refund)
    await db_session.commit()
    await db_session.refresh(refund)
    return refund


@pytest_asyncio.fixture
async def payment_profile(db_session, test_tenant):
    """创建支付配置"""
    profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="测试支付配置",
        code="test_payment",
        mode="direct",
        app_id="wx_app_id",
        mch_id="1234567890",
        cert_serial_no="serial123",
        api_v3_key_ref="key_ref",
        private_key_ref="key_ref",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


@pytest_asyncio.fixture
async def multiple_refunds(db_session, test_tenant, paid_appointment):
    """创建多个退款记录用于测试列表和分页"""
    refunds = []
    for i in range(5):
        refund = RefundRecord(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            appointment_id=paid_appointment.id,
            payment_profile_id=paid_appointment.payment_profile_id,
            refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}ABC{i}",
            out_trade_no=paid_appointment.appointment_no,
            wx_transaction_id=paid_appointment.payment_transaction_id,
            refund_amount=Decimal(f"{(i + 1) * 5}.00"),
            original_amount=Decimal("30.00"),
            refund_reason=f"测试退款{i}",
            status="success" if i % 2 == 0 else "pending",
            mch_id=paid_appointment.payment_mch_id,
            sub_mchid=paid_appointment.payment_sub_mchid,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(refund)
        refunds.append(refund)
    await db_session.commit()
    for refund in refunds:
        await db_session.refresh(refund)
    return refunds


# ==================== 微信退款回调测试 ====================

@pytest.mark.asyncio
async def test_refund_callback_success(async_client, db_session, test_tenant, refund_record, payment_profile):
    """测试微信退款回调成功事件"""
    # 更新 refund_record 关联 payment_profile
    refund_record.payment_profile_id = payment_profile.id
    await db_session.commit()

    callback_data = {
        "event_type": "REFUND.SUCCESS",
        "resource": {
            "out_refund_no": refund_record.refund_no,
            "refund_id": "wx_refund_id_123",
        }
    }

    # Mock WeChatPayService.verify_callback 方法 - 使用 MagicMock 创建可调用的类
    from unittest.mock import MagicMock

    mock_wx_service_instance = MagicMock()
    mock_wx_service_instance.verify_callback.return_value = callback_data

    original_init = None

    def mock_wx_init(self, payment_profile, cert_dir=None):
        # Mock __init__ 只设置 profile，不调用原始初始化
        self.profile = payment_profile

    with patch("app.infrastructure.payments.wechat_pay_service.WeChatPayService.__init__", mock_wx_init):
        with patch("app.infrastructure.payments.wechat_pay_service.WeChatPayService.verify_callback",
                   mock_wx_service_instance.verify_callback):

            response = await async_client.post(
                "/api/v1/refunds/wechat/callback",
                content=json.dumps(callback_data).encode(),
                headers={
                    "Wechatpay-Serial": payment_profile.cert_serial_no,
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 200
    assert response.json() == {"code": "SUCCESS", "message": "成功"}

    # 验证退款记录状态更新
    await db_session.refresh(refund_record)
    assert refund_record.status == "success"
    assert refund_record.wx_refund_id == "wx_refund_id_123"


@pytest.mark.asyncio
async def test_refund_callback_abnormal(async_client, db_session, test_tenant, refund_record, payment_profile):
    """测试微信退款回调异常事件"""
    refund_record.payment_profile_id = payment_profile.id
    await db_session.commit()

    callback_data = {
        "event_type": "REFUND.ABNORMAL",
        "resource": {
            "out_refund_no": refund_record.refund_no,
            "refund_id": "wx_refund_id_456",
        }
    }

    from unittest.mock import MagicMock

    mock_wx_service_instance = MagicMock()
    mock_wx_service_instance.verify_callback.return_value = callback_data

    def mock_wx_init(self, payment_profile, cert_dir=None):
        self.profile = payment_profile

    with patch("app.infrastructure.payments.wechat_pay_service.WeChatPayService.__init__", mock_wx_init):
        with patch("app.infrastructure.payments.wechat_pay_service.WeChatPayService.verify_callback",
                   mock_wx_service_instance.verify_callback):

            response = await async_client.post(
                "/api/v1/refunds/wechat/callback",
                content=json.dumps(callback_data).encode(),
                headers={
                    "Wechatpay-Serial": payment_profile.cert_serial_no,
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 200
    assert response.json() == {"code": "SUCCESS", "message": "成功"}

    await db_session.refresh(refund_record)
    assert refund_record.status == "failed"
    assert refund_record.failed_reason == "退款异常"


@pytest.mark.asyncio
async def test_refund_callback_closed(async_client, db_session, test_tenant, refund_record, payment_profile):
    """测试微信退款回调关闭事件"""
    refund_record.payment_profile_id = payment_profile.id
    await db_session.commit()

    callback_data = {
        "event_type": "REFUND.CLOSED",
        "resource": {
            "out_refund_no": refund_record.refund_no,
            "refund_id": "wx_refund_id_789",
        }
    }

    from unittest.mock import MagicMock

    mock_wx_service_instance = MagicMock()
    mock_wx_service_instance.verify_callback.return_value = callback_data

    def mock_wx_init(self, payment_profile, cert_dir=None):
        self.profile = payment_profile

    with patch("app.infrastructure.payments.wechat_pay_service.WeChatPayService.__init__", mock_wx_init):
        with patch("app.infrastructure.payments.wechat_pay_service.WeChatPayService.verify_callback",
                   mock_wx_service_instance.verify_callback):

            response = await async_client.post(
                "/api/v1/refunds/wechat/callback",
                content=json.dumps(callback_data).encode(),
                headers={
                    "Wechatpay-Serial": payment_profile.cert_serial_no,
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 200
    assert response.json() == {"code": "SUCCESS", "message": "成功"}

    await db_session.refresh(refund_record)
    assert refund_record.status == "failed"


@pytest.mark.asyncio
async def test_refund_callback_ignores_non_refund_event(async_client, payment_profile):
    """测试微信退款回调忽略非退款事件"""
    callback_data = {
        "event_type": "TRANSACTION.SUCCESS",
        "resource": {
            "out_trade_no": "trade_123",
        }
    }

    from unittest.mock import MagicMock

    mock_wx_service_instance = MagicMock()
    mock_wx_service_instance.verify_callback.return_value = callback_data

    def mock_wx_init(self, payment_profile, cert_dir=None):
        self.profile = payment_profile

    with patch("app.infrastructure.payments.wechat_pay_service.WeChatPayService.__init__", mock_wx_init):
        with patch("app.infrastructure.payments.wechat_pay_service.WeChatPayService.verify_callback",
                   mock_wx_service_instance.verify_callback):

            response = await async_client.post(
                "/api/v1/refunds/wechat/callback",
                content=json.dumps(callback_data).encode(),
                headers={
                    "Wechatpay-Serial": payment_profile.cert_serial_no,
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 200
    assert response.json() == {"code": "SUCCESS", "message": "忽略非退款事件"}


@pytest.mark.asyncio
async def test_refund_callback_missing_serial(async_client):
    """测试微信退款回调缺少证书序列号"""
    callback_data = {
        "event_type": "REFUND.SUCCESS",
        "resource": {
            "out_refund_no": "RF123",
        }
    }

    response = await async_client.post(
        "/api/v1/refunds/wechat/callback",
        content=json.dumps(callback_data).encode(),
        headers={
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"code": "FAILED", "message": "缺少证书序列号"}


@pytest.mark.asyncio
async def test_refund_callback_profile_not_found(async_client):
    """测试微信退款回调支付配置不存在"""
    callback_data = {
        "event_type": "REFUND.SUCCESS",
        "resource": {
            "out_refund_no": "RF123",
        }
    }

    # 不需要 mock WeChatPayService，因为找不到 PaymentProfile 时不会调用
    response = await async_client.post(
        "/api/v1/refunds/wechat/callback",
        content=json.dumps(callback_data).encode(),
        headers={
            "Wechatpay-Serial": "non_existent_serial",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"code": "FAILED", "message": "未找到支付配置"}


# ==================== 退款记录查询测试 ====================

@pytest.mark.asyncio
async def test_list_refunds_requires_permission(async_client, store_admin_token, test_store_admin_role):
    """测试退款记录列表需要权限"""
    response = await async_client.get(
        "/api/v1/refunds",
        headers={"Authorization": f"Bearer {store_admin_token}"},
    )

    assert response.status_code == 403
    assert "需要权限" in response_message(response)


@pytest.mark.asyncio
async def test_list_refunds_by_appointment(async_client, super_admin_token, multiple_refunds, paid_appointment):
    """测试按预约ID筛选退款记录"""
    response = await async_client.get(
        f"/api/v1/refunds?appointment_id={paid_appointment.id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    data = response_data(response)
    assert "items" in data
    assert len(data["items"]) == 5
    assert all(item["appointment_id"] == paid_appointment.id for item in data["items"])


@pytest.mark.asyncio
async def test_list_refunds_by_status(async_client, super_admin_token, multiple_refunds):
    """测试按状态筛选退款记录"""
    response = await async_client.get(
        "/api/v1/refunds?status=success",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    data = response_data(response)
    assert "items" in data
    assert all(item["status"] == "success" for item in data["items"])


@pytest.mark.asyncio
async def test_list_refunds_pagination(async_client, super_admin_token, multiple_refunds):
    """测试退款记录列表分页"""
    response = await async_client.get(
        "/api/v1/refunds?page=1&page_size=2",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    data = response_data(response)
    assert "total" in data
    assert "items" in data
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_refund_detail(async_client, super_admin_token, refund_record):
    """测试获取退款详情"""
    response = await async_client.get(
        f"/api/v1/refunds/{refund_record.id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    data = response_data(response)
    assert data["id"] == refund_record.id
    assert data["refund_no"] == refund_record.refund_no
    assert data["status"] == refund_record.status


@pytest.mark.asyncio
async def test_get_refund_detail_not_found(async_client, super_admin_token):
    """测试获取不存在的退款详情"""
    fake_id = str(uuid4())
    response = await async_client.get(
        f"/api/v1/refunds/{fake_id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 404
    assert response_message(response) == "退款记录不存在"


@pytest.mark.asyncio
async def test_refundable_amount_endpoint(async_client, super_admin_token, db_session, paid_appointment):
    """测试查询可退款金额端点"""
    # 确保预约的 refund_status 有默认值
    if paid_appointment.refund_status is None:
        paid_appointment.refund_status = "none"
        await db_session.commit()

    response = await async_client.get(
        f"/api/v1/refunds/refundable-amount/{paid_appointment.id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    data = response_data(response)
    assert Decimal(str(data["payment_amount"])) == Decimal("30.00")
    assert Decimal(str(data["refunded_amount"])) == Decimal("0")
    assert Decimal(str(data["refundable_amount"])) == Decimal("30.00")
    assert data["refund_status"] == "none"


@pytest.mark.asyncio
async def test_refundable_amount_with_partial_refund(async_client, super_admin_token, db_session, test_tenant, paid_appointment):
    """测试部分退款后的可退款金额"""
    # 创建部分退款记录
    refund = RefundRecord(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        appointment_id=paid_appointment.id,
        payment_profile_id=paid_appointment.payment_profile_id,
        refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}PARTIAL",
        out_trade_no=paid_appointment.appointment_no,
        wx_transaction_id=paid_appointment.payment_transaction_id,
        refund_amount=Decimal("10.00"),
        original_amount=Decimal("30.00"),
        refund_reason="部分退款",
        status="success",
        mch_id=paid_appointment.payment_mch_id,
        sub_mchid=paid_appointment.payment_sub_mchid,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(refund)

    # 更新预约退款状态
    paid_appointment.refund_amount = Decimal("10.00")
    paid_appointment.refund_status = "partial_refunded"
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/refunds/refundable-amount/{paid_appointment.id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    data = response_data(response)
    assert Decimal(str(data["payment_amount"])) == Decimal("30.00")
    assert Decimal(str(data["refunded_amount"])) == Decimal("10.00")
    assert Decimal(str(data["refundable_amount"])) == Decimal("20.00")
    assert data["refund_status"] == "partial_refunded"


@pytest.mark.asyncio
async def test_refundable_amount_fully_refunded(async_client, super_admin_token, db_session, test_tenant, paid_appointment):
    """测试全额退款后的可退款金额"""
    # 创建全额退款记录
    refund = RefundRecord(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        appointment_id=paid_appointment.id,
        payment_profile_id=paid_appointment.payment_profile_id,
        refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}FULL",
        out_trade_no=paid_appointment.appointment_no,
        wx_transaction_id=paid_appointment.payment_transaction_id,
        refund_amount=Decimal("30.00"),
        original_amount=Decimal("30.00"),
        refund_reason="全额退款",
        status="success",
        mch_id=paid_appointment.payment_mch_id,
        sub_mchid=paid_appointment.payment_sub_mchid,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(refund)

    # 更新预约退款状态
    paid_appointment.refund_amount = Decimal("30.00")
    paid_appointment.refund_status = "refunded"
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/refunds/refundable-amount/{paid_appointment.id}",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 200
    data = response_data(response)
    assert Decimal(str(data["payment_amount"])) == Decimal("30.00")
    assert Decimal(str(data["refunded_amount"])) == Decimal("30.00")
    assert Decimal(str(data["refundable_amount"])) == Decimal("0")
    assert data["refund_status"] == "refunded"


@pytest.mark.asyncio
async def test_refund_callback_syncs_appointment_refund_status(async_client, db_session, test_tenant, refund_record, payment_profile, paid_appointment):
    """测试退款回调正确同步预约退款状态"""
    refund_record.payment_profile_id = payment_profile.id
    refund_record.refund_amount = Decimal("30.00")
    if paid_appointment.refund_status is None:
        paid_appointment.refund_status = "none"
    await db_session.commit()

    callback_data = {
        "event_type": "REFUND.SUCCESS",
        "resource": {
            "out_refund_no": refund_record.refund_no,
            "refund_id": "wx_refund_id_full",
        }
    }

    from unittest.mock import MagicMock

    mock_wx_service_instance = MagicMock()
    mock_wx_service_instance.verify_callback.return_value = callback_data

    def mock_wx_init(self, payment_profile, cert_dir=None):
        self.profile = payment_profile

    with patch("app.infrastructure.payments.wechat_pay_service.WeChatPayService.__init__", mock_wx_init):
        with patch("app.infrastructure.payments.wechat_pay_service.WeChatPayService.verify_callback",
                   mock_wx_service_instance.verify_callback):

            response = await async_client.post(
                "/api/v1/refunds/wechat/callback",
                content=json.dumps(callback_data).encode(),
                headers={
                    "Wechatpay-Serial": payment_profile.cert_serial_no,
                    "Content-Type": "application/json",
                },
            )

    assert response.status_code == 200

    # 验证预约退款状态更新
    await db_session.refresh(paid_appointment)
    assert paid_appointment.refund_status == "refunded"
    assert paid_appointment.refund_amount == Decimal("30.00")
