"""退款服务 — 防退错核心逻辑。"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.appointment import Appointment
from app.models.refund import RefundRecord
from app.models.schedule import Schedule
from app.constants.appointment import APPOINTMENT_STATUS

COUNTED_REFUND_STATUSES = ("pending", "processing", "success")
IN_FLIGHT_REFUND_STATUSES = ("pending", "processing")
FINAL_REFUND_STATUSES = ("success", "failed")

# 兼容旧名 — 历史调用方用作"金额累计聚合"语义；新代码请使用 COUNTED_REFUND_STATUSES。
ACTIVE_REFUND_STATUSES = COUNTED_REFUND_STATUSES


def _generate_refund_no() -> str:
    """生成退款单号：RF + 时间戳 + 随机后缀。"""
    now = datetime.now()
    return f"RF{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


class RefundService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_payment_out_trade_no(self, appointment: Appointment) -> str:
        """复用支付模块的商户订单号规则，确保退款永远指向同一原订单。"""
        from app.modules.payments.service import PaymentService

        payment_service = PaymentService(self.db)
        return payment_service._generate_out_trade_no(appointment)

    async def _get_refund_appointment(
        self,
        refund_record: RefundRecord,
    ) -> Optional[Appointment]:
        if not refund_record.appointment_id:
            return None

        stmt = select(Appointment).where(Appointment.id == refund_record.appointment_id)
        if refund_record.tenant_id:
            stmt = stmt.where(Appointment.tenant_id == refund_record.tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_refund_payment_reference_repair_plan(
        self,
        refund_record: RefundRecord,
    ) -> dict:
        """生成退款支付引用修复计划，不直接落库。"""
        appointment = await self._get_refund_appointment(refund_record)

        changes: dict[str, Optional[str]] = {}
        issues: list[str] = []
        expected_out_trade_no: Optional[str] = None
        expected_transaction_id: Optional[str] = None
        expected_payment_profile_id: Optional[str] = None

        if appointment:
            expected_out_trade_no = self._get_payment_out_trade_no(appointment)
            expected_transaction_id = appointment.payment_transaction_id
            expected_payment_profile_id = appointment.payment_profile_id

            if refund_record.out_trade_no != expected_out_trade_no:
                changes["out_trade_no"] = expected_out_trade_no

            if expected_transaction_id and (
                refund_record.wx_transaction_id != expected_transaction_id
            ):
                changes["wx_transaction_id"] = expected_transaction_id

            if expected_payment_profile_id and (
                refund_record.payment_profile_id != expected_payment_profile_id
            ):
                changes["payment_profile_id"] = expected_payment_profile_id
        else:
            issues.append("appointment_not_found")

        final_out_trade_no = changes.get("out_trade_no", refund_record.out_trade_no)
        final_transaction_id = changes.get(
            "wx_transaction_id", refund_record.wx_transaction_id
        )

        if not final_out_trade_no and not final_transaction_id:
            issues.append("missing_payment_reference")

        return {
            "appointment": appointment,
            "changes": changes,
            "issues": issues,
            "repairable": bool(final_out_trade_no or final_transaction_id),
            "expected_out_trade_no": expected_out_trade_no,
            "expected_transaction_id": expected_transaction_id,
            "expected_payment_profile_id": expected_payment_profile_id,
            "final_out_trade_no": final_out_trade_no,
            "final_transaction_id": final_transaction_id,
        }

    async def ensure_refund_payment_reference(
        self,
        refund_record: RefundRecord,
    ) -> tuple[str, Optional[str]]:
        """修正历史退款记录中的支付引用信息。

        兼容早期错误写入 `appointment_no` 到 `out_trade_no` 的数据，
        并尽量从预约补齐缺失的微信交易号。
        """
        plan = await self.get_refund_payment_reference_repair_plan(refund_record)

        for field, value in plan["changes"].items():
            setattr(refund_record, field, value)

        if plan["changes"]:
            await self.db.flush()

        if not plan["repairable"]:
            raise ValueError("退款记录缺少原支付凭证")

        return plan["final_out_trade_no"] or "", plan["final_transaction_id"]

    async def backfill_refund_payment_references(
        self,
        *,
        tenant_id: Optional[str] = None,
        limit: Optional[int] = None,
        dry_run: bool = True,
    ) -> dict:
        """批量修复历史退款记录中的支付引用信息。"""
        stmt = select(RefundRecord).order_by(
            RefundRecord.created_at.asc(),
            RefundRecord.id.asc(),
        )
        if tenant_id:
            stmt = stmt.where(RefundRecord.tenant_id == tenant_id)
        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        refund_records = list(result.scalars().all())

        summary = {
            "scanned": len(refund_records),
            "would_update": 0,
            "updated": 0,
            "unchanged": 0,
            "unrepairable": 0,
            "details": [],
        }

        for refund_record in refund_records:
            plan = await self.get_refund_payment_reference_repair_plan(refund_record)
            detail = {
                "refund_id": refund_record.id,
                "refund_no": refund_record.refund_no,
                "appointment_id": refund_record.appointment_id,
                "changes": plan["changes"],
                "issues": plan["issues"],
            }

            if plan["changes"]:
                summary["details"].append(detail)
                if dry_run:
                    summary["would_update"] += 1
                else:
                    for field, value in plan["changes"].items():
                        setattr(refund_record, field, value)
                    summary["updated"] += 1
                continue

            if plan["repairable"]:
                summary["unchanged"] += 1
            else:
                summary["unrepairable"] += 1
                summary["details"].append(detail)

        if not dry_run and summary["updated"] > 0:
            await self.db.flush()

        return summary

    async def sync_appointment_refund_state(
        self,
        appointment_id: str,
        *,
        active_statuses: tuple[str, ...] = COUNTED_REFUND_STATUSES,
    ) -> Optional[Appointment]:
        """按非失败退款记录聚合回写预约退款状态。"""
        stmt = select(Appointment).where(Appointment.id == appointment_id)
        result = await self.db.execute(stmt)
        appointment = result.scalar_one_or_none()

        if not appointment:
            return None

        refund_stmt = select(func.coalesce(func.sum(RefundRecord.refund_amount), 0)).where(
            RefundRecord.appointment_id == appointment_id,
            RefundRecord.status.in_(active_statuses),
        )
        if appointment.tenant_id:
            refund_stmt = refund_stmt.where(RefundRecord.tenant_id == appointment.tenant_id)

        refund_result = await self.db.execute(refund_stmt)
        aggregated_refund_amount = Decimal(str(refund_result.scalar()))

        appointment.refund_amount = aggregated_refund_amount
        payment_amount = appointment.payment_amount or Decimal("0")
        if aggregated_refund_amount <= 0:
            appointment.refund_status = "none"
        elif payment_amount > 0 and aggregated_refund_amount >= payment_amount:
            appointment.refund_status = "refunded"
        else:
            appointment.refund_status = "partial_refunded"

        await self.db.flush()
        return appointment

    async def get_refundable_amount(self, appointment_id: str) -> dict:
        """查询预约的可退款金额。"""
        tenant_id = get_current_tenant_id()

        # 查询预约
        stmt = select(Appointment).where(Appointment.id == appointment_id)
        if tenant_id:
            stmt = stmt.where(Appointment.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise ValueError("预约不存在")

        payment_amount = appointment.payment_amount or Decimal("0")

        # 查询累计退款金额
        refund_stmt = select(func.coalesce(func.sum(RefundRecord.refund_amount), 0)).where(
            RefundRecord.appointment_id == appointment_id,
            RefundRecord.status.in_(COUNTED_REFUND_STATUSES),
        )
        if tenant_id:
            refund_stmt = refund_stmt.where(RefundRecord.tenant_id == tenant_id)
        refund_result = await self.db.execute(refund_stmt)
        refunded_amount = Decimal(str(refund_result.scalar()))

        refundable_amount = payment_amount - refunded_amount

        return {
            "payment_amount": payment_amount,
            "refunded_amount": refunded_amount,
            "refundable_amount": max(refundable_amount, Decimal("0")),
            "refund_status": appointment.refund_status,
        }

    async def create_refund(
        self,
        appointment_id: str,
        refund_amount: Decimal,
        refund_reason: str,
        operator_id: str,
    ) -> RefundRecord:
        """
        创建退款记录并发起微信退款。

        防退错机制：
        1. 商户一致性：从预约支付快照读取 mch_id/sub_mchid
        2. 金额校验：累计退款不超过原支付金额
        3. 幂等性：refund_no 唯一约束
        4. 事务一致性：RefundRecord + Appointment 同一事务
        5. 租户隔离：双重过滤
        """
        tenant_id = get_current_tenant_id()

        # === 1. 校验预约 ===
        apt_stmt = select(Appointment).where(Appointment.id == appointment_id)
        if tenant_id:
            apt_stmt = apt_stmt.where(Appointment.tenant_id == tenant_id)
        result = await self.db.execute(apt_stmt)
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise ValueError("预约不存在")

        # === 2. 校验预约状态 — 已支付才能退款 ===
        if appointment.status not in (
            APPOINTMENT_STATUS["CONFIRMED"],
            APPOINTMENT_STATUS["SIGNED"],
            APPOINTMENT_STATUS["SEEING"],
            APPOINTMENT_STATUS["COMPLETED"],
        ):
            raise ValueError("当前预约状态不允许退款")

        payment_amount = appointment.payment_amount
        if not payment_amount or payment_amount <= 0:
            raise ValueError("预约未支付，无法退款")

        # === 3a. 并发去重：同一预约不允许同时存在 pending/processing 退款 ===
        # 防止用户重复点击或后台并发触发，导致同一笔钱被重复发起退款。
        # 仅在金额上限校验之前拦截 — 避免"两条 pending 各退一半"绕开金额上限。
        in_flight_stmt = select(func.count(RefundRecord.id)).where(
            RefundRecord.appointment_id == appointment_id,
            RefundRecord.status.in_(IN_FLIGHT_REFUND_STATUSES),
        )
        if tenant_id:
            in_flight_stmt = in_flight_stmt.where(RefundRecord.tenant_id == tenant_id)
        in_flight_result = await self.db.execute(in_flight_stmt)
        in_flight_count = in_flight_result.scalar() or 0
        if in_flight_count > 0:
            raise ValueError("已有进行中的退款，请等待处理完成后再发起")

        # === 3b. 累计退款金额校验（success 也计入累计，部分退款场景仍可补退）===
        refunded_stmt = select(func.coalesce(func.sum(RefundRecord.refund_amount), 0)).where(
            RefundRecord.appointment_id == appointment_id,
            RefundRecord.status.in_(COUNTED_REFUND_STATUSES),
        )
        if tenant_id:
            refunded_stmt = refunded_stmt.where(RefundRecord.tenant_id == tenant_id)
        refunded_result = await self.db.execute(refunded_stmt)
        already_refunded = Decimal(str(refunded_result.scalar()))

        if refund_amount <= 0:
            raise ValueError("退款金额必须大于0")
        if already_refunded + refund_amount > payment_amount:
            raise ValueError(
                f"退款金额超出限制：已退 {already_refunded}，本次 {refund_amount}，"
                f"原支付 {payment_amount}"
            )

        # === 4. 校验支付配置快照存在 ===
        if not appointment.payment_mch_id and not appointment.payment_sub_mchid:
            raise ValueError("预约缺少支付商户信息，无法退款")

        # === 5. 生成退款单号 ===
        refund_no = _generate_refund_no()
        out_trade_no = self._get_payment_out_trade_no(appointment)

        # === 6. 创建退款记录 ===
        refund_record = RefundRecord(
            tenant_id=tenant_id or appointment.tenant_id,
            appointment_id=appointment_id,
            payment_profile_id=appointment.payment_profile_id,
            refund_no=refund_no,
            out_trade_no=out_trade_no,
            wx_transaction_id=appointment.payment_transaction_id,
            refund_amount=refund_amount,
            original_amount=payment_amount,
            refund_reason=refund_reason,
            status="pending",
            mch_id=appointment.payment_mch_id,
            sub_mchid=appointment.payment_sub_mchid,
            created_by=operator_id,
        )
        self.db.add(refund_record)

        await self.db.flush()
        await self.sync_appointment_refund_state(appointment_id)

        # === 8. 调用微信退款 API（委托给调用方处理） ===
        # 实际的微信退款调用在 router 层处理，因为需要从 PaymentProfile 加载密钥
        # router 层会调用 WeChatPayService.create_refund() 并更新 status

        return refund_record

    async def process_refund_callback(
        self,
        refund_no: str,
        wx_refund_id: Optional[str],
        status: str,
        callback_raw: Optional[str] = None,
        failed_reason: Optional[str] = None,
    ) -> RefundRecord:
        """处理微信退款回调。"""
        stmt = select(RefundRecord).where(RefundRecord.refund_no == refund_no)
        result = await self.db.execute(stmt)
        refund_record = result.scalar_one_or_none()

        if not refund_record:
            raise ValueError(f"退款记录不存在: {refund_no}")

        # 终态回调重复到达时保持既有结果不变，只补齐缺失元数据。
        if refund_record.status in FINAL_REFUND_STATUSES:
            if refund_record.status != status:
                return refund_record
            if wx_refund_id and not refund_record.wx_refund_id:
                refund_record.wx_refund_id = wx_refund_id
            if callback_raw:
                refund_record.callback_raw = callback_raw
            refund_record.callback_at = datetime.now()
            if failed_reason and not refund_record.failed_reason:
                refund_record.failed_reason = failed_reason
            await self.sync_appointment_refund_state(refund_record.appointment_id)
            return refund_record

        refund_record.wx_refund_id = wx_refund_id
        refund_record.status = status
        refund_record.callback_raw = callback_raw
        refund_record.callback_at = datetime.now()
        if failed_reason:
            refund_record.failed_reason = failed_reason

        await self.db.flush()
        await self.sync_appointment_refund_state(refund_record.appointment_id)
        return refund_record

    async def get_refund_records(
        self,
        appointment_id: Optional[str] = None,
        status: Optional[str] = None,
        store_id: Optional[Union[str, list[str]]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[RefundRecord], int]:
        """查询退款记录列表。"""
        tenant_id = get_current_tenant_id()

        query = select(RefundRecord).order_by(RefundRecord.created_at.desc())
        count_stmt = select(func.count(RefundRecord.id))
        conditions = []
        if tenant_id:
            conditions.append(RefundRecord.tenant_id == tenant_id)
        if appointment_id:
            conditions.append(RefundRecord.appointment_id == appointment_id)
        if status:
            conditions.append(RefundRecord.status == status)
        if store_id:
            query = query.join(Appointment, RefundRecord.appointment_id == Appointment.id).join(
                Schedule, Appointment.schedule_id == Schedule.id
            )
            count_stmt = count_stmt.join(Appointment, RefundRecord.appointment_id == Appointment.id).join(
                Schedule, Appointment.schedule_id == Schedule.id
            )
            if isinstance(store_id, list):
                conditions.append(Schedule.store_id.in_(store_id))
            else:
                conditions.append(Schedule.store_id == store_id)

        # 计数
        for cond in conditions:
            count_stmt = count_stmt.where(cond)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()

        # 分页查询
        for cond in conditions:
            query = query.where(cond)
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def get_refund_by_id(self, refund_id: str) -> Optional[RefundRecord]:
        """获取单条退款记录。"""
        tenant_id = get_current_tenant_id()
        stmt = select(RefundRecord).where(RefundRecord.id == refund_id)
        if tenant_id:
            stmt = stmt.where(RefundRecord.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
