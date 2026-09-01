"""排班创建相关操作（单条 / 批量 / 复制）。"""

import json
import logging
import uuid
from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError

from app.core.redis import RedisCache
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.schedule_status import ScheduleStatus
from app.modules.schedules.audit_helpers import (
    make_schedule_audit,
    snapshot_schedule,
)
from app.modules.schedules.service_conflict import ScheduleConflictService
from app.schemas.schedule import (
    ScheduleBatchCopyRequest,
    ScheduleBatchCopyResult,
    ScheduleBatchCreate,
    ScheduleCreate,
)
from app.utils.audit import set_create_audit
from app.utils.schedule_utils import get_time_slot_from_time

logger = logging.getLogger(__name__)


class ScheduleMutationCreateMixin:
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

        # 如果排班直接以 published 状态创建，生成预期考勤记录
        if schedule.schedule_status == ScheduleStatus.PUBLISHED:
            from app.modules.attendance_records.service import AttendanceRecordService
            await AttendanceRecordService.create_expected_records(self.db, schedule)

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
        created_schedules = []
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
                        created_schedules.append(schedule)
                        created_count += 1
            current_date = current_date.fromordinal(current_date.toordinal() + 1)

        await self.db.commit()

        # 为批量创建的排班生成预期考勤记录
        if created_schedules:
            from app.modules.attendance_records.service import AttendanceRecordService
            for schedule in created_schedules:
                await AttendanceRecordService.create_expected_records(self.db, schedule)

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
                copied_schedules = []

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

                        copied_schedules.append(new_schedule)
                        copied += 1
                    except Exception as e:
                        logger.warning(f"复制排班失败 (source_id={src.id}, target_date={target_date}): {e}")
                        failed += 1

                if copied > 0 or overwritten > 0:
                    await self.db.commit()

                    # 为复制的排班创建预期考勤记录
                    if copied_schedules:
                        from app.modules.attendance_records.service import AttendanceRecordService
                        for schedule in copied_schedules:
                            await AttendanceRecordService.create_expected_records(self.db, schedule)

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
