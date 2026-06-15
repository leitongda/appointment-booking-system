"""Mutation-oriented schedule operations."""

import json
import logging
import uuid
from datetime import date

import pytz
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.redis import RedisCache
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.schedule_status import ScheduleStatus
from app.modules.messages.service_messages import MessageService
from app.modules.schedules.audit_helpers import (
    compute_diff,
    make_schedule_audit,
    snapshot_schedule,
)
from app.modules.schedules.service_conflict import ScheduleConflictService
from app.schemas.schedule import (
    ScheduleBatchCopyRequest,
    ScheduleBatchCopyResult,
    ScheduleBatchCreate,
    ScheduleCreate,
    ScheduleUpdate,
)
from app.utils.audit import set_create_audit, set_update_audit
from app.utils.schedule_utils import get_time_slot_from_time

logger = logging.getLogger(__name__)


class ScheduleMutationMixin:
    async def create(self, data: ScheduleCreate, operator_id: str | None = None) -> Schedule:
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        time_slot = data.time_slot
        if not time_slot and data.start_time:
            time_slot = get_time_slot_from_time(data.start_time)
        elif not time_slot:
            raise ValueError("必须提供 time_slot 或 start_time")

        # 冲突预检：检测医生时间重叠、节假日、休息日、医生状态等
        conflict_service = ScheduleConflictService(self.db)
        conflict_result = await conflict_service.check_conflicts(
            doctor_id=data.doctor_id,
            schedule_date=data.schedule_date,
            start_time=data.start_time,
            end_time=data.end_time,
            time_slot=time_slot,
            store_id=data.store_id,
            room_id=data.room_id,
        )
        if conflict_result.blocking:
            error_msgs = [c.message for c in conflict_result.conflicts if c.severity == "error"]
            raise ValueError(f"排班冲突: {'; '.join(error_msgs)}")

        # P1修复：使用租户隔离的分布式锁，避免不同租户的排班创建互相阻塞
        # 锁的粒度：租户+医生+日期+时间段
        lock_key_parts = [data.doctor_id, str(data.schedule_date)]
        if data.start_time and data.end_time:
            lock_key_parts.extend([str(data.start_time), str(data.end_time)])
        else:
            lock_key_parts.append(time_slot)
        lock_name = f"schedule:create:{':'.join(lock_key_parts)}"

        async with RedisCache.tenant_distributed_lock(lock_name, tenant_id=tenant_id, timeout=10, retry_times=5):
            conditions = [
                Schedule.doctor_id == data.doctor_id,
                Schedule.schedule_date == data.schedule_date,
            ]
            if data.start_time and data.end_time:
                conditions.append(Schedule.start_time == data.start_time)
                conditions.append(Schedule.end_time == data.end_time)
            else:
                conditions.append(Schedule.time_slot == time_slot)

            existing = await self.db.execute(select(Schedule).where(and_(*conditions)))
            existing_schedule = existing.scalar_one_or_none()

            if existing_schedule:
                is_new_custom = data.template_id is None
                is_existing_normal = existing_schedule.template_id is not None
                is_existing_suspended = existing_schedule.status == 0

                if is_existing_suspended:
                    raise ValueError("该时段已停诊，无法创建排班")

                if is_new_custom and is_existing_normal:
                    if existing_schedule.booked_slots > 0:
                        raise ValueError("该时段普通排班已有预约，无法覆盖")
                    await self.db.delete(existing_schedule)
                    await self.db.flush()
                else:
                    raise ValueError("该时段排班已存在")

            store_id = data.store_id
            if not store_id:
                doctor_result = await self.db.execute(select(Doctor).where(Doctor.id == data.doctor_id, Doctor.deleted_at.is_(None)))
                doctor = doctor_result.scalar_one_or_none()
                if doctor:
                    store_id = doctor.store_id

            # 推导 schedule_status
            if data.schedule_status:
                schedule_status = data.schedule_status
            else:
                schedule_status = (
                    ScheduleStatus.SUSPENDED if data.status == 0
                    else ScheduleStatus.PUBLISHED
                )

            # 号源拆分：计算 total_slots
            online_quota = data.online_quota or 0
            offline_quota = data.offline_quota or 0
            reserved_quota = data.reserved_quota or 0
            extra_quota = data.extra_quota or 0
            quota_sum = online_quota + offline_quota + reserved_quota + extra_quota
            # 如果 quota 字段均为 0（未传），回退到 data.total_slots
            total_slots = quota_sum if quota_sum > 0 else data.total_slots

            schedule = Schedule(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                doctor_id=data.doctor_id,
                store_id=store_id,
                template_id=data.template_id,
                schedule_date=data.schedule_date,
                time_slot=time_slot,
                start_time=data.start_time,
                end_time=data.end_time,
                total_slots=total_slots,
                booked_slots=0,
                online_quota=online_quota if quota_sum > 0 else total_slots,
                offline_quota=offline_quota,
                reserved_quota=reserved_quota,
                extra_quota=extra_quota,
                fee=data.fee or 0,
                appointment_type=data.appointment_type or "normal",
                status=data.status,
                schedule_status=schedule_status,
            )
            set_create_audit(schedule, operator_id)
            self.db.add(schedule)
            try:
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
                raise ValueError("该时段排班已存在（并发冲突）")
            await self.db.refresh(schedule)

        # 在锁外发送通知，避免阻塞
        if data.template_id is None:
            await self._send_schedule_notification_to_doctor(
                doctor_id=data.doctor_id,
                title="新增排班通知",
                content=f"您有新增排班：{data.schedule_date.strftime('%Y年%m月%d日')}，请及时查看。",
                schedule_id=schedule.id,
            )

        return schedule

    async def batch_create(self, data: ScheduleBatchCreate, operator_id: str | None = None) -> int:
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        doctor_result = await self.db.execute(select(Doctor).where(Doctor.id == data.doctor_id, Doctor.deleted_at.is_(None)))
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            raise ValueError("医生不存在")

        store_id = doctor.store_id
        created_count = 0
        current_date = data.start_date

        while current_date <= data.end_date:
            weekday = current_date.isoweekday()
            if weekday in data.weekdays:
                for time_slot in data.time_slots:
                    existing = await self.db.execute(
                        select(Schedule).where(
                            and_(
                                Schedule.doctor_id == data.doctor_id,
                                Schedule.schedule_date == current_date,
                                Schedule.time_slot == time_slot,
                            )
                        )
                    )
                    if not existing.scalar_one_or_none():
                        # 号源拆分：批量创建同样支持 quota 字段
                        online_quota = data.online_quota or 0
                        offline_quota = data.offline_quota or 0
                        reserved_quota = data.reserved_quota or 0
                        extra_quota = data.extra_quota or 0
                        quota_sum = online_quota + offline_quota + reserved_quota + extra_quota
                        total_slots = quota_sum if quota_sum > 0 else data.total_slots

                        schedule = Schedule(
                            id=str(uuid.uuid4()),
                            tenant_id=tenant_id,
                            doctor_id=data.doctor_id,
                            store_id=store_id,
                            schedule_date=current_date,
                            time_slot=time_slot,
                            total_slots=total_slots,
                            booked_slots=0,
                            online_quota=online_quota if quota_sum > 0 else total_slots,
                            offline_quota=offline_quota,
                            reserved_quota=reserved_quota,
                            extra_quota=extra_quota,
                            fee=data.fee or 0,
                            appointment_type="normal",
                            status=1,
                            schedule_status=ScheduleStatus.PUBLISHED,
                        )
                        set_create_audit(schedule, operator_id)
                        self.db.add(schedule)
                        created_count += 1
            current_date = current_date.fromordinal(current_date.toordinal() + 1)

        await self.db.commit()

        if created_count > 0:
            await self._send_schedule_notification_to_doctor(
                doctor_id=data.doctor_id,
                title="批量排班通知",
                content=(
                    f"您有 {created_count} 个新排班已创建"
                    f"（{data.start_date.strftime('%Y年%m月%d日')} 至 {data.end_date.strftime('%Y年%m月%d日')}），请及时查看。"
                ),
                schedule_id=None,
            )

        return created_count

    async def batch_copy(
        self,
        data: ScheduleBatchCopyRequest,
        operator_id: str | None = None,
    ) -> ScheduleBatchCopyResult:
        """批量复制排班：源周期 -> 目标周期。

        核心逻辑:
        1. 查询源周期排班（按 doctor_ids 过滤）
        2. 计算日期偏移量（target_start_date - source_start_date）
        3. 对每个源排班生成偏移后的目标日期
        4. 批量冲突检测
        5. 按 conflict_strategy 处理冲突
        6. 按 copy_* 标志决定是否复制号源/诊室/费用
        """
        from datetime import timedelta

        from app.middleware.tenant_context import get_current_tenant_id
        from app.models.rest_day import RestDay
        from app.models.schedule_holiday import ScheduleHoliday
        from app.modules.schedules.service_conflict import ScheduleCheckItem
        from app.utils.schedule_utils import is_rest_day

        tenant_id = get_current_tenant_id()

        # 计算日期偏移
        offset_days = (data.target_start_date - data.source_start_date).days

        # 构建源查询条件
        source_conditions = [
            Schedule.schedule_date >= data.source_start_date,
            Schedule.schedule_date <= data.source_end_date,
            Schedule.status == 1,
        ]
        if tenant_id:
            source_conditions.append(Schedule.tenant_id == tenant_id)
        if data.doctor_ids:
            source_conditions.append(Schedule.doctor_id.in_(data.doctor_ids))

        source_result = await self.db.execute(
            select(Schedule).where(and_(*source_conditions))
        )
        source_schedules = list(source_result.scalars().all())
        total_source = len(source_schedules)

        if not source_schedules:
            return ScheduleBatchCopyResult(total_source=0, copied=0, skipped=0, overwritten=0, failed=0)

        # 预加载节假日（用于 skip_holidays 过滤）
        holidays = []
        if data.skip_holidays:
            holiday_conditions = [
                ScheduleHoliday.holiday_date >= data.target_start_date,
                ScheduleHoliday.holiday_date <= data.target_end_date,
                ScheduleHoliday.status == 1,
                ScheduleHoliday.allow_schedule == False,  # noqa: E712
            ]
            if tenant_id:
                holiday_conditions.append(ScheduleHoliday.tenant_id == tenant_id)
            holiday_result = await self.db.execute(
                select(ScheduleHoliday).where(and_(*holiday_conditions))
            )
            holidays = list(holiday_result.scalars().all())

        # 预加载休息日（用于 skip_holidays 过滤）
        rest_days = []
        if data.skip_holidays:
            rest_day_conditions = [
                RestDay.status == 1,
                RestDay.start_date <= data.target_end_date,
                RestDay.end_date >= data.target_start_date,
            ]
            if tenant_id:
                rest_day_conditions.append(RestDay.tenant_id == tenant_id)
            rest_day_result = await self.db.execute(
                select(RestDay).where(and_(*rest_day_conditions))
            )
            rest_days = list(rest_day_result.scalars().all())

        # 构建待复制项
        copy_items: list[tuple[Schedule, date]] = []
        skipped = 0
        for src in source_schedules:
            target_date = src.schedule_date + timedelta(days=offset_days)

            # 日期范围校验
            if target_date < data.target_start_date or target_date > data.target_end_date:
                skipped += 1
                continue

            # 跳过节假日
            if data.skip_holidays:
                # 检查是否为禁止排班的节假日
                from app.modules.schedules.service_conflict import ScheduleConflictService
                conflict_svc = ScheduleConflictService(self.db)
                holiday_conflict = conflict_svc._check_holiday_from_cache(holidays, target_date, src.store_id)
                if holiday_conflict:
                    skipped += 1
                    continue

                # 检查是否为休息日
                if is_rest_day(rest_days, target_date, src.store_id, src.doctor_id):
                    skipped += 1
                    continue

            copy_items.append((src, target_date))

        if not copy_items:
            return ScheduleBatchCopyResult(
                total_source=total_source, copied=0, skipped=skipped, overwritten=0, failed=0,
            )

        # 批量冲突检测
        check_items = [
            ScheduleCheckItem(
                doctor_id=src.doctor_id,
                schedule_date=target_date,
                start_time=src.start_time,
                end_time=src.end_time,
                time_slot=src.time_slot,
                store_id=src.store_id,
            )
            for src, target_date in copy_items
        ]
        from app.modules.schedules.service_conflict import ScheduleConflictService
        conflict_service = ScheduleConflictService(self.db)
        conflict_results = await conflict_service.batch_check_conflicts(check_items)

        # 根据冲突策略分拣
        to_create: list[tuple[Schedule, date]] = []
        to_overwrite: list = []
        manual_conflicts: list[dict] = []
        conflict_skipped = 0

        for (src, target_date), conflict_result in zip(copy_items, conflict_results, strict=False):
            if not conflict_result.has_conflict:
                to_create.append((src, target_date))
                continue

            if data.conflict_strategy == "skip":
                conflict_skipped += 1
            elif data.conflict_strategy == "overwrite":
                to_overwrite.append((src, target_date, conflict_result))
            else:  # manual
                manual_conflicts.append({
                    "source_schedule_id": src.id,
                    "source_date": str(src.schedule_date),
                    "target_date": str(target_date),
                    "doctor_id": src.doctor_id,
                    "time_slot": src.time_slot,
                    "conflicts": [
                        {"type": c.type, "severity": c.severity, "message": c.message}
                        for c in conflict_result.conflicts
                    ],
                })

        # 分布式锁保护覆盖删除和批量创建
        lock_name = f"schedule:batch_copy:{tenant_id}:{data.target_start_date}:{data.target_end_date}"

        try:
            async with RedisCache.tenant_distributed_lock(lock_name, tenant_id=tenant_id, timeout=60, retry_times=3):
                # overwrite 策略：删除目标位置旧排班（在锁内执行，避免竞态）
                overwritten = 0
                if to_overwrite:
                    for src, target_date, conflict_result in to_overwrite:
                        all_resolved = True
                        for c in conflict_result.conflicts:
                            existing_id = c.details.get("existing_schedule_id")
                            if existing_id:
                                existing_result = await self.db.execute(
                                    select(Schedule).where(
                                        Schedule.id == existing_id,
                                        Schedule.booked_slots == 0,
                                    )
                                )
                                existing_schedule = existing_result.scalar_one_or_none()
                                if existing_schedule:
                                    await self.db.delete(existing_schedule)
                                    overwritten += 1
                                else:
                                    all_resolved = False
                        if all_resolved:
                            to_create.append((src, target_date))
                        else:
                            conflict_skipped += 1

                if overwritten > 0:
                    await self.db.flush()

                copied = 0
                failed = 0

                for src, target_date in to_create:
                    try:
                        default_online = 10
                        new_schedule = Schedule(
                            id=str(uuid.uuid4()),
                            tenant_id=tenant_id,
                            doctor_id=src.doctor_id,
                            store_id=src.store_id,
                            template_id=src.template_id,
                            schedule_date=target_date,
                            time_slot=src.time_slot,
                            start_time=src.start_time,
                            end_time=src.end_time,
                            total_slots=src.total_slots if data.copy_quota else default_online,
                            booked_slots=0,
                            online_quota=src.online_quota if data.copy_quota else default_online,
                            offline_quota=src.offline_quota if data.copy_quota else 0,
                            reserved_quota=src.reserved_quota if data.copy_quota else 0,
                            extra_quota=src.extra_quota if data.copy_quota else 0,
                            fee=src.fee if data.copy_fee else 0,
                            appointment_type=src.appointment_type,
                            status=1,
                            schedule_status=ScheduleStatus.PUBLISHED,
                        )
                        set_create_audit(new_schedule, operator_id)
                        self.db.add(new_schedule)

                        # 审计：记录复制操作
                        after = snapshot_schedule(new_schedule)
                        after_json = json.dumps(after, ensure_ascii=False, default=str) if after else None
                        audit_log = make_schedule_audit(
                            schedule_id=new_schedule.id,
                            tenant_id=tenant_id or "",
                            action="copy",
                            operator_id=operator_id,
                            snapshot_before=None,
                            snapshot_after=after_json,
                            changes=None,
                        )
                        self.db.add(audit_log)

                        copied += 1
                    except Exception as e:
                        logger.warning(f"复制排班失败 (source_id={src.id}, target_date={target_date}): {e}")
                        failed += 1

                if copied > 0 or overwritten > 0:
                    await self.db.commit()

        except RuntimeError:
            return ScheduleBatchCopyResult(
                total_source=total_source,
                copied=0,
                skipped=skipped + conflict_skipped,
                overwritten=0,
                failed=total_source,
                conflicts=[{"message": "操作频繁，请稍后重试"}],
            )

        return ScheduleBatchCopyResult(
            total_source=total_source,
            copied=copied,
            skipped=skipped + conflict_skipped,
            overwritten=overwritten,
            failed=failed,
            conflicts=manual_conflicts,
        )

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
