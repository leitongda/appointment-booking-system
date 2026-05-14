"""Mutation-oriented schedule operations."""

import json
import logging
import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.redis import RedisCache
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.schemas.schedule import ScheduleBatchCreate, ScheduleCreate, ScheduleUpdate
from app.modules.messages.service_messages import MessageService
from app.utils.audit import set_create_audit, set_update_audit
from app.utils.schedule_utils import get_time_slot_from_time

logger = logging.getLogger(__name__)


class ScheduleMutationMixin:
    async def create(self, data: ScheduleCreate, operator_id: Optional[str] = None) -> Schedule:
        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        time_slot = data.time_slot
        if not time_slot and data.start_time:
            time_slot = get_time_slot_from_time(data.start_time)
        elif not time_slot:
            raise ValueError("必须提供 time_slot 或 start_time")

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
                total_slots=data.total_slots,
                booked_slots=0,
                appointment_type=data.appointment_type or "normal",
                status=data.status,
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

    async def batch_create(self, data: ScheduleBatchCreate, operator_id: Optional[str] = None) -> int:
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
                        schedule = Schedule(
                            id=str(uuid.uuid4()),
                            tenant_id=tenant_id,
                            doctor_id=data.doctor_id,
                            store_id=store_id,
                            schedule_date=current_date,
                            time_slot=time_slot,
                            total_slots=data.total_slots,
                            booked_slots=0,
                            appointment_type="normal",
                            status=1,
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

    async def update(
        self, schedule_id: str, data: ScheduleUpdate, operator_id: Optional[str] = None
    ) -> Optional[Schedule]:
        from app.middleware.tenant_context import get_current_tenant_id
        schedule = await self.get_by_id(schedule_id)
        if not schedule:
            return None

        # 租户隔离校验：防止跨租户修改
        tenant_id = get_current_tenant_id()
        if tenant_id and schedule.tenant_id and schedule.tenant_id != tenant_id:
            raise ValueError("无权修改此排班")

        update_data = data.model_dump(exclude_unset=True)
        if "total_slots" in update_data and update_data["total_slots"] < schedule.booked_slots:
            raise ValueError("总号源数不能小于已预约数")

        for field, value in update_data.items():
            setattr(schedule, field, value)

        set_update_audit(schedule, operator_id)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def batch_suspend(
        self, schedule_ids: List[str], reason: Optional[str] = None, operator_id: Optional[str] = None
    ) -> dict:
        """
        批量停诊排班

        P0修复：统一停诊操作路径，创建 ScheduleSuspension 记录，确保可以通过停诊管理恢复

        Args:
            schedule_ids: 排班ID列表
            reason: 停诊原因
            operator_id: 操作人ID

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
        from app.utils.schedule_utils import group_schedules_for_suspension, create_suspension_records
        from app.models.schedule_suspension import ScheduleSuspension
        from app.utils.audit import set_create_audit

        schedule_map = {s.id: s for s in schedules}

        # 使用工具函数分组
        suspension_groups = group_schedules_for_suspension(schedules, tenant_id)

        # 使用工具函数生成停诊记录数据
        suspension_records = create_suspension_records(
            suspension_groups, reason, tenant_id, operator_id
        )

        # 创建停诊记录并更新排班状态
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
                    status=record_data["status"]
                )
                set_create_audit(suspension, operator_id)
                self.db.add(suspension)

                # 更新排班状态
                sched_ids = json.loads(record_data["schedule_ids"])
                for sched_id in sched_ids:
                    schedule = schedule_map.get(sched_id)
                    if schedule:
                        schedule.status = 0
                        success_ids.append(sched_id)
                        affected_count += 1
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

        return {
            "success_count": affected_count,
            "failed_count": len(failed_items),
            "success_ids": success_ids,
            "failed_items": failed_items,
            "suspended_count": affected_count,
            "message": f"成功停诊 {affected_count} 个排班" + (f"，失败 {len(failed_items)} 个" if failed_items else "")
        }

    async def _send_batch_suspend_notifications(
        self, schedules: List[Schedule], reason: Optional[str] = None
    ):
        try:
            schedule_ids = [s.id for s in schedules]
            if not schedule_ids:
                return

            message_service = MessageService(self.db)
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
                    reason_text = f"原因：{reason}" if reason else "请重新预约其他时间"

                    await message_service.send_stop_clinic_notification(
                        user_id=appointment.user_id,
                        user_type="patient",
                        title="停诊通知",
                        content=f"您预约的{doctor_name}医生（{schedule_date_str} {time_slot_display}）因故停诊。{reason_text}，给您带来不便敬请谅解。",
                        appointment_id=appointment.id,
                        template_variables={
                            "doctor_name": doctor_name,
                            "date": schedule_date_str,
                            "time_slot": time_slot_display,
                            "reason": reason or "",
                        },
                    )
                except Exception as e:
                    logger.warning(f"停诊通知发送失败 (appointment_id={appointment.id}): {e}")
        except Exception as e:
            logger.warning(f"批量停诊通知发送失败: {e}")

    async def batch_resume(self, schedule_ids: List[str], operator_id: Optional[str] = None) -> int:
        """
        批量恢复排班

        P0修复：统一恢复操作路径，通过取消 ScheduleSuspension 记录来恢复排班

        Args:
            schedule_ids: 排班ID列表
            operator_id: 操作人ID

        Returns:
            恢复的排班数量
        """
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
                                    s.status = 1
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
                            s.status = 1
                            affected_count += 1

                    processed_suspension_ids.add(suspension.id)
                else:
                    # 只恢复当前排班
                    schedule.status = 1
                    affected_count += 1
            else:
                # 如果没有找到停诊记录，直接恢复排班状态
                schedule.status = 1
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

    async def batch_delete(self, schedule_ids: List[str]) -> dict:
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
