"""排班发布 / 批量发布 / 撤回操作（状态机相关）。"""

import json

from sqlalchemy import and_, select

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.schedule_status import ScheduleStatus
from app.modules.schedules.audit_helpers import (
    compute_diff,
    make_schedule_audit,
    snapshot_schedule,
)
from app.utils.audit import set_update_audit


class ScheduleMutationPublishMixin:
    # ========== 排班发布状态机操作 ==========

    async def publish(self, schedule_id: str, operator_id: str | None = None) -> Schedule:
        """
        发布排班: draft -> published

        只有 draft 状态的排班可以发布。
        """
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            raise ValueError("排班不存在")

        if schedule.schedule_status != ScheduleStatus.DRAFT:
            raise ValueError(
                f"当前排班状态为 [{schedule.schedule_status}]，只有 draft 状态的排班可以发布"
            )

        # 审计：快照变更前状态
        before = snapshot_schedule(schedule)
        before_json = json.dumps(before, ensure_ascii=False, default=str) if before else None

        schedule.schedule_status = ScheduleStatus.PUBLISHED
        schedule.status = 1  # 同步 legacy 字段
        set_update_audit(schedule, operator_id)

        # 审计：快照变更后状态并写入审计日志
        after = snapshot_schedule(schedule)
        after_json = json.dumps(after, ensure_ascii=False, default=str) if after else None
        changes_data = compute_diff(before, after)
        changes_json = json.dumps(changes_data, ensure_ascii=False, default=str) if changes_data else None
        audit_log = make_schedule_audit(
            schedule_id=schedule.id,
            tenant_id=schedule.tenant_id or "",
            action="publish",
            operator_id=operator_id,
            snapshot_before=before_json,
            snapshot_after=after_json,
            changes=changes_json,
        )
        self.db.add(audit_log)

        await self.db.commit()
        await self.db.refresh(schedule)

        # 创建预期考勤记录
        from app.modules.attendance_records.service import AttendanceRecordService
        await AttendanceRecordService.create_expected_records(self.db, schedule)

        return schedule

    async def batch_publish(
        self, schedule_ids: list[str], operator_id: str | None = None
    ) -> dict:
        """
        批量发布排班: draft -> published

        Args:
            schedule_ids: 排班ID列表
            operator_id: 操作人ID

        Returns:
            包含详细结果的字典
        """
        if not schedule_ids:
            return {
                "success_count": 0,
                "failed_count": 0,
                "success_ids": [],
                "failed_items": [],
                "message": "没有提供排班ID",
            }

        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        conditions = [
            Schedule.id.in_(schedule_ids),
            Schedule.schedule_status == ScheduleStatus.DRAFT,
        ]
        if tenant_id:
            conditions.append(Schedule.tenant_id == tenant_id)

        result = await self.db.execute(select(Schedule).where(and_(*conditions)))
        schedules = result.scalars().all()

        existing_ids = {s.id for s in schedules}
        not_found_ids = [sid for sid in schedule_ids if sid not in existing_ids]

        success_ids = []
        failed_items = []
        for sid in not_found_ids:
            failed_items.append({
                "schedule_id": sid,
                "reason": "排班不存在或不是 draft 状态",
            })

        for schedule in schedules:
            # 审计：快照变更前状态
            before = snapshot_schedule(schedule)
            before_json = json.dumps(before, ensure_ascii=False, default=str) if before else None

            schedule.schedule_status = ScheduleStatus.PUBLISHED
            schedule.status = 1
            set_update_audit(schedule, operator_id)

            # 审计：快照变更后状态并写入审计日志
            after = snapshot_schedule(schedule)
            after_json = json.dumps(after, ensure_ascii=False, default=str) if after else None
            changes_data = compute_diff(before, after)
            changes_json = json.dumps(changes_data, ensure_ascii=False, default=str) if changes_data else None
            audit_log = make_schedule_audit(
                schedule_id=schedule.id,
                tenant_id=schedule.tenant_id or "",
                action="publish",
                operator_id=operator_id,
                snapshot_before=before_json,
                snapshot_after=after_json,
                changes=changes_json,
            )
            self.db.add(audit_log)
            success_ids.append(schedule.id)

        if success_ids:
            await self.db.commit()

            # 为已发布的排班创建预期考勤记录
            from app.modules.attendance_records.service import AttendanceRecordService
            for schedule in schedules:
                if schedule.id in success_ids:
                    await AttendanceRecordService.create_expected_records(self.db, schedule)

        return {
            "success_count": len(success_ids),
            "failed_count": len(failed_items),
            "success_ids": success_ids,
            "failed_items": failed_items,
            "message": f"成功发布 {len(success_ids)} 个排班"
            + (f"，失败 {len(failed_items)} 个" if failed_items else ""),
        }

    async def withdraw(
        self,
        schedule_ids: list[str],
        reason: str | None = None,
        operator_id: str | None = None,
    ) -> dict:
        """
        撤回排班: published/booking -> withdrawn

        仅当排班没有活跃预约时允许撤回。
        活跃预约 = status IN (0待支付, 1已预约, 2已签到, 4就诊中)。

        Args:
            schedule_ids: 排班ID列表
            reason: 撤回原因（可选）
            operator_id: 操作人ID

        Returns:
            包含详细结果的字典
        """
        if not schedule_ids:
            return {
                "success_count": 0,
                "failed_count": 0,
                "success_ids": [],
                "failed_items": [],
                "message": "没有提供排班ID",
            }

        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        allowed_statuses = {ScheduleStatus.PUBLISHED, ScheduleStatus.BOOKING}
        conditions = [
            Schedule.id.in_(schedule_ids),
            Schedule.schedule_status.in_(list(allowed_statuses)),
        ]
        if tenant_id:
            conditions.append(Schedule.tenant_id == tenant_id)

        result = await self.db.execute(select(Schedule).where(and_(*conditions)))
        schedules = result.scalars().all()

        existing_ids = {s.id for s in schedules}
        not_found_ids = [sid for sid in schedule_ids if sid not in existing_ids]

        success_ids = []
        failed_items = []
        for sid in not_found_ids:
            failed_items.append({
                "schedule_id": sid,
                "reason": "排班不存在或当前状态不允许撤回（仅 published/booking 可撤回）",
            })

        # 检查是否有活跃预约
        if schedules:
            active_appointments_result = await self.db.execute(
                select(Appointment.schedule_id)
                .where(
                    and_(
                        Appointment.schedule_id.in_([s.id for s in schedules]),
                        Appointment.status.in_([0, 1, 2, 4]),
                    )
                )
                .distinct()
            )
            schedules_with_active = {
                row[0] for row in active_appointments_result.fetchall()
            }
        else:
            schedules_with_active = set()

        for schedule in schedules:
            if schedule.id in schedules_with_active:
                failed_items.append({
                    "schedule_id": schedule.id,
                    "reason": "该排班存在活跃预约，无法撤回",
                })
                continue

            # 审计：快照变更前状态
            before = snapshot_schedule(schedule)
            before_json = json.dumps(before, ensure_ascii=False, default=str) if before else None

            schedule.schedule_status = ScheduleStatus.WITHDRAWN
            set_update_audit(schedule, operator_id)

            # 审计：快照变更后状态并写入审计日志
            after = snapshot_schedule(schedule)
            after_json = json.dumps(after, ensure_ascii=False, default=str) if after else None
            changes_data = compute_diff(before, after)
            changes_json = json.dumps(changes_data, ensure_ascii=False, default=str) if changes_data else None
            audit_log = make_schedule_audit(
                schedule_id=schedule.id,
                tenant_id=schedule.tenant_id or "",
                action="withdraw",
                operator_id=operator_id,
                snapshot_before=before_json,
                snapshot_after=after_json,
                changes=changes_json,
            )
            self.db.add(audit_log)
            success_ids.append(schedule.id)

        if success_ids:
            await self.db.commit()

        return {
            "success_count": len(success_ids),
            "failed_count": len(failed_items),
            "success_ids": success_ids,
            "failed_items": failed_items,
            "message": f"成功撤回 {len(success_ids)} 个排班"
            + (f"，失败 {len(failed_items)} 个" if failed_items else ""),
        }
