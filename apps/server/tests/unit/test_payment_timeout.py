from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models.miniapp_platform import PaymentProfile
from app.modules.appointments.common import APPOINTMENT_STATUS
from app.modules.payments.service import PaymentService
from app.tasks.payment_task import _cancel_tenant_expired


class _ScalarListResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items


class _ExecResult:
    def __init__(self, rowcount: int):
        self.rowcount = rowcount


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_payment_callback_settles_pending_appointment_with_tenant_fallback(
    db_session,
    test_tenant,
    test_appointment,
):
    test_appointment.status = 0
    test_appointment.payment_amount = 30

    payment_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="测试支付配置",
        code="pay-profile-callback",
        mode="direct",
        cert_serial_no="callback-serial-1",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(payment_profile)
    await db_session.commit()

    service = PaymentService(db_session)

    with patch("app.modules.payments.service.WeChatPayService") as mock_wx_service_cls, patch(
        "app.modules.payments.service.get_current_tenant_id",
        return_value=str(uuid4()),
    ):
        mock_wx_service_cls.return_value.verify_callback.return_value = {
            "event_type": "TRANSACTION.SUCCESS",
            "resource": {
                "out_trade_no": f"APPT{test_appointment.id}",
                "transaction_id": "wx_txn_paid_1",
            },
        }

        result = await service.handle_payment_callback(
            headers={"Wechatpay-Serial": payment_profile.cert_serial_no},
            body=b"{}",
        )

    await db_session.refresh(test_appointment)
    assert result == {"code": "SUCCESS", "message": "成功"}
    assert test_appointment.status == APPOINTMENT_STATUS["CONFIRMED"]
    assert test_appointment.payment_transaction_id == "wx_txn_paid_1"
    assert test_appointment.paid_at is not None


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_payment_callback_treats_duplicate_success_as_idempotent(
    db_session,
    test_tenant,
    test_appointment,
):
    paid_at = datetime.utcnow() - timedelta(minutes=1)
    test_appointment.status = APPOINTMENT_STATUS["CONFIRMED"]
    test_appointment.payment_amount = 30
    test_appointment.payment_transaction_id = "wx_txn_paid_2"
    test_appointment.paid_at = paid_at

    payment_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="测试支付配置",
        code="pay-profile-callback-dup",
        mode="direct",
        cert_serial_no="callback-serial-2",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(payment_profile)
    await db_session.commit()

    service = PaymentService(db_session)

    with patch("app.modules.payments.service.WeChatPayService") as mock_wx_service_cls:
        mock_wx_service_cls.return_value.verify_callback.return_value = {
            "event_type": "TRANSACTION.SUCCESS",
            "resource": {
                "out_trade_no": f"APPT{test_appointment.id}",
                "transaction_id": "wx_txn_paid_2",
            },
        }

        result = await service.handle_payment_callback(
            headers={"Wechatpay-Serial": payment_profile.cert_serial_no},
            body=b"{}",
        )

    await db_session.refresh(test_appointment)
    assert result == {"code": "SUCCESS", "message": "成功"}
    assert test_appointment.status == APPOINTMENT_STATUS["CONFIRMED"]
    assert test_appointment.payment_transaction_id == "wx_txn_paid_2"
    assert test_appointment.paid_at == paid_at


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_payment_callback_ignores_late_success_after_expiration(
    db_session,
    test_tenant,
    test_appointment,
):
    test_appointment.status = APPOINTMENT_STATUS["EXPIRED"]
    test_appointment.payment_amount = 30
    test_appointment.payment_transaction_id = None
    test_appointment.paid_at = None

    payment_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="测试支付配置",
        code="pay-profile-callback-expired",
        mode="direct",
        cert_serial_no="callback-serial-3",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(payment_profile)
    await db_session.commit()

    service = PaymentService(db_session)

    with patch("app.modules.payments.service.WeChatPayService") as mock_wx_service_cls:
        mock_wx_service_cls.return_value.verify_callback.return_value = {
            "event_type": "TRANSACTION.SUCCESS",
            "resource": {
                "out_trade_no": f"APPT{test_appointment.id}",
                "transaction_id": "wx_txn_paid_3",
            },
        }

        result = await service.handle_payment_callback(
            headers={"Wechatpay-Serial": payment_profile.cert_serial_no},
            body=b"{}",
        )

    await db_session.refresh(test_appointment)
    assert result == {"code": "SUCCESS", "message": "成功"}
    assert test_appointment.status == APPOINTMENT_STATUS["EXPIRED"]
    assert test_appointment.payment_transaction_id is None
    assert test_appointment.paid_at is None


@pytest.mark.unit
def test_cancel_tenant_expired_releases_slot_once_when_expire_succeeds():
    appointment = SimpleNamespace(
        id=str(uuid4()),
        appointment_no="YYTEST001",
        schedule_id=str(uuid4()),
    )
    db = MagicMock()
    db.execute.side_effect = [
        _ScalarListResult([appointment]),
        _ExecResult(1),
        _ExecResult(1),
    ]

    cancelled = _cancel_tenant_expired(
        db=db,
        tenant_id=str(uuid4()),
        timeout_threshold=datetime.now() - timedelta(minutes=30),
    )

    assert cancelled == 1
    db.commit.assert_called_once()
    assert len(db.execute.call_args_list) == 3
    assert "booked_slots" in str(db.execute.call_args_list[2].args[0])


@pytest.mark.unit
def test_cancel_tenant_expired_skips_release_when_race_already_settled():
    appointment = SimpleNamespace(
        id=str(uuid4()),
        appointment_no="YYTEST002",
        schedule_id=str(uuid4()),
    )
    db = MagicMock()
    db.execute.side_effect = [
        _ScalarListResult([appointment]),
        _ExecResult(0),
    ]

    cancelled = _cancel_tenant_expired(
        db=db,
        tenant_id=str(uuid4()),
        timeout_threshold=datetime.now() - timedelta(minutes=30),
    )

    assert cancelled == 0
    db.commit.assert_not_called()
    assert len(db.execute.call_args_list) == 2
