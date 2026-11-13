"""Rest-day checks and template-based generation for schedules."""

import logging
import uuid
from datetime import date, time, timedelta

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError

from app.middleware.tenant_context import get_current_tenant_id
from app.models.doctor import Doctor
from app.models.rest_day import RestDay
from app.models.schedule import Schedule
from app.modules.messages.service_messages import MessageService
from app.utils.schedule_utils import get_time_slot_from_time

logger = logging.getLogger(__name__)


class ScheduleGenerationMixin:
    async def _check_rest_day(
        self, check_date: date, store_id: str | None = None, doctor_id: str | None = None
    ) -> bool:
        from app.utils.schedule_utils import is_rest_day
        try:
            query = select(RestDay).where(
                and_(
                    RestDay.status == 1,
                    RestDay.start_date <= check_date,
                    RestDay.end_date >= check_date,
                )
            )
            if store_id:
                query = query.where(RestDay.store_id == store_id)

            result = await self.db.execute(query)
            rest_days = result.scalars().all()

            return is_rest_day(rest_days, check_date, store_id, doctor_id)
        except Exception as e:
            logger.error(f"检查休息日失败: date={check_date}, store_id={store_id}, error={e}")
            return False

    async def _validate_slot_against_rules(
        self,
        shift_type_id: str | None,
        slot_capacity: int,
        store_id: str | None = None,
        department_id: str | None = None,
        doctor_id: str | None = None,
    ) -> list[str]:
        """校验排班槽位是否符合规则引擎约束，返回警告列表。

        检查项：
        1. 规则集是否存在
        2. 预约时间窗是否配置
        3. 容量策略是否与模板一致
        """
        warnings: list[str] = []

        if not shift_type_id:
            warnings.append("未关联班次类型，无法校验规则约束")
            return warnings

        try:
            from app.modules.rule_engine.service import RuleEngineService
            rule_engine = RuleEngineService(self.db)

            rule_set = await rule_engine.get_applicable_rule_set(shift_type_id)
            if not rule_set:
                warnings.append("未配置适用的规则集，患者预约时将不受时间窗和策略限制")
                return warnings

            # 检查预约时间窗
            from app.models.rule_set import RuleWindow
            windows_result = await self.db.execute(
                select(RuleWindow).where(
                    and_(
                        RuleWindow.rule_set_id == rule_set.id,
                        RuleWindow.action == "BOOK",
                        RuleWindow.enabled == True,
                    )
                )
            )
            book_window = windows_result.scalar_one_or_none()
            if not book_window:
                warnings.append("未配置预约时间窗(BOOK)，患者可能随时预约或无法预约")

            # 检查容量策略
            capacity_policy = await rule_engine.get_capacity_policy(shift_type_id)
            if capacity_policy and capacity_policy.total_capacity > 0:
                if slot_capacity > capacity_policy.total_capacity:
                    warnings.append(
                        f"模板号源容量({slot_capacity})超过规则容量限制({capacity_policy.total_capacity})，"
                        f"超出部分可能无法预约"
                    )

        except Exception as e:
            logger.warning(f"规则引擎校验失败: {e}")
            warnings.append(f"规则引擎校验异常: {e}")

        return warnings

    async def _create_schedule_if_not_exists(
        self,
        doctor_id: str,
        store_id: str | None,
        schedule_date: date,
        start_time: time | None,
        end_time: time | None,
        time_slot: str,
        total_slots: int,
        appointment_type: str = "normal",
        template_id: str | None = None,
        shift_type_id: str | None = None,
        rule_set_id: str | None = None,
        check_rest_day: bool = True,
        check_duplicate: bool = True,
    ) -> tuple[Schedule | None, bool]:
        if check_rest_day and await self._check_rest_day(schedule_date, store_id, doctor_id):
            return None, False

        if check_duplicate:
            conditions = [Schedule.doctor_id == doctor_id, Schedule.schedule_date == schedule_date]
            if start_time and end_time:
                conditions.append(Schedule.start_time < end_time)
                conditions.append(Schedule.end_time > start_time)
            else:
                conditions.append(Schedule.time_slot == time_slot)

            existing_result = await self.db.execute(select(Schedule).where(and_(*conditions)))
            existing = existing_result.scalar_one_or_none()
            if existing:
                logger.info(
                    f"排班时间段重叠，跳过创建: doctor={doctor_id}, date={schedule_date}, "
                    f"new={start_time}-{end_time}, existing={existing.start_time}-{existing.end_time} "
                    f"(id={existing.id})"
                )
                return None, False

        if not store_id:
            doctor_result = await self.db.execute(select(Doctor).where(Doctor.id == doctor_id, Doctor.deleted_at.is_(None)))
            doctor = doctor_result.scalar_one_or_none()
            if doctor:
                store_id = doctor.store_id

        tenant_id = get_current_tenant_id()
        schedule = Schedule(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            doctor_id=doctor_id,
            store_id=store_id,
            template_id=template_id,
            shift_type_id=shift_type_id,
            rule_set_id=rule_set_id,
            schedule_date=schedule_date,
            time_slot=time_slot,
            start_time=start_time,
            end_time=end_time,
            total_slots=total_slots,
            appointment_type=appointment_type,
            booked_slots=0,
            status=1,
        )
        self.db.add(schedule)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            logger.info(f"排班已存在（数据库唯一约束兜底）: doctor={doctor_id}, date={schedule_date}, time={start_time}-{end_time}")
            return None, False
        return schedule, True

    async def _generate_from_template_internal(
        self,
        template_id: str,
        start_date: date,
        end_date: date,
        check_rest_day: bool = True,
        auto_commit: bool = True,
    ) -> int:
        from app.models.schedule_template import ScheduleTemplate
        from app.utils.schedule_utils import should_generate_schedule, split_time_range_with_breaks

        template_result = await self.db.execute(
            select(ScheduleTemplate).where(ScheduleTemplate.id == template_id)
        )
        template = template_result.scalar_one_or_none()
        if not template or template.status != 1:
            return 0

        weekdays = template.weekday_list
        if not weekdays:
            return 0

        # 在模板级别执行一次规则引擎校验
        rule_warnings = await self._validate_slot_against_rules(
            shift_type_id=template.shift_type_id if hasattr(template, 'shift_type_id') else None,
            slot_capacity=template.slot_capacity,
            store_id=template.store_id,
            department_id=template.department_id if hasattr(template, 'department_id') else None,
            doctor_id=template.doctor_id,
        )
        if rule_warnings:
            logger.warning(f"模板 {template_id} 规则引擎校验警告: {'; '.join(rule_warnings)}")

        break_times = template.break_times_list or []
        time_slots = split_time_range_with_breaks(
            template.start_time, template.end_time, template.slot_count, break_times
        )

        created_count = 0
        current_date = start_date
        while current_date <= end_date:
            weekday = current_date.isoweekday()
            if weekday in weekdays and should_generate_schedule(current_date, template.schedule_mode):
                for slot_start, slot_end in time_slots:
                    time_slot = get_time_slot_from_time(slot_start)
                    schedule, created = await self._create_schedule_if_not_exists(
                        doctor_id=template.doctor_id,
                        store_id=template.store_id,
                        schedule_date=current_date,
                        start_time=slot_start,
                        end_time=slot_end,
                        time_slot=time_slot,
                        total_slots=template.slot_capacity,
                        appointment_type=template.appointment_type,
                        template_id=template.id,
                        shift_type_id=template.shift_type_id,
                        rule_set_id=template.rule_set_id,
                        check_rest_day=check_rest_day,
                        check_duplicate=True,
                    )
                    if created:
                        created_count += 1
            current_date += timedelta(days=1)

        if auto_commit:
            try:
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
                logger.warning(f"模板 {template_id} 生成排班时遇到并发冲突，部分记录可能已被其他任务创建")
        return created_count

    async def generate_from_template(
        self,
        template_id: str,
        start_date: date,
        end_date: date,
        check_rest_day: bool = True,
    ) -> int:
        return await self._generate_from_template_internal(
            template_id=template_id,
            start_date=start_date,
            end_date=end_date,
            check_rest_day=check_rest_day,
            auto_commit=True,
        )

    async def validate_template_rules(
        self,
        shift_type_id: str | None,
        slot_capacity: int,
        store_id: str | None = None,
        department_id: str | None = None,
        doctor_id: str | None = None,
    ) -> list[str]:
        """公开接口：校验模板配置是否符合规则引擎约束。供预览 API 调用。"""
        return await self._validate_slot_against_rules(
            shift_type_id=shift_type_id,
            slot_capacity=slot_capacity,
            store_id=store_id,
            department_id=department_id,
            doctor_id=doctor_id,
        )

    async def _send_schedule_notification_to_doctor(
        self, doctor_id: str, title: str, content: str, schedule_id: str | None = None
    ):
        try:
            message_service = MessageService(self.db)
            await message_service.send_schedule_notification(
                doctor_id=doctor_id,
                title=title,
                content=content,
                schedule_id=schedule_id,
            )
        except Exception as e:
            # 通知是尽力而为：失败时必须回滚，否则 session 停留在
            # aborted 事务上，后续同 session 的考勤/返回序列化全部
            # 报 PendingRollbackError，把已成功的创建变成 500。
            logger.warning(f"排班通知发送失败 (doctor_id={doctor_id}): {e}")
            try:
                await self.db.rollback()
            except Exception:
                logger.warning("排班通知失败后的回滚也失败，忽略")
