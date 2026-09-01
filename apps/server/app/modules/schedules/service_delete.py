"""排班删除（单条 / 批量）与状态转换校验。"""

import json

from sqlalchemy import and_, select

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.schedule_status import ScheduleStatus
from app.modules.schedules.audit_helpers import (
    make_schedule_audit,
    snapshot_schedule,
)


class ScheduleMutationDeleteMixin:
    async def delete(self, schedule_id: str) -> bool:
        from app.middleware.tenant_context import get_current_tenant_id
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            raise ValueError("排班不存在")

        # 租户隔离校验：防止跨租户删除
        tenant_id = get_current_tenant_id()
        if tenant_id and schedule.tenant_id and schedule.tenant_id != tenant_id:
            raise ValueError("无权删除此排班")

        appointments_result = await self.db.execute(
            select(Appointment.id).where(Appointment.schedule_id == schedule_id).limit(1)
        )
        if appointments_result.scalar_one_or_none():
            raise ValueError("该排班已有预约记录，无法删除")

        await self.db.delete(schedule)
        await self.db.commit()
        return True

    async def batch_delete(self, schedule_ids: list[str]) -> dict:
        """
        批量删除排班

        Args:
            schedule_ids: 排班ID列表

        Returns:
            包含详细结果的字典:
            success_count: 成功数量
            failed_count: 失败数量
            success_ids: 成功删除的ID列表
            failed_items: 失败项列表（包含原因）
            skipped_ids: 跳过的ID列表（有预约记录）
            deleted_count: 已删除数量
        """
        if not schedule_ids:
            return {
                "success_count": 0,
                "failed_count": 0,
                "success_ids": [],
                "failed_items": [],
                "skipped_ids": [],
                "deleted_count": 0,
                "message": "没有提供排班ID"
            }

        # 查询有预约记录的排班
        appointments_result = await self.db.execute(
            select(Appointment.schedule_id).where(Appointment.schedule_id.in_(schedule_ids)).distinct()
        )
        schedule_ids_with_appointments = {row[0] for row in appointments_result.fetchall()}

        # 分类：可删除的和需要跳过的
        deletable_schedule_ids = [sid for sid in schedule_ids if sid not in schedule_ids_with_appointments]
        skipped_ids = list(schedule_ids_with_appointments)

        if not deletable_schedule_ids:
            return {
                "success_count": 0,
                "failed_count": 0,
                "success_ids": [],
                "failed_items": [],
                "skipped_ids": skipped_ids,
                "deleted_count": 0,
                "message": "所有排班都有预约记录，无法删除"
            }

        # 租户隔离：仅删除当前租户下的排班
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        delete_conditions = [Schedule.id.in_(deletable_schedule_ids)]
        if tenant_id:
            delete_conditions.append(Schedule.tenant_id == tenant_id)

        result = await self.db.execute(select(Schedule).where(and_(*delete_conditions)))
        schedules = result.scalars().all()

        success_ids = []
        failed_items = []
        affected_count = 0

        for schedule in schedules:
            try:
                # 审计：快照删除前状态
                before = snapshot_schedule(schedule)
                before_json = json.dumps(before, ensure_ascii=False, default=str) if before else None
                audit_log = make_schedule_audit(
                    schedule_id=schedule.id,
                    tenant_id=schedule.tenant_id or "",
                    action="delete",
                    operator_id=None,
                    snapshot_before=before_json,
                    snapshot_after=None,
                    changes=None,
                )
                self.db.add(audit_log)

                await self.db.delete(schedule)
                success_ids.append(schedule.id)
                affected_count += 1
            except Exception as e:
                failed_items.append({
                    "schedule_id": schedule.id,
                    "reason": str(e)
                })

        if affected_count > 0:
            await self.db.commit()

        return {
            "success_count": affected_count,
            "failed_count": len(failed_items),
            "success_ids": success_ids,
            "failed_items": failed_items,
            "skipped_ids": skipped_ids,
            "deleted_count": affected_count,
            "message": f"成功删除 {affected_count} 个排班" + (f"，跳过 {len(skipped_ids)} 个有预约的排班" if skipped_ids else "")
        }

    @staticmethod
    def validate_schedule_transition(current: str, target: str) -> bool:
        """校验状态转换是否合法。

        Returns:
            True 如果转换合法

        Raises:
            ValueError 如果转换不合法
        """
        # 定义合法的转换映射
        transitions = {
            ScheduleStatus.DRAFT: {ScheduleStatus.PUBLISHED},
            ScheduleStatus.PUBLISHED: {
                ScheduleStatus.BOOKING,
                ScheduleStatus.WITHDRAWN,
                ScheduleStatus.FINISHED,
            },
            ScheduleStatus.BOOKING: {
                ScheduleStatus.FULL,
                ScheduleStatus.SUSPENDED,
                ScheduleStatus.WITHDRAWN,
                ScheduleStatus.FINISHED,
            },
            ScheduleStatus.FULL: {
                ScheduleStatus.SUSPENDED,
                ScheduleStatus.FINISHED,
            },
            ScheduleStatus.SUSPENDED: {
                ScheduleStatus.PUBLISHED,
                ScheduleStatus.BOOKING,
                ScheduleStatus.FINISHED,
            },
            ScheduleStatus.FINISHED: set(),
            ScheduleStatus.WITHDRAWN: set(),
        }

        allowed = transitions.get(current, set())
        if target not in allowed:
            raise ValueError(
                f"不允许的状态转换: {current} -> {target}，"
                f"允许的目标状态: {sorted(allowed) if allowed else '无'}"
            )
        return True
