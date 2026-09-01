"""排班批量停诊 / 恢复生命周期操作。"""

import json
import logging

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.schedule_status import ScheduleStatus
from app.modules.messages.service_messages import MessageService
from app.modules.schedules.audit_helpers import (
    compute_diff,
    make_schedule_audit,
    snapshot_schedule,
)

logger = logging.getLogger(__name__)


class ScheduleMutationBatchLifecycleMixin:
    async def batch_suspend(
        self,
        schedule_ids: list[str],
        reason: str | None = None,
        operator_id: str | None = None,
        processing_method: str | None = None,
    ) -> dict:
        """
        批量停诊排班

        P0修复：统一停诊操作路径，创建 ScheduleSuspension 记录，确保可以通过停诊管理恢复

        Args:
            schedule_ids: 排班ID列表
            reason: 停诊原因
            operator_id: 操作人ID
            processing_method: 处置方式 (auto_refund/reschedule/change_date/manual)，提供后自动处置

        Returns:
            包含详细结果的字典:
            success_count: 成功数量
            failed_count: 失败数量
            success_ids: 成功的ID列表
            failed_items: 失败项列表（包含原因）
            suspended_count: 已停诊数量
        """
        if not schedule_ids:
            return {
                "success_count": 0,
                "failed_count": 0,
                "success_ids": [],
                "failed_items": [],
                "suspended_count": 0,
                "message": "没有提供排班ID"
            }

        # 租户隔离：仅操作当前租户下的排班
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        conditions = [Schedule.id.in_(schedule_ids), Schedule.status == 1]
        if tenant_id:
            conditions.append(Schedule.tenant_id == tenant_id)

        result = await self.db.execute(
            select(Schedule)
            .options(selectinload(Schedule.doctor))
            .where(and_(*conditions))
        )
        schedules = result.scalars().all()

        # 找出不存在的排班
        existing_ids = {s.id for s in schedules}
        not_found_ids = [sid for sid in schedule_ids if sid not in existing_ids]

        success_ids = []
        failed_items = []
        affected_count = 0

        # 记录未找到的排班
        for sid in not_found_ids:
            failed_items.append({
                "schedule_id": sid,
                "reason": "排班不存在或已停诊"
            })

        # P0修复：按门店和医生分组创建停诊记录
        # 使用统一的工具函数进行分组
        from app.models.schedule_suspension import ScheduleSuspension
        from app.utils.audit import set_create_audit
        from app.utils.schedule_utils import create_suspension_records, group_schedules_for_suspension

        schedule_map = {s.id: s for s in schedules}

        # 使用工具函数分组
        suspension_groups = group_schedules_for_suspension(schedules, tenant_id)

        # 使用工具函数生成停诊记录数据
        suspension_records = create_suspension_records(
            suspension_groups, reason, tenant_id, operator_id
        )

        # 创建停诊记录并更新排班状态
        created_suspension_ids = []
        for record_data in suspension_records:
            try:
                suspension = ScheduleSuspension(
                    id=record_data["id"],
                    tenant_id=record_data["tenant_id"],
                    store_id=record_data["store_id"],
                    doctor_id=record_data["doctor_id"],
                    title=record_data["title"],
                    suspension_date=record_data["suspension_date"],
                    schedule_ids=record_data["schedule_ids"],
                    time_slots=record_data["time_slots"],
                    status=record_data["status"],
                    suspension_type="batch" if len(suspension_records) > 1 else "temporary",
                    processing_method=processing_method,
                    processing_status="pending" if processing_method else "pending",
                    affected_appointment_count=0,
                    reason=reason,
                )
                set_create_audit(suspension, operator_id)
                self.db.add(suspension)

                # 更新排班状态 (legacy + 新状态)
                sched_ids = json.loads(record_data["schedule_ids"])
                for sched_id in sched_ids:
                    schedule = schedule_map.get(sched_id)
                    if schedule:
                        # 审计：快照变更前状态
                        before = snapshot_schedule(schedule)
                        before_json = json.dumps(before, ensure_ascii=False, default=str) if before else None

                        schedule.status = 0
                        schedule.schedule_status = ScheduleStatus.SUSPENDED

                        # 审计：快照变更后状态并写入审计日志
                        after = snapshot_schedule(schedule)
                        after_json = json.dumps(after, ensure_ascii=False, default=str) if after else None
                        changes_data = compute_diff(before, after)
                        changes_json = json.dumps(changes_data, ensure_ascii=False, default=str) if changes_data else None
                        audit_log = make_schedule_audit(
                            schedule_id=schedule.id,
                            tenant_id=schedule.tenant_id or "",
                            action="suspend",
                            operator_id=operator_id,
                            snapshot_before=before_json,
                            snapshot_after=after_json,
                            changes=changes_json,
                        )
                        self.db.add(audit_log)

                        success_ids.append(sched_id)
                        affected_count += 1
                created_suspension_ids.append(record_data["id"])
            except Exception as e:
                # 记录失败
                sched_ids = json.loads(record_data["schedule_ids"])
                for sched_id in sched_ids:
                    failed_items.append({
                        "schedule_id": sched_id,
                        "reason": f"创建停诊记录失败: {str(e)}"
                    })

        if affected_count > 0:
            await self.db.commit()
            # 发送停诊通知
            await self._send_batch_suspend_notifications(
                [schedule_map[sid] for sid in success_ids if sid in schedule_map],
                reason
            )

            # 如果指定了处置方式，自动执行患者处置
            if processing_method and created_suspension_ids:
                from app.modules.schedule_suspensions.service_processing import SuspensionProcessingService
                processing_service = SuspensionProcessingService(self.db)
                for suspension_id in created_suspension_ids:
                    try:
                        await processing_service.process_suspension(
                            suspension_id=suspension_id,
                            processing_method=processing_method,
                            operator_id=operator_id,
                        )
                    except Exception as e:
                        logger.warning(f"批量停诊自动处置失败 (suspension_id={suspension_id}): {e}")

        return {
            "success_count": affected_count,
            "failed_count": len(failed_items),
            "success_ids": success_ids,
            "failed_items": failed_items,
            "suspended_count": affected_count,
            "message": f"成功停诊 {affected_count} 个排班" + (f"，失败 {len(failed_items)} 个" if failed_items else "")
        }

    async def _send_batch_suspend_notifications(
        self, schedules: list[Schedule], reason: str | None = None
    ):
        """发送批量停诊通知（医生 + 患者）

        患者通知内容包含：
        - 停诊医生、日期、时段等核心信息
        - 停诊原因（如有）
        - 操作指引（重新预约、联系方式）
        - 确保 SMS 降级时关键信息不丢失
        """
        try:
            schedule_ids = [s.id for s in schedules]
            if not schedule_ids:
                return

            message_service = MessageService(self.db)

            # 获取门店联系方式（用于患者通知中的联系信息）
            store_phone = None
            if schedules:
                first_schedule = schedules[0]
                if first_schedule.store_id:
                    from app.models.store import Store
                    store_result = await self.db.execute(
                        select(Store.phone).where(Store.id == first_schedule.store_id)
                    )
                    store_phone = store_result.scalar_one_or_none()

            doctor_schedules = {}
            for schedule in schedules:
                doctor_schedules.setdefault(schedule.doctor_id, []).append(schedule)

            for doctor_id, doc_schedules in doctor_schedules.items():
                try:
                    dates = sorted(set(s.schedule_date for s in doc_schedules))
                    date_str = (
                        dates[0].strftime("%Y年%m月%d日")
                        if len(dates) == 1
                        else f"{dates[0].strftime('%Y年%m月%d日')} 至 {dates[-1].strftime('%Y年%m月%d日')}"
                    )
                    reason_text = f"（原因：{reason}）" if reason else ""
                    await message_service.send_schedule_notification(
                        doctor_id=doctor_id,
                        title="排班停诊通知",
                        content=f"您的 {len(doc_schedules)} 个排班已被停诊（{date_str}）{reason_text}。如有疑问请联系管理员。",
                        schedule_id=doc_schedules[0].id if len(doc_schedules) == 1 else None,
                    )
                except Exception as e:
                    logger.warning(f"医生停诊通知发送失败 (doctor_id={doctor_id}): {e}")

            appointments_result = await self.db.execute(
                select(Appointment)
                .options(selectinload(Appointment.schedule))
                .where(and_(Appointment.schedule_id.in_(schedule_ids), Appointment.status.in_([1, 2])))
            )
            appointments = appointments_result.scalars().all()
            if not appointments:
                return

            schedule_map = {s.id: s for s in schedules}
            for appointment in appointments:
                try:
                    schedule = schedule_map.get(appointment.schedule_id)
                    if not schedule:
                        continue

                    doctor_name = schedule.doctor.name if schedule.doctor else appointment.doctor_name or "医生"
                    schedule_date_str = schedule.schedule_date.strftime("%Y年%m月%d日")
                    time_slot_display = {
                        "morning": "上午",
                        "afternoon": "下午",
                        "evening": "晚间",
                    }.get(schedule.time_slot, schedule.time_slot or "")
                    reason_text = f"原因：{reason}。" if reason else ""

                    # 构建操作指引（确保 SMS 降级时关键信息完整）
                    action_parts = ["请您重新预约其他时间。"]
                    if store_phone:
                        action_parts.append(f"如需帮助请联系：{store_phone}。")
                    action_parts.append("您也可以通过APP查看其他可预约时段。")
                    action_text = "".join(action_parts)

                    # 确保 SMS 降级时内容完整：
                    # - 包含医生名、日期、时段、原因、联系方式、操作指引
                    # - 纯文本格式，无富文本标记
                    content = (
                        f"您预约的{doctor_name}医生（{schedule_date_str} {time_slot_display}）因故停诊。"
                        f"{reason_text}给您带来不便敬请谅解。{action_text}"
                    )

                    await message_service.send_stop_clinic_notification(
                        user_id=appointment.user_id,
                        user_type="patient",
                        title="停诊通知",
                        content=content,
                        appointment_id=appointment.id,
                        template_variables={
                            "doctor_name": doctor_name,
                            "date": schedule_date_str,
                            "time_slot": time_slot_display,
                            "reason": reason or "",
                            "store_phone": store_phone or "",
                            "action": "请重新预约其他时间",
                        },
                    )
                except Exception as e:
                    logger.warning(f"停诊通知发送失败 (appointment_id={appointment.id}): {e}")
        except Exception as e:
            logger.warning(f"批量停诊通知发送失败: {e}")

    async def batch_resume(self, schedule_ids: list[str], operator_id: str | None = None) -> int:
        """
        批量恢复排班

        P0修复：统一恢复操作路径，通过取消 ScheduleSuspension 记录来恢复排班

        Args:
            schedule_ids: 排班ID列表
            operator_id: 操作人ID

        Returns:
            恢复的排班数量
        """
        # 审计辅助：为单个排班记录 resume 审计
        def _audit_resume(schedule):
            before = snapshot_schedule(schedule)
            before_json = json.dumps(before, ensure_ascii=False, default=str) if before else None
            schedule.status = 1
            schedule.schedule_status = ScheduleStatus.PUBLISHED
            after = snapshot_schedule(schedule)
            after_json = json.dumps(after, ensure_ascii=False, default=str) if after else None
            changes_data = compute_diff(before, after)
            changes_json = json.dumps(changes_data, ensure_ascii=False, default=str) if changes_data else None
            audit_log = make_schedule_audit(
                schedule_id=schedule.id,
                tenant_id=schedule.tenant_id or "",
                action="resume",
                operator_id=operator_id,
                snapshot_before=before_json,
                snapshot_after=after_json,
                changes=changes_json,
            )
            self.db.add(audit_log)
        if not schedule_ids:
            return 0

        # 租户隔离：仅恢复当前租户下的排班
        from app.middleware.tenant_context import get_current_tenant_id
        from app.models.schedule_suspension import ScheduleSuspension
        from app.utils.audit import set_update_audit

        tenant_id = get_current_tenant_id()
        conditions = [Schedule.id.in_(schedule_ids), Schedule.status == 0]
        if tenant_id:
            conditions.append(Schedule.tenant_id == tenant_id)

        result = await self.db.execute(
            select(Schedule).where(and_(*conditions))
        )
        schedules = result.scalars().all()

        if not schedules:
            return 0

        # P0修复：查找并取消相关的停诊记录
        affected_count = 0
        processed_suspension_ids = set()

        for schedule in schedules:
            # 查找包含该排班ID的停诊记录
            suspension_conditions = [
                ScheduleSuspension.doctor_id == schedule.doctor_id,
                ScheduleSuspension.suspension_date == schedule.schedule_date,
                ScheduleSuspension.status == 1  # 仅处理生效中的停诊
            ]
            if tenant_id:
                suspension_conditions.append(ScheduleSuspension.tenant_id == tenant_id)

            suspensions_result = await self.db.execute(
                select(ScheduleSuspension).where(and_(*suspension_conditions))
            )
            suspensions = suspensions_result.scalars().all()

            for suspension in suspensions:
                if suspension.id in processed_suspension_ids:
                    continue

                # 检查该停诊记录是否包含当前排班
                should_cancel = False
                if suspension.schedule_ids:
                    try:
                        suspension_schedule_ids = json.loads(suspension.schedule_ids)
                        if schedule.id in suspension_schedule_ids:
                            # 从 schedule_ids 中移除该排班
                            suspension_schedule_ids.remove(schedule.id)
                            if suspension_schedule_ids:
                                suspension.schedule_ids = json.dumps(suspension_schedule_ids)
                            else:
                                # 如果没有其他排班了，取消整个停诊记录
                                should_cancel = True
                    except Exception:
                        pass

                    if not should_cancel:
                        # 如果还有其他排班，只更新 schedule_ids
                        set_update_audit(suspension, operator_id)
                else:
                    # 如果停诊记录没有指定 schedule_ids，说明是全天停诊
                    # 需要检查该医生该日期是否还有其他停诊的排班
                    other_suspended_result = await self.db.execute(
                        select(Schedule).where(
                            and_(
                                Schedule.doctor_id == schedule.doctor_id,
                                Schedule.schedule_date == schedule.schedule_date,
                                Schedule.status == 0,
                                Schedule.id != schedule.id  # 排除当前排班
                            )
                        )
                    )
                    other_suspended = other_suspended_result.scalars().first()

                    if not other_suspended:
                        # 没有其他停诊排班了，可以取消停诊记录
                        should_cancel = True
                    else:
                        # 还有其他停诊排班，不取消停诊记录
                        pass

                if should_cancel:
                    # 取消停诊记录
                    suspension.status = 0
                    set_update_audit(suspension, operator_id)
                    # 恢复该停诊记录关联的所有排班
                    if suspension.schedule_ids:
                        try:
                            suspension_schedule_ids = json.loads(suspension.schedule_ids)
                            for sid in suspension_schedule_ids:
                                s_result = await self.db.execute(
                                    select(Schedule).where(Schedule.id == sid)
                                )
                                s = s_result.scalar_one_or_none()
                                if s and s.status == 0:
                                    _audit_resume(s)
                                    affected_count += 1
                        except Exception:
                            pass
                    else:
                        # 全天停诊，恢复该医生该日期所有停诊的排班
                        all_suspended_result = await self.db.execute(
                            select(Schedule).where(
                                and_(
                                    Schedule.doctor_id == suspension.doctor_id,
                                    Schedule.schedule_date == suspension.suspension_date,
                                    Schedule.status == 0
                                )
                            )
                        )
                        all_suspended = all_suspended_result.scalars().all()
                        for s in all_suspended:
                            _audit_resume(s)
                            affected_count += 1

                    processed_suspension_ids.add(suspension.id)
                else:
                    # 只恢复当前排班
                    _audit_resume(schedule)
                    affected_count += 1

            if not suspensions:
                # 如果没有找到停诊记录，直接恢复排班状态
                _audit_resume(schedule)
                affected_count += 1

        if affected_count > 0:
            await self.db.commit()

        return affected_count
