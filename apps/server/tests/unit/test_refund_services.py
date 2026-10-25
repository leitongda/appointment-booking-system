"""RefundService 单元测试

覆盖范围:
- create_refund: 正常创建、状态校验、金额校验、并发去重、商户信息校验
- process_refund_callback: 成功/失败回调、终态幂等性
- sync_appointment_refund_state: 退款状态聚合回写
- get_refundable_amount: 可退金额计算
- _generate_refund_no: 退款单号格式
"""

import re
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.appointment import APPOINTMENT_STATUS
from app.models.appointment import Appointment
from app.models.refund import RefundRecord
from app.modules.refunds.service import (
    RefundService,
    _generate_refund_no,
    COUNTED_REFUND_STATUSES,
    IN_FLIGHT_REFUND_STATUSES,
    FINAL_REFUND_STATUSES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_paid_appointment(db, tenant_id, **overrides):
    """创建一个已支付的预约（status=CONFIRMED, payment_amount > 0）。"""
    apt_id = str(uuid4())
    defaults = dict(
        id=apt_id,
        appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:4].upper()}",
        user_id=str(uuid4()),
        patient_id=str(uuid4()),
        doctor_id=str(uuid4()),
        schedule_id=str(uuid4()),
        tenant_id=tenant_id,
        queue_number=1,
        status=APPOINTMENT_STATUS["CONFIRMED"],
        patient_name="测试患者",
        patient_phone="13800000000",
        doctor_name="测试医生",
        doctor_title="主任医师",
        department_name="测试科室",
        payment_amount=Decimal("100.00"),
        payment_mch_id="1900000001",
        payment_sub_mchid="1900000001_001",
        payment_transaction_id="wx_trade_001",
        payment_profile_id=str(uuid4()),
        refund_status="none",
        refund_amount=Decimal("0"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    defaults.update(overrides)
    apt = Appointment(**defaults)
    db.add(apt)
    return apt


def _make_refund_record(db, tenant_id, appointment_id, **overrides):
    """创建一条退款记录。"""
    defaults = dict(
        id=str(uuid4()),
        tenant_id=tenant_id,
        appointment_id=appointment_id,
        refund_no=f"RF{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6].upper()}",
        out_trade_no="OT001",
        wx_transaction_id="wx_trade_001",
        refund_amount=Decimal("50.00"),
        original_amount=Decimal("100.00"),
        refund_reason="测试退款",
        status="pending",
        mch_id="1900000001",
        sub_mchid="1900000001_001",
        created_by=str(uuid4()),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    defaults.update(overrides)
    record = RefundRecord(**defaults)
    db.add(record)
    return record


# ---------------------------------------------------------------------------
# Shared fixtures (module-level so all classes can use them)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def paid_appointment(db_session: AsyncSession, test_tenant):
    """已支付的预约 (status=CONFIRMED, payment_amount=100)"""
    apt = _make_paid_appointment(db_session, test_tenant.id)
    await db_session.commit()
    await db_session.refresh(apt)
    return apt


# ---------------------------------------------------------------------------
# TestRefundService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRefundService:
    """RefundService 核心逻辑测试"""

    @pytest.mark.asyncio
    async def test_create_refund_success(self, db_session, test_tenant, paid_appointment):
        """正常创建退款记录 -- Happy path"""
        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ), patch.object(
            RefundService, "_get_payment_out_trade_no", return_value="OT001"
        ):
            svc = RefundService(db_session)
            record = await svc.create_refund(
                appointment_id=paid_appointment.id,
                refund_amount=Decimal("30.00"),
                refund_reason="患者主动取消",
                operator_id="admin_001",
            )

            assert record is not None
            assert record.status == "pending"
            assert record.refund_amount == Decimal("30.00")
            assert record.original_amount == Decimal("100.00")
            assert record.refund_reason == "患者主动取消"
            assert record.appointment_id == paid_appointment.id
            assert record.mch_id == "1900000001"
            assert record.sub_mchid == "1900000001_001"
            assert record.refund_no.startswith("RF")

    @pytest.mark.asyncio
    async def test_create_refund_updates_appointment_state(self, db_session, test_tenant, paid_appointment):
        """创建退款后预约退款状态应同步更新为 partial_refunded"""
        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ), patch.object(
            RefundService, "_get_payment_out_trade_no", return_value="OT001"
        ):
            svc = RefundService(db_session)
            await svc.create_refund(
                appointment_id=paid_appointment.id,
                refund_amount=Decimal("30.00"),
                refund_reason="部分退款",
                operator_id="admin_001",
            )

            await db_session.refresh(paid_appointment)
            assert paid_appointment.refund_status == "partial_refunded"
            assert paid_appointment.refund_amount == Decimal("30.00")

    @pytest.mark.asyncio
    async def test_create_refund_full_amount_marks_refunded(self, db_session, test_tenant, paid_appointment):
        """全额退款后预约 refund_status 应为 refunded"""
        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ), patch.object(
            RefundService, "_get_payment_out_trade_no", return_value="OT001"
        ):
            svc = RefundService(db_session)
            await svc.create_refund(
                appointment_id=paid_appointment.id,
                refund_amount=Decimal("100.00"),
                refund_reason="全额退款",
                operator_id="admin_001",
            )

            await db_session.refresh(paid_appointment)
            assert paid_appointment.refund_status == "refunded"
            assert paid_appointment.refund_amount == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_create_refund_appointment_not_found(self, db_session, test_tenant):
        """预约不存在时应抛出 ValueError"""
        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            with pytest.raises(ValueError, match="预约不存在"):
                await svc.create_refund(
                    appointment_id="nonexistent_id",
                    refund_amount=Decimal("50.00"),
                    refund_reason="测试",
                    operator_id="admin_001",
                )

    @pytest.mark.asyncio
    async def test_create_refund_invalid_status(self, db_session, test_tenant):
        """未支付/已取消的预约不允许退款"""
        apt = _make_paid_appointment(
            db_session, test_tenant.id,
            status=APPOINTMENT_STATUS["CANCELLED"],
        )
        await db_session.commit()
        await db_session.refresh(apt)

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            with pytest.raises(ValueError, match="当前预约状态不允许退款"):
                await svc.create_refund(
                    appointment_id=apt.id,
                    refund_amount=Decimal("50.00"),
                    refund_reason="测试",
                    operator_id="admin_001",
                )

    @pytest.mark.asyncio
    async def test_create_refund_unpaid_appointment(self, db_session, test_tenant):
        """payment_amount 为 0 或 None 的预约不允许退款"""
        apt = _make_paid_appointment(
            db_session, test_tenant.id,
            payment_amount=None,
        )
        await db_session.commit()
        await db_session.refresh(apt)

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            with pytest.raises(ValueError, match="预约未支付"):
                await svc.create_refund(
                    appointment_id=apt.id,
                    refund_amount=Decimal("50.00"),
                    refund_reason="测试",
                    operator_id="admin_001",
                )

    @pytest.mark.asyncio
    async def test_create_refund_over_refund_prevention(self, db_session, test_tenant, paid_appointment):
        """累计退款金额超过原支付金额时应拒绝"""
        # 先创建一条已成功的退款 (已退 80)
        _make_refund_record(
            db_session, test_tenant.id, paid_appointment.id,
            refund_amount=Decimal("80.00"),
            status="success",
        )
        await db_session.commit()

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ), patch.object(
            RefundService, "_get_payment_out_trade_no", return_value="OT001"
        ):
            svc = RefundService(db_session)
            # 再退 30 -> 累计 110 > 100，应拒绝
            with pytest.raises(ValueError, match="退款金额超出限制"):
                await svc.create_refund(
                    appointment_id=paid_appointment.id,
                    refund_amount=Decimal("30.00"),
                    refund_reason="超退测试",
                    operator_id="admin_001",
                )

    @pytest.mark.asyncio
    async def test_create_refund_concurrent_in_flight_blocked(self, db_session, test_tenant, paid_appointment):
        """已有 pending/processing 退款时不允许再创建"""
        _make_refund_record(
            db_session, test_tenant.id, paid_appointment.id,
            status="pending",
        )
        await db_session.commit()

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ), patch.object(
            RefundService, "_get_payment_out_trade_no", return_value="OT001"
        ):
            svc = RefundService(db_session)
            with pytest.raises(ValueError, match="已有进行中的退款"):
                await svc.create_refund(
                    appointment_id=paid_appointment.id,
                    refund_amount=Decimal("10.00"),
                    refund_reason="并发测试",
                    operator_id="admin_001",
                )

    @pytest.mark.asyncio
    async def test_create_refund_zero_amount_rejected(self, db_session, test_tenant, paid_appointment):
        """退款金额 <= 0 应被拒绝"""
        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            with pytest.raises(ValueError, match="退款金额必须大于0"):
                await svc.create_refund(
                    appointment_id=paid_appointment.id,
                    refund_amount=Decimal("0"),
                    refund_reason="零元退款",
                    operator_id="admin_001",
                )

    @pytest.mark.asyncio
    async def test_create_refund_missing_merchant_info(self, db_session, test_tenant):
        """预约缺少支付商户信息时应拒绝退款"""
        apt = _make_paid_appointment(
            db_session, test_tenant.id,
            payment_mch_id=None,
            payment_sub_mchid=None,
        )
        await db_session.commit()
        await db_session.refresh(apt)

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            with pytest.raises(ValueError, match="缺少支付商户信息"):
                await svc.create_refund(
                    appointment_id=apt.id,
                    refund_amount=Decimal("50.00"),
                    refund_reason="测试",
                    operator_id="admin_001",
                )

    @pytest.mark.asyncio
    async def test_create_refund_partial_refund_allows_topup(self, db_session, test_tenant, paid_appointment):
        """已成功部分退款后，仍可发起补退（累计不超过原支付金额）"""
        # 先退 60 成功
        _make_refund_record(
            db_session, test_tenant.id, paid_appointment.id,
            refund_amount=Decimal("60.00"),
            status="success",
        )
        await db_session.commit()

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ), patch.object(
            RefundService, "_get_payment_out_trade_no", return_value="OT001"
        ):
            svc = RefundService(db_session)
            record = await svc.create_refund(
                appointment_id=paid_appointment.id,
                refund_amount=Decimal("40.00"),
                refund_reason="补退剩余",
                operator_id="admin_001",
            )
            assert record.refund_amount == Decimal("40.00")

            await db_session.refresh(paid_appointment)
            assert paid_appointment.refund_status == "refunded"
            assert paid_appointment.refund_amount == Decimal("100.00")


# ---------------------------------------------------------------------------
# TestRefundCallback
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRefundCallback:
    """退款回调处理测试"""

    @pytest_asyncio.fixture
    async def pending_refund(self, db_session, test_tenant, paid_appointment):
        record = _make_refund_record(
            db_session, test_tenant.id, paid_appointment.id,
            status="pending",
        )
        await db_session.commit()
        await db_session.refresh(record)
        return record

    @pytest.mark.asyncio
    async def test_callback_success(self, db_session, test_tenant, pending_refund, paid_appointment):
        """微信回调 success 状态 -- 正常流转"""
        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            result = await svc.process_refund_callback(
                refund_no=pending_refund.refund_no,
                wx_refund_id="WXRF001",
                status="success",
                callback_raw='{"status":"success"}',
            )

            assert result.status == "success"
            assert result.wx_refund_id == "WXRF001"
            assert result.callback_raw == '{"status":"success"}'
            assert result.callback_at is not None

            # 预约退款状态应同步
            await db_session.refresh(paid_appointment)
            assert paid_appointment.refund_status == "partial_refunded"

    @pytest.mark.asyncio
    async def test_callback_failure(self, db_session, test_tenant, pending_refund, paid_appointment):
        """微信回调 failed 状态 -- 退款标记失败"""
        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            result = await svc.process_refund_callback(
                refund_no=pending_refund.refund_no,
                wx_refund_id=None,
                status="failed",
                failed_reason="余额不足",
            )

            assert result.status == "failed"
            assert result.failed_reason == "余额不足"

            # 失败的退款不计入累计，预约应恢复 none
            await db_session.refresh(paid_appointment)
            assert paid_appointment.refund_status == "none"

    @pytest.mark.asyncio
    async def test_callback_idempotent_final_status(self, db_session, test_tenant, paid_appointment):
        """终态回调重复到达时应保持既有结果不变（幂等性）"""
        # 先把退款推进到 success
        record = _make_refund_record(
            db_session, test_tenant.id, paid_appointment.id,
            status="success",
            wx_refund_id="WXRF001",
        )
        await db_session.commit()
        await db_session.refresh(record)

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            # 再次收到 success 回调（重复投递）
            result = await svc.process_refund_callback(
                refund_no=record.refund_no,
                wx_refund_id="WXRF001",
                status="success",
                callback_raw='{"retry":true}',
            )

            # 状态不变
            assert result.status == "success"
            assert result.wx_refund_id == "WXRF001"

    @pytest.mark.asyncio
    async def test_callback_idempotent_status_mismatch_returns_early(self, db_session, test_tenant, paid_appointment):
        """终态回调但 status 不同时直接返回（不覆盖已有结果）"""
        record = _make_refund_record(
            db_session, test_tenant.id, paid_appointment.id,
            status="failed",
        )
        await db_session.commit()
        await db_session.refresh(record)

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            result = await svc.process_refund_callback(
                refund_no=record.refund_no,
                wx_refund_id="WXRF002",
                status="success",  # 与已有 failed 不同
            )

            # 不应覆盖
            assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_callback_record_not_found(self, db_session, test_tenant):
        """退款记录不存在时应抛出 ValueError"""
        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            with pytest.raises(ValueError, match="退款记录不存在"):
                await svc.process_refund_callback(
                    refund_no="RF_NONEXISTENT",
                    wx_refund_id=None,
                    status="success",
                )

    @pytest.mark.asyncio
    async def test_callback_fills_missing_metadata_on_final(self, db_session, test_tenant, paid_appointment):
        """终态回调补齐缺失的 wx_refund_id 和 callback_raw"""
        record = _make_refund_record(
            db_session, test_tenant.id, paid_appointment.id,
            status="success",
            wx_refund_id=None,  # 缺失
            callback_raw=None,  # 缺失
        )
        await db_session.commit()
        await db_session.refresh(record)

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            result = await svc.process_refund_callback(
                refund_no=record.refund_no,
                wx_refund_id="WXRF_LATE",
                status="success",
                callback_raw='{"补发":true}',
            )

            assert result.wx_refund_id == "WXRF_LATE"
            assert result.callback_raw == '{"补发":true}'


# ---------------------------------------------------------------------------
# TestSyncRefundState & GetRefundableAmount
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRefundStateSync:
    """退款状态聚合与可退金额查询"""

    @pytest.mark.asyncio
    async def test_sync_no_refund_sets_none(self, db_session, test_tenant, paid_appointment):
        """无退款记录时 refund_status 应为 none"""
        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            result = await svc.sync_appointment_refund_state(paid_appointment.id)
            assert result.refund_status == "none"
            assert result.refund_amount == Decimal("0")

    @pytest.mark.asyncio
    async def test_sync_partial_refund(self, db_session, test_tenant, paid_appointment):
        """部分退款时 refund_status 应为 partial_refunded"""
        _make_refund_record(
            db_session, test_tenant.id, paid_appointment.id,
            refund_amount=Decimal("25.00"),
            status="success",
        )
        await db_session.commit()

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            result = await svc.sync_appointment_refund_state(paid_appointment.id)
            assert result.refund_status == "partial_refunded"
            assert result.refund_amount == Decimal("25.00")

    @pytest.mark.asyncio
    async def test_get_refundable_amount(self, db_session, test_tenant, paid_appointment):
        """可退金额 = 原支付金额 - 已退金额"""
        _make_refund_record(
            db_session, test_tenant.id, paid_appointment.id,
            refund_amount=Decimal("40.00"),
            status="success",
        )
        await db_session.commit()

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            result = await svc.get_refundable_amount(paid_appointment.id)
            assert result["payment_amount"] == Decimal("100.00")
            assert result["refunded_amount"] == Decimal("40.00")
            assert result["refundable_amount"] == Decimal("60.00")

    @pytest.mark.asyncio
    async def test_get_refundable_amount_floors_at_zero(self, db_session, test_tenant, paid_appointment):
        """全额退款后可退金额应为 0，不出现负数"""
        _make_refund_record(
            db_session, test_tenant.id, paid_appointment.id,
            refund_amount=Decimal("100.00"),
            status="success",
        )
        await db_session.commit()

        with patch(
            "app.modules.refunds.service.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            svc = RefundService(db_session)
            result = await svc.get_refundable_amount(paid_appointment.id)
            assert result["refundable_amount"] == Decimal("0")


# ---------------------------------------------------------------------------
# TestGenerateRefundNo
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGenerateRefundNo:
    """退款单号生成格式校验"""

    def test_format_starts_with_rf(self):
        refund_no = _generate_refund_no()
        assert refund_no.startswith("RF")

    def test_format_contains_timestamp(self):
        refund_no = _generate_refund_no()
        # RF + 14 digits (YYYYMMDDHHmmSS) + 6 hex chars = 22 chars total
        assert len(refund_no) == 22

    def test_unique_per_call(self):
        nos = {_generate_refund_no() for _ in range(50)}
        assert len(nos) == 50, "退款单号应唯一"


# ---------------------------------------------------------------------------
# R4-11: 退款回查租户收敛（process_refund_callback 的 tenant_id 参数）
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.security
class TestRefundCallbackTenantScope:
    """A 租户上下文的回调不能命中/更新 B 租户的退款记录。"""

    @pytest_asyncio.fixture
    async def other_tenant(self, db_session: AsyncSession, test_tenant):
        """第二个租户：退款记录属于它，回调上下文属于 test_tenant。"""
        from app.models.tenant import Tenant

        tenant = Tenant(
            id=str(uuid4()),
            tenant_code=f"refund_b_{uuid4().hex[:8]}",
            name="退款租户B",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        return tenant

    @pytest_asyncio.fixture
    async def tenant_b_refund(self, db_session, other_tenant):
        """属于租户 B 的 pending 退款记录。"""
        apt = _make_paid_appointment(db_session, other_tenant.id)
        record = _make_refund_record(db_session, other_tenant.id, apt.id, status="pending")
        await db_session.commit()
        await db_session.refresh(record)
        return record

    async def test_callback_with_wrong_tenant_raises(
        self, db_session, test_tenant, tenant_b_refund
    ):
        """A 租户上下文 + B 租户的退款单号 → 查不到，视为不存在。"""
        service = RefundService(db_session)
        with pytest.raises(ValueError, match="退款记录不存在"):
            await service.process_refund_callback(
                refund_no=tenant_b_refund.refund_no,
                wx_refund_id="wx_refund_1",
                status="success",
                tenant_id=test_tenant.id,
            )
        await db_session.refresh(tenant_b_refund)
        assert tenant_b_refund.status == "pending"  # 未被误更新

    async def test_callback_with_matching_tenant_updates(
        self, db_session, other_tenant, tenant_b_refund
    ):
        service = RefundService(db_session)
        result = await service.process_refund_callback(
            refund_no=tenant_b_refund.refund_no,
            wx_refund_id="wx_refund_1",
            status="success",
            tenant_id=other_tenant.id,
        )
        assert result.status == "success"
        assert result.wx_refund_id == "wx_refund_1"

    async def test_callback_without_tenant_keeps_legacy_lookup(
        self, db_session, tenant_b_refund
    ):
        """不传 tenant_id（非回调路径）保持全局幂等键查找。"""
        service = RefundService(db_session)
        result = await service.process_refund_callback(
            refund_no=tenant_b_refund.refund_no,
            wx_refund_id="wx_refund_2",
            status="success",
        )
        assert result.status == "success"
