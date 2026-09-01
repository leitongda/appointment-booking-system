"""排班更新 / 拖拽调整操作。"""

import json
from datetime import date

import pytz

from app.core.redis import RedisCache
from app.models.schedule import Schedule
from app.modules.schedules.audit_helpers import (
    compute_diff,
    make_schedule_audit,
    snapshot_schedule,
)
from app.modules.schedules.service_conflict import ScheduleConflictService
from app.schemas.schedule import ScheduleUpdate
from app.utils.audit import set_update_audit


class ScheduleMutationUpdateMixin:
    async def update(
        self, schedule_id: str, data: ScheduleUpdate, operator_id: str | None = None
    ) -> Schedule | None:
        from app.middleware.tenant_context import get_current_tenant_id
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return None

        # 租户隔离校验：防止跨租户修改
        tenant_id = get_current_tenant_id()
        if tenant_id and schedule.tenant_id and schedule.tenant_id != tenant_id:
            raise ValueError("无权修改此排班")

        update_data = data.model_dump(exclude_unset=True)

        # 冲突预检：当时间字段变更时，检测新时间段是否与其他排班冲突
        time_fields_changed = {"start_time", "end_time"} & set(update_data.keys())
        if time_fields_changed:
            new_start = update_data.get("start_time", schedule.start_time)
            new_end = update_data.get("end_time", schedule.end_time)
            if new_start and new_end:
                conflict_service = ScheduleConflictService(self.db)
                conflict_result = await conflict_service.check_conflicts(
                    doctor_id=schedule.doctor_id,
                    schedule_date=schedule.schedule_date,
                    start_time=new_start,
                    end_time=new_end,
                    time_slot=schedule.time_slot,
                    store_id=schedule.store_id,
                    room_id=update_data.get("room_id", schedule.room_id),
                    exclude_schedule_id=schedule_id,
                )
                if conflict_result.blocking:
                    error_msgs = [c.message for c in conflict_result.conflicts if c.severity == "error"]
                    raise ValueError(f"排班冲突: {'; '.join(error_msgs)}")

        # 号源拆分：如果传入了 quota 字段，自动计算 total_slots
        quota_fields = {"online_quota", "offline_quota", "reserved_quota", "extra_quota"}
        has_quota_update = quota_fields & set(update_data.keys())
        if has_quota_update:
            online = update_data.get("online_quota", schedule.online_quota or 0)
            offline = update_data.get("offline_quota", schedule.offline_quota or 0)
            reserved = update_data.get("reserved_quota", schedule.reserved_quota or 0)
            extra = update_data.get("extra_quota", schedule.extra_quota or 0)
            new_total = online + offline + reserved + extra
            if new_total < schedule.booked_slots:
                raise ValueError("号源总数不能小于已预约数")
            update_data["total_slots"] = new_total

        if "total_slots" in update_data and update_data["total_slots"] < schedule.booked_slots:
            raise ValueError("总号源数不能小于已预约数")

        for field, value in update_data.items():
            setattr(schedule, field, value)

        set_update_audit(schedule, operator_id)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def drag_adjust(
        self,
        schedule_id: str,
        target_date,
        target_start_time=None,
        target_end_time=None,
        target_time_slot=None,
        operator_id: str | None = None,
    ) -> dict:
        """拖拽调整排班位置（日期/时间）。

        返回: {"success": bool, "schedule": Optional[Schedule], "conflicts": Optional[ConflictCheckResponse], "message": str}
        """
        from app.middleware.tenant_context import get_current_tenant_id

        # 1. 获取排班
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return {"success": False, "schedule": None, "conflicts": None, "message": "排班不存在"}

        # 2. 租户隔离
        tenant_id = get_current_tenant_id()
        if schedule.tenant_id and tenant_id and schedule.tenant_id != tenant_id:
            return {"success": False, "schedule": None, "conflicts": None, "message": "无权修改此排班"}

        # 3. 拖拽限制检查
        # 3a. 已有预约不允许直接拖拽
        if schedule.booked_slots > 0:
            return {
                "success": False,
                "schedule": None,
                "conflicts": None,
                "message": f"该排班已有 {schedule.booked_slots} 个预约，不允许直接拖拽调整，请先处理预约",
            }

        # 3b. 停诊状态不允许拖拽
        if schedule.status == 0 or schedule.schedule_status == "suspended":
            return {"success": False, "schedule": None, "conflicts": None, "message": "停诊状态的排班不允许拖拽调整"}

        # 3c. 历史排班不允许拖拽
        if schedule.schedule_date < date.today():
            return {"success": False, "schedule": None, "conflicts": None, "message": "历史排班不允许调整"}

        # 4. 确定新位置
        new_start = target_start_time or schedule.start_time
        new_end = target_end_time or schedule.end_time
        new_slot = target_time_slot or schedule.time_slot

        # 5. 冲突检测
        conflict_service = ScheduleConflictService(self.db)

        conflict_result = await conflict_service.check_conflicts(
            doctor_id=schedule.doctor_id,
            schedule_date=target_date,
            start_time=new_start,
            end_time=new_end,
            time_slot=new_slot,
            store_id=schedule.store_id,
            room_id=schedule.room_id,
            exclude_schedule_id=schedule_id,
        )

        # 如果有 error 级别冲突，返回冲突信息（不阻止，让前端决定是否 force）
        if conflict_result.blocking:
            from app.schemas.schedule import ConflictCheckResponse, ConflictItemResponse

            return {
                "success": False,
                "schedule": None,
                "conflicts": ConflictCheckResponse(
                    has_conflict=True,
                    blocking=True,
                    conflicts=[
                        ConflictItemResponse(
                            type=c.type,
                            severity=c.severity,
                            message=c.message,
                            details=c.details,
                        )
                        for c in conflict_result.conflicts
                    ],
                ),
                "message": "存在冲突，请确认后重试",
            }

        # 6. 使用分布式锁防止并发拖拽冲突
        lock_name = f"schedule:drag:{schedule.doctor_id}:{target_date}"

        try:
            async with RedisCache.tenant_distributed_lock(lock_name, tenant_id=tenant_id, timeout=30, retry_times=3):
                # double-check after lock: 再次检查目标位置无冲突
                recheck = await conflict_service.check_conflicts(
                    doctor_id=schedule.doctor_id,
                    schedule_date=target_date,
                    start_time=new_start,
                    end_time=new_end,
                    time_slot=new_slot,
                    store_id=schedule.store_id,
                    exclude_schedule_id=schedule_id,
                )
                if recheck.blocking:
                    from app.schemas.schedule import ConflictCheckResponse, ConflictItemResponse

                    return {
                        "success": False,
                        "schedule": None,
                        "conflicts": ConflictCheckResponse(
                            has_conflict=True,
                            blocking=True,
                            conflicts=[
                                ConflictItemResponse(
                                    type=c.type,
                                    severity=c.severity,
                                    message=c.message,
                                    details=c.details,
                                )
                                for c in recheck.conflicts
                            ],
                        ),
                        "message": "目标位置已被占用",
                    }

                # 更新排班位置
                # 审计：快照变更前状态
                before = snapshot_schedule(schedule)
                before_json = json.dumps(before, ensure_ascii=False, default=str) if before else None

                schedule.schedule_date = target_date
                schedule.start_time = new_start
                schedule.end_time = new_end
                schedule.time_slot = new_slot

                # 更新 start_at/end_at（带时区）
                if new_start and new_end:
                    from datetime import datetime as dt_datetime

                    tz_name = schedule.timezone or "Asia/Shanghai"
                    tz = pytz.timezone(tz_name)
                    schedule.start_at = tz.localize(dt_datetime.combine(target_date, new_start))
                    schedule.end_at = tz.localize(dt_datetime.combine(target_date, new_end))

                set_update_audit(schedule, operator_id)

                # 审计：快照变更后状态并写入审计日志
                after = snapshot_schedule(schedule)
                after_json = json.dumps(after, ensure_ascii=False, default=str) if after else None
                changes_data = compute_diff(before, after)
                changes_json = json.dumps(changes_data, ensure_ascii=False, default=str) if changes_data else None
                audit_log = make_schedule_audit(
                    schedule_id=schedule.id,
                    tenant_id=schedule.tenant_id or "",
                    action="drag",
                    operator_id=operator_id,
                    snapshot_before=before_json,
                    snapshot_after=after_json,
                    changes=changes_json,
                )
                self.db.add(audit_log)

                await self.db.commit()
                await self.db.refresh(schedule)

                return {"success": True, "schedule": schedule, "conflicts": None, "message": "调整成功"}
        except RuntimeError:
            return {"success": False, "schedule": None, "conflicts": None, "message": "操作频繁，请稍后重试"}
