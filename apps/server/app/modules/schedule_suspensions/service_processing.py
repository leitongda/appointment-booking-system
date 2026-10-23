"""停诊患者处置服务

负责处理停诊后受影响预约的自动化处置，支持四种处置方式:
- auto_refund: 自动取消预约并触发退款
- reschedule: 取消原预约、释放号源，通知患者选择同一科室的其他医生
- change_date: 取消原预约、释放号源，通知患者选择同一医生的其他日期
- manual: 仅记录，等待人工处理
"""
import json
import logging
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants.appointment import ACTIVE_APPOINTMENT_STATUSES, APPOINTMENT_STATUS
from app.core.redis import RedisCache
from app.middleware.tenant_context import get_current_tenant_id
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.schedule_suspension import ScheduleSuspension
from app.modules.messages.service_messages import MessageService
from app.utils.audit import set_update_audit

logger = logging.getLogger(__name__)

# 允许的处置方式
VALID_PROCESSING_METHODS = {"auto_refund", "reschedule", "change_date", "manual"}


class SuspensionProcessingService:
    """停诊患者处置服务

    Args:
        db: 数据库会话
        tenant_id: 管理员账号租户锚点（R1-9）。停诊记录查询以锚点强过滤；
            未传入时才回退请求上下文（兼容排班内部调用）。
    """

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    def _tenant(self) -> str | None:
        """账号锚点优先，未提供时回退请求上下文。"""
        if self.tenant_id is not None:
            return self.tenant_id
        return get_current_tenant_id()

    async def process_suspension(
        self,
        suspension_id: str,
        processing_method: str,
        operator_id: str | None = None,
    ) -> dict:
        """
        处置停诊影响的患者

        Args:
            suspension_id: 停诊记录ID
            processing_method: 处置方式 (auto_refund/reschedule/change_date/manual)
            operator_id: 操作人ID

        Returns:
            处置结果统计

        Raises:
            ValueError: 停诊记录不存在、处置方式无效、停诊已取消、已处置完成
        """
        if processing_method not in VALID_PROCESSING_METHODS:
            raise ValueError(
                f"无效的处置方式: {processing_method}，"
                f"允许的值: {', '.join(sorted(VALID_PROCESSING_METHODS))}"
            )

        # 1. 获取停诊记录
        suspension = await self._get_suspension(suspension_id)
        if not suspension:
            raise ValueError("停诊记录不存在")
        if suspension.status != 1:
            raise ValueError("停诊记录已取消，无法处置")
        if suspension.processing_status == "completed":
            raise ValueError("该停诊已处置完成")

        # 2. 标记为处理中
        suspension.processing_method = processing_method
        suspension.processing_status = "processing"
        set_update_audit(suspension, operator_id)
        await self.db.flush()

        # 3. 查找所有受影响的活跃预约
        affected_appointments = await self._find_affected_appointments(suspension)
        suspension.affected_appointment_count = len(affected_appointments)

        if not affected_appointments:
            suspension.processing_status = "completed"
            set_update_audit(suspension, operator_id)
            await self.db.commit()
            await self.db.refresh(suspension)
            return {
                "suspension_id": suspension_id,
                "processing_method": processing_method,
                "processing_status": "completed",
                "total_affected": 0,
                "success_count": 0,
                "failed_count": 0,
                "details": [],
            }

        # 4. 根据 processing_method 分别处理
        success_count = 0
        failed_count = 0
        details = []

        for appointment in affected_appointments:
            try:
                result = await self._process_single_appointment(
                    appointment, suspension, processing_method, operator_id
                )
                if result["success"]:
                    success_count += 1
                else:
                    failed_count += 1
                details.append(result)
            except Exception as e:
                failed_count += 1
                details.append({
                    "appointment_id": appointment.id,
                    "success": False,
                    "error": str(e),
                })
                logger.warning(
                    f"处置预约失败: appointment_id={appointment.id}, "
                    f"method={processing_method}, error={e}"
                )

        # 5. 更新停诊记录状态
        if failed_count == 0:
            suspension.processing_status = "completed"
        elif success_count == 0:
            suspension.processing_status = "failed"
        else:
            # 部分成功仍标记为 completed，details 中可查看失败项
            suspension.processing_status = "completed"

        set_update_audit(suspension, operator_id)
        await self.db.commit()
        await self.db.refresh(suspension)

        # 6. 发送处置通知
        await self._send_processing_notifications(
            suspension, affected_appointments, processing_method, success_count
        )

        return {
            "suspension_id": suspension_id,
            "processing_method": processing_method,
            "processing_status": suspension.processing_status,
            "total_affected": len(affected_appointments),
            "success_count": success_count,
            "failed_count": failed_count,
            "details": details,
        }

    async def count_affected_appointments(self, suspension_id: str) -> int:
        """统计停诊影响的活跃预约数量"""
        suspension = await self._get_suspension(suspension_id)
        if not suspension:
            raise ValueError("停诊记录不存在")
        appointments = await self._find_affected_appointments(suspension)
        return len(appointments)

    # ---- 内部方法 ----

    async def _get_suspension(self, suspension_id: str) -> ScheduleSuspension | None:
        """获取停诊记录"""
        query = (
            select(ScheduleSuspension)
            .options(
                selectinload(ScheduleSuspension.store),
                selectinload(ScheduleSuspension.doctor),
            )
            .where(ScheduleSuspension.id == suspension_id)
        )
        tenant_id = self._tenant()
        if tenant_id:
            query = query.where(ScheduleSuspension.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _find_affected_appointments(
        self, suspension: ScheduleSuspension
    ) -> list[Appointment]:
        """查找停诊影响的所有活跃预约

        活跃预约: status IN (0待支付, 1已预约, 2已签到, 4就诊中)
        """
        # 获取受影响的排班 ID
        affected_schedule_ids = await self._get_affected_schedule_ids(suspension)
        if not affected_schedule_ids:
            return []

        conditions = [
            Appointment.schedule_id.in_(affected_schedule_ids),
            Appointment.status.in_(list(ACTIVE_APPOINTMENT_STATUSES)),
        ]
        if suspension.tenant_id:
            conditions.append(Appointment.tenant_id == suspension.tenant_id)

        result = await self.db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.schedule),
                selectinload(Appointment.user),
                selectinload(Appointment.patient),
            )
            .where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def _get_affected_schedule_ids(
        self, suspension: ScheduleSuspension
    ) -> list[str]:
        """获取停诊影响的排班 ID 列表"""
        if suspension.schedule_ids:
            try:
                return json.loads(suspension.schedule_ids)
            except Exception:
                return []

        # 无 schedule_ids 则按医生+日期查找已停诊的排班
        conditions = [
            Schedule.doctor_id == suspension.doctor_id,
            Schedule.schedule_date == suspension.suspension_date,
            Schedule.status == 0,
        ]
        if suspension.tenant_id:
            conditions.append(Schedule.tenant_id == suspension.tenant_id)

        result = await self.db.execute(select(Schedule.id).where(and_(*conditions)))
        return [row[0] for row in result.fetchall()]

    async def _process_single_appointment(
        self,
        appointment: Appointment,
        suspension: ScheduleSuspension,
        processing_method: str,
        operator_id: str | None = None,
    ) -> dict:
        """处理单个预约"""
        base_result = {
            "appointment_id": appointment.id,
            "patient_name": appointment.patient_name or (
                appointment.patient.name if appointment.patient else "未知"
            ),
            "processing_method": processing_method,
        }

        if processing_method == "auto_refund":
            return await self._auto_refund(appointment, suspension, operator_id, base_result)
        elif processing_method == "reschedule":
            return await self._mark_reschedule(appointment, suspension, operator_id, base_result)
        elif processing_method == "change_date":
            return await self._mark_change_date(appointment, suspension, operator_id, base_result)
        elif processing_method == "manual":
            return await self._mark_manual(appointment, suspension, operator_id, base_result)
        else:
            base_result["success"] = False
            base_result["error"] = f"未知处置方式: {processing_method}"
            return base_result

    async def _auto_refund(
        self,
        appointment: Appointment,
        suspension: ScheduleSuspension,
        operator_id: str | None,
        result: dict,
    ) -> dict:
        """自动取消预约并触发退款

        复用 service_booking.py 的取消+退款逻辑。
        """
        try:
            schedule = appointment.schedule

            # 已支付预约需要退款
            needs_refund = bool(
                appointment.payment_amount
                and appointment.payment_amount > 0
                and appointment.payment_transaction_id
            )

            appointment.status = APPOINTMENT_STATUS["CANCELLED"]
            appointment.cancel_time = datetime.now()
            appointment.cancel_reason = f"停诊自动取消（停诊ID: {suspension.id}）"
            set_update_audit(appointment, operator_id)

            if schedule:
                schedule.booked_slots = max(0, schedule.booked_slots - 1)

            if needs_refund:
                await self._trigger_refund(appointment, operator_id)

            result["success"] = True
            result["refunded"] = needs_refund
            result["payment_amount"] = float(appointment.payment_amount or 0)
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    async def _trigger_refund(self, appointment: Appointment, operator_id: str | None):
        """触发退款

        复用 AppointmentBookingService._refund_paid_appointment_on_cancel 的逻辑。
        """
        from app.infrastructure.payments.wechat_pay_service import WeChatPayService
        from app.models.miniapp_platform import PaymentProfile
        from app.modules.refunds.service import RefundService

        refund_service = RefundService(self.db)
        refund_record = await refund_service.create_refund(
            appointment_id=appointment.id,
            refund_amount=appointment.payment_amount,
            refund_reason="停诊自动退款",
            operator_id=operator_id or "system",
        )

        if not refund_record.payment_profile_id:
            raise ValueError("预约缺少支付配置快照，无法发起退款")

        profile_result = await self.db.execute(
            select(PaymentProfile).where(PaymentProfile.id == refund_record.payment_profile_id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            raise ValueError("退款关联的支付配置不存在")

        wx_service = WeChatPayService(profile)
        out_trade_no, transaction_id = await refund_service.ensure_refund_payment_reference(
            refund_record
        )

        wx_result = await wx_service.create_refund(
            out_trade_no=out_trade_no,
            out_refund_no=refund_record.refund_no,
            total=refund_record.original_amount,
            refund=refund_record.refund_amount,
            reason=refund_record.refund_reason or "",
            notify_url=profile.refund_notify_url or profile.notify_url or "",
            transaction_id=transaction_id,
        )

        refund_record.status = "processing"
        if wx_result.get("refund_id"):
            refund_record.wx_refund_id = wx_result.get("refund_id")
        await refund_service.sync_appointment_refund_state(refund_record.appointment_id)

    async def _mark_reschedule(
        self,
        appointment: Appointment,
        suspension: ScheduleSuspension,
        operator_id: str | None,
        result: dict,
    ) -> dict:
        """取消原预约、释放号源，通知患者选择同一科室的其他医生。

        事务原子性：预约状态更新 + 号源释放在同一事务中 commit。
        通知在 commit 后发送，失败仅 logger.warning。
        """
        schedule = appointment.schedule
        if not schedule:
            result["success"] = False
            result["error"] = "预约缺少排班信息"
            return result

        # 锁租户跟随预约归属，避免请求上下文缺失时跨租户争用
        tenant_id = appointment.tenant_id or self._tenant()

        try:
            async with RedisCache.tenant_distributed_lock(
                f"schedule:slot:{schedule.id}",
                tenant_id=tenant_id,
                timeout=10,
            ):
                # 重新加载预约（含 schedule 关联），避免竞态
                refreshed = await self.db.execute(
                    select(Appointment)
                    .options(selectinload(Appointment.schedule))
                    .where(Appointment.id == appointment.id)
                )
                appointment = refreshed.scalar_one()
                if not appointment or appointment.status not in ACTIVE_APPOINTMENT_STATUSES:
                    result["success"] = False
                    result["error"] = "预约已被其他操作处理"
                    return result

                # 释放号源
                schedule = appointment.schedule
                if schedule:
                    schedule.booked_slots = max(0, schedule.booked_slots - 1)

                # 更新预约状态
                original_id = appointment.id
                appointment.status = APPOINTMENT_STATUS["CANCELLED"]
                appointment.cancel_time = datetime.now()
                appointment.cancel_reason = f"停诊转约（停诊ID: {suspension.id}）"
                appointment.rescheduled_from_id = original_id
                appointment.remark = (
                    (appointment.remark or "")
                    + f"\n[停诊待转约] 停诊ID: {suspension.id}，请患者选择其他医生重新预约"
                )
                set_update_audit(appointment, operator_id)

                await self.db.commit()
                await self.db.refresh(appointment)

            result["success"] = True
            result["new_status"] = appointment.status

            # 通知在事务 commit 后发送，失败不回滚
            await self._notify_reschedule_patient(
                appointment, suspension, method="reschedule",
            )
        except Exception as e:
            await self.db.rollback()
            result["success"] = False
            result["error"] = str(e)

        return result

    async def _mark_change_date(
        self,
        appointment: Appointment,
        suspension: ScheduleSuspension,
        operator_id: str | None,
        result: dict,
    ) -> dict:
        """取消原预约、释放号源，通知患者选择同一医生的其他日期。

        事务原子性：预约状态更新 + 号源释放在同一事务中 commit。
        通知在 commit 后发送，失败仅 logger.warning。
        """
        schedule = appointment.schedule
        if not schedule:
            result["success"] = False
            result["error"] = "预约缺少排班信息"
            return result

        # 锁租户跟随预约归属，避免请求上下文缺失时跨租户争用
        tenant_id = appointment.tenant_id or self._tenant()

        try:
            async with RedisCache.tenant_distributed_lock(
                f"schedule:slot:{schedule.id}",
                tenant_id=tenant_id,
                timeout=10,
            ):
                # 重新加载预约（含 schedule 关联），避免竞态
                refreshed = await self.db.execute(
                    select(Appointment)
                    .options(selectinload(Appointment.schedule))
                    .where(Appointment.id == appointment.id)
                )
                appointment = refreshed.scalar_one()
                if not appointment or appointment.status not in ACTIVE_APPOINTMENT_STATUSES:
                    result["success"] = False
                    result["error"] = "预约已被其他操作处理"
                    return result

                # 释放号源
                schedule = appointment.schedule
                if schedule:
                    schedule.booked_slots = max(0, schedule.booked_slots - 1)

                # 更新预约状态
                original_id = appointment.id
                appointment.status = APPOINTMENT_STATUS["CANCELLED"]
                appointment.cancel_time = datetime.now()
                appointment.cancel_reason = f"停诊改期（停诊ID: {suspension.id}）"
                appointment.rescheduled_from_id = original_id
                appointment.remark = (
                    (appointment.remark or "")
                    + f"\n[停诊待改期] 停诊ID: {suspension.id}，请患者选择其他日期重新预约"
                )
                set_update_audit(appointment, operator_id)

                await self.db.commit()
                await self.db.refresh(appointment)

            result["success"] = True
            result["new_status"] = appointment.status

            # 通知在事务 commit 后发送，失败不回滚
            await self._notify_reschedule_patient(
                appointment, suspension, method="change_date",
            )
        except Exception as e:
            await self.db.rollback()
            result["success"] = False
            result["error"] = str(e)

        return result

    async def _mark_manual(
        self,
        appointment: Appointment,
        suspension: ScheduleSuspension,
        operator_id: str | None,
        result: dict,
    ) -> dict:
        """仅记录，等待人工处理"""
        try:
            appointment.remark = (
                (appointment.remark or "")
                + f"\n[停诊待人工处理] 停诊ID: {suspension.id}"
            )
            set_update_audit(appointment, operator_id)
            result["success"] = True
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
        return result

    async def _notify_reschedule_patient(
        self,
        appointment: Appointment,
        suspension: ScheduleSuspension,
        method: str,
    ):
        """发送转约/改期通知给患者。

        在事务 commit 后调用，失败仅 logger.warning 不回滚。
        """
        try:
            message_service = MessageService(self.db)
            doctor_name = (
                suspension.doctor.name if suspension.doctor else "医生"
            )
            suspension_date_str = suspension.suspension_date.strftime("%Y年%m月%d日")
            time_slot_display = self._get_time_slot_display(appointment)
            content = self._build_patient_notification(
                method, doctor_name, suspension_date_str, time_slot_display,
            )

            await message_service.send_stop_clinic_notification(
                user_id=appointment.user_id,
                user_type="patient",
                title=self._get_patient_title(method),
                content=content,
                appointment_id=appointment.id,
                template_code=f"suspension_{method}",
                template_variables={
                    "doctor_name": doctor_name,
                    "date": suspension_date_str,
                    "time_slot": time_slot_display,
                    "processing_method": method,
                },
            )
        except Exception as e:
            logger.warning(
                f"停诊处置通知发送失败 "
                f"(appointment_id={appointment.id}, method={method}): {e}"
            )

    async def _send_processing_notifications(
        self,
        suspension: ScheduleSuspension,
        appointments: list[Appointment],
        processing_method: str,
        success_count: int,
    ):
        """发送处置通知"""
        try:
            message_service = MessageService(self.db)
            doctor_name = (
                suspension.doctor.name if suspension.doctor else "医生"
            )
            suspension_date_str = suspension.suspension_date.strftime("%Y年%m月%d日")

            # 通知医生
            try:
                await message_service.send_schedule_notification(
                    doctor_id=suspension.doctor_id,
                    title="停诊患者处置通知",
                    content=(
                        f"您的排班（{suspension_date_str}）已停诊，"
                        f"影响 {len(appointments)} 名患者，"
                        f"处置方式：{self._method_display(processing_method)}，"
                        f"成功处置 {success_count} 名。"
                    ),
                )
            except Exception as e:
                logger.warning(f"医生停诊处置通知发送失败: {e}")

            # 通知患者
            for appointment in appointments:
                try:
                    time_slot_display = self._get_time_slot_display(appointment)
                    content = self._build_patient_notification(
                        processing_method, doctor_name,
                        suspension_date_str, time_slot_display,
                    )

                    await message_service.send_stop_clinic_notification(
                        user_id=appointment.user_id,
                        user_type="patient",
                        title=self._get_patient_title(processing_method),
                        content=content,
                        appointment_id=appointment.id,
                        template_code=f"suspension_{processing_method}",
                        template_variables={
                            "doctor_name": doctor_name,
                            "date": suspension_date_str,
                            "time_slot": time_slot_display,
                            "processing_method": processing_method,
                        },
                    )
                except Exception as e:
                    logger.warning(
                        f"停诊处置通知发送失败 "
                        f"(appointment_id={appointment.id}): {e}"
                    )

        except Exception as e:
            logger.warning(f"停诊处置通知批量发送失败: {e}")

    @staticmethod
    def _method_display(method: str) -> str:
        """处置方式中文显示"""
        return {
            "auto_refund": "自动退款",
            "reschedule": "转约",
            "change_date": "改期",
            "manual": "人工处理",
        }.get(method, method)

    @staticmethod
    def _get_patient_title(method: str) -> str:
        """获取患者通知标题"""
        return {
            "auto_refund": "预约已自动取消",
            "reschedule": "预约需要改约",
            "change_date": "预约需要改期",
            "manual": "预约待处理",
        }.get(method, "停诊处置通知")

    @staticmethod
    def _get_time_slot_display(appointment: Appointment) -> str:
        """获取时段显示"""
        if appointment.schedule:
            return {
                "morning": "上午",
                "afternoon": "下午",
                "evening": "晚间",
            }.get(appointment.schedule.time_slot, appointment.schedule.time_slot or "")
        return ""

    @staticmethod
    def _build_patient_notification(
        method: str, doctor_name: str,
        date_str: str, time_slot: str,
    ) -> str:
        """构建患者通知内容"""
        if method == "auto_refund":
            return (
                f"您预约的{doctor_name}医生（{date_str} {time_slot}）"
                f"因停诊已自动取消，退款将在 1-3 个工作日内到账。"
                f"给您带来不便敬请谅解。"
            )
        elif method == "reschedule":
            return (
                f"您预约的{doctor_name}医生（{date_str} {time_slot}）"
                f"因停诊需要改约，请选择其他医生或时间重新预约。"
                f"给您带来不便敬请谅解。"
            )
        elif method == "change_date":
            return (
                f"您预约的{doctor_name}医生（{date_str} {time_slot}）"
                f"因停诊需要改期，请选择其他日期重新预约。"
                f"给您带来不便敬请谅解。"
            )
        else:
            return (
                f"您预约的{doctor_name}医生（{date_str} {time_slot}）"
                f"因停诊需要处理，请等待工作人员联系您。"
                f"给您带来不便敬请谅解。"
            )
