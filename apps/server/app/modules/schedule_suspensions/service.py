"""停诊管理服务"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date
import uuid
import json
import logging

from app.models.schedule_suspension import ScheduleSuspension
from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.models.store import Store
from app.models.appointment import Appointment
from app.schemas.schedule_suspension import ScheduleSuspensionCreate, AvailableScheduleForSuspension
from app.utils.audit import set_create_audit, set_update_audit
from app.modules.messages.service_messages import MessageService
from app.middleware.tenant_context import get_current_tenant_id

logger = logging.getLogger(__name__)


class ScheduleSuspensionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, suspension_id: str) -> Optional[ScheduleSuspension]:
        query = (
            select(ScheduleSuspension)
            .options(
                selectinload(ScheduleSuspension.store),
                selectinload(ScheduleSuspension.doctor)
            )
            .where(ScheduleSuspension.id == suspension_id)
        )
        # 租户隔离
        tenant_id = get_current_tenant_id()
        if tenant_id:
            query = query.where(ScheduleSuspension.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[ScheduleSuspension], int]:
        tenant_id = get_current_tenant_id()
        query = select(ScheduleSuspension).options(
            selectinload(ScheduleSuspension.store),
            selectinload(ScheduleSuspension.doctor)
        )
        count_query = select(func.count(ScheduleSuspension.id))

        conditions = []
        if tenant_id:
            conditions.append(ScheduleSuspension.tenant_id == tenant_id)
        if store_id:
            conditions.append(ScheduleSuspension.store_id == store_id)
        if doctor_id:
            conditions.append(ScheduleSuspension.doctor_id == doctor_id)
        if start_date:
            conditions.append(ScheduleSuspension.suspension_date >= start_date)
        if end_date:
            conditions.append(ScheduleSuspension.suspension_date <= end_date)
        if status is not None:
            conditions.append(ScheduleSuspension.status == status)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        query = query.order_by(ScheduleSuspension.suspension_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def create(self, data: ScheduleSuspensionCreate, operator_id: Optional[str] = None) -> ScheduleSuspension:
        """创建停诊并自动更新相关排班状态"""
        tenant_id = get_current_tenant_id()
        suspension = ScheduleSuspension(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            store_id=data.store_id,
            doctor_id=data.doctor_id,
            title=data.title,
            suspension_date=data.suspension_date,
            schedule_ids=json.dumps(data.schedule_ids) if data.schedule_ids else None,
            time_slots=json.dumps(data.time_slots) if data.time_slots else None,
            status=1
        )
        set_create_audit(suspension, operator_id)
        self.db.add(suspension)

        # 如果有指定的排班ID，更新这些排班的状态
        if data.schedule_ids:
            for schedule_id in data.schedule_ids:
                schedule_conditions = [Schedule.id == schedule_id]
                if tenant_id:
                    schedule_conditions.append(Schedule.tenant_id == tenant_id)
                schedule_result = await self.db.execute(
                    select(Schedule).where(and_(*schedule_conditions))
                )
                schedule = schedule_result.scalar_one_or_none()
                if schedule:
                    schedule.status = 0  # 停诊
        else:
            # 如果没有指定排班ID，但有time_slots，更新匹配的排班
            if data.time_slots:
                # 获取该日期所有排班
                all_schedule_conditions = [
                    Schedule.doctor_id == data.doctor_id,
                    Schedule.schedule_date == data.suspension_date,
                    Schedule.status == 1
                ]
                if tenant_id:
                    all_schedule_conditions.append(Schedule.tenant_id == tenant_id)
                all_schedules_result = await self.db.execute(
                    select(Schedule).where(and_(*all_schedule_conditions))
                )
                all_schedules = all_schedules_result.scalars().all()

                for schedule in all_schedules:
                    if schedule.start_time and schedule.end_time:
                        time_str = f"{schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}"
                        if time_str in data.time_slots:
                            schedule.status = 0
            else:
                # 全天停诊，更新该日期所有排班
                all_schedule_conditions = [
                    Schedule.doctor_id == data.doctor_id,
                    Schedule.schedule_date == data.suspension_date,
                    Schedule.status == 1
                ]
                if tenant_id:
                    all_schedule_conditions.append(Schedule.tenant_id == tenant_id)
                all_schedules_result = await self.db.execute(
                    select(Schedule).where(and_(*all_schedule_conditions))
                )
                all_schedules = all_schedules_result.scalars().all()
                for schedule in all_schedules:
                    schedule.status = 0

        await self.db.commit()
        await self.db.refresh(suspension)

        # 发送停诊通知给受影响的患者
        await self._send_stop_clinic_notifications(suspension, data)

        return suspension

    async def _send_stop_clinic_notifications(
        self,
        suspension: ScheduleSuspension,
        data: ScheduleSuspensionCreate
    ):
        """发送停诊通知给受影响的患者"""
        try:
            tenant_id = get_current_tenant_id()
            # 获取受影响的排班 ID 列表
            affected_schedule_ids = []
            if data.schedule_ids:
                affected_schedule_ids = data.schedule_ids
            else:
                # 如果没有指定排班 ID，获取该日期该医生的所有停诊排班
                schedule_conditions = [
                    Schedule.doctor_id == data.doctor_id,
                    Schedule.schedule_date == data.suspension_date,
                    Schedule.status == 0  # 已停诊
                ]
                if tenant_id:
                    schedule_conditions.append(Schedule.tenant_id == tenant_id)
                schedules_result = await self.db.execute(
                    select(Schedule).where(and_(*schedule_conditions))
                )
                schedules = schedules_result.scalars().all()
                affected_schedule_ids = [s.id for s in schedules]

            if not affected_schedule_ids:
                return

            # 获取这些排班关联的有效预约（已预约、已签到状态）
            appointment_conditions = [
                Appointment.schedule_id.in_(affected_schedule_ids),
                Appointment.status.in_([1, 2])  # 1=已预约, 2=已签到
            ]
            if tenant_id:
                appointment_conditions.append(Appointment.tenant_id == tenant_id)
            appointments_result = await self.db.execute(
                select(Appointment)
                .options(selectinload(Appointment.schedule))
                .where(and_(*appointment_conditions))
            )
            appointments = appointments_result.scalars().all()

            if not appointments:
                return

            # 获取医生信息
            doctor_result = await self.db.execute(
                select(Doctor).where(Doctor.id == data.doctor_id)
            )
            doctor = doctor_result.scalar_one_or_none()
            doctor_name = doctor.name if doctor else "医生"

            # 发送消息通知
            message_service = MessageService(self.db)
            suspension_date_str = data.suspension_date.strftime('%Y年%m月%d日')

            for appointment in appointments:
                try:
                    # 格式化时段显示
                    time_slot_display = ""
                    if appointment.schedule:
                        time_slot_display = {
                            'morning': '上午',
                            'afternoon': '下午',
                            'evening': '晚间',
                        }.get(appointment.schedule.time_slot, appointment.schedule.time_slot or "")

                    title_text = data.title or "停诊通知"

                    await message_service.send_stop_clinic_notification(
                        user_id=appointment.user_id,
                        user_type="patient",
                        title=title_text,
                        content=f"您预约的{doctor_name}医生（{suspension_date_str} {time_slot_display}）因故停诊。请重新预约其他时间，给您带来不便敬请谅解。",
                        appointment_id=appointment.id
                    )
                except Exception as e:
                    logger.warning(f"停诊通知发送失败 (appointment_id={appointment.id}): {e}")

        except Exception as e:
            # 消息通知失败不影响停诊操作
            logger.warning(f"停诊通知批量发送失败: {e}")

    async def delete(self, suspension_id: str) -> bool:
        """删除停诊记录"""
        suspension = await self.get_by_id(suspension_id)
        if not suspension:
            return False

        await self.db.delete(suspension)
        await self.db.commit()
        return True

    async def cancel(self, suspension_id: str) -> Optional[ScheduleSuspension]:
        """取消停诊并恢复相关排班状态"""
        suspension = await self.get_by_id(suspension_id)
        if not suspension:
            return None

        # 恢复相关排班状态
        if suspension.schedule_ids:
            try:
                schedule_ids_list = json.loads(suspension.schedule_ids)
                for schedule_id in schedule_ids_list:
                    schedule_conditions = [Schedule.id == schedule_id]
                    if suspension.tenant_id:
                        schedule_conditions.append(Schedule.tenant_id == suspension.tenant_id)
                    schedule_result = await self.db.execute(
                        select(Schedule).where(and_(*schedule_conditions))
                    )
                    schedule = schedule_result.scalar_one_or_none()
                    if schedule:
                        schedule.status = 1  # 恢复
            except Exception:
                pass
        elif suspension.time_slots:
            # 如果有time_slots，恢复匹配的排班
            try:
                time_slots_list = json.loads(suspension.time_slots)
                all_schedule_conditions = [
                    Schedule.doctor_id == suspension.doctor_id,
                    Schedule.schedule_date == suspension.suspension_date,
                    Schedule.status == 0
                ]
                if suspension.tenant_id:
                    all_schedule_conditions.append(Schedule.tenant_id == suspension.tenant_id)
                all_schedules_result = await self.db.execute(
                    select(Schedule).where(and_(*all_schedule_conditions))
                )
                all_schedules = all_schedules_result.scalars().all()
                for schedule in all_schedules:
                    if schedule.start_time and schedule.end_time:
                        time_str = f"{schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}"
                        if time_str in time_slots_list:
                            schedule.status = 1
            except Exception:
                pass
        else:
            # 全天停诊，恢复该日期所有排班
            all_schedule_conditions = [
                Schedule.doctor_id == suspension.doctor_id,
                Schedule.schedule_date == suspension.suspension_date,
                Schedule.status == 0
            ]
            if suspension.tenant_id:
                all_schedule_conditions.append(Schedule.tenant_id == suspension.tenant_id)
            all_schedules_result = await self.db.execute(
                select(Schedule).where(and_(*all_schedule_conditions))
            )
            all_schedules = all_schedules_result.scalars().all()
            for schedule in all_schedules:
                schedule.status = 1

        suspension.status = 0  # 标记停诊记录为已取消
        set_update_audit(suspension, None)  # 取消时更新 updated_by
        await self.db.commit()
        await self.db.refresh(suspension)
        return suspension

    async def get_available_schedules(
        self,
        store_id: str,
        doctor_id: str,
        suspension_date: date
    ) -> List[AvailableScheduleForSuspension]:
        """获取指定日期的可选排班（用于停诊选择）"""
        schedules = []
        tenant_id = get_current_tenant_id()

        # 1. 获取普通排班
        normal_conditions = [
            Schedule.doctor_id == doctor_id,
            Schedule.schedule_date == suspension_date,
            Schedule.status == 1
        ]
        if tenant_id:
            normal_conditions.append(Schedule.tenant_id == tenant_id)

        normal_result = await self.db.execute(
            select(Schedule).where(
                and_(*normal_conditions)
            ).order_by(Schedule.start_time)
        )
        normal_schedules = normal_result.scalars().all()

        for s in normal_schedules:
            start_str = s.start_time.strftime('%H:%M') if s.start_time else ''
            end_str = s.end_time.strftime('%H:%M') if s.end_time else ''
            time_slot = f"{start_str}-{end_str}" if start_str and end_str else s.time_slot

            schedules.append(AvailableScheduleForSuspension(
                schedule_id=s.id,
                time_slot=time_slot,
                schedule_type="normal",
                booked_count=s.booked_slots,
                max_patients=s.total_slots
            ))

        # 2. 获取自定义排班（template_id为NULL的排班）
        custom_conditions = [
            Schedule.doctor_id == doctor_id,
            Schedule.schedule_date == suspension_date,
            Schedule.status == 1,
            Schedule.template_id.is_(None)  # 自定义排班
        ]
        if tenant_id:
            custom_conditions.append(Schedule.tenant_id == tenant_id)

        custom_result = await self.db.execute(
            select(Schedule).where(
                and_(*custom_conditions)
            ).order_by(Schedule.start_time)
        )
        custom_schedules = custom_result.scalars().all()

        for s in custom_schedules:
            if s.start_time and s.end_time:
                time_slot = f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}"
            else:
                time_slot = s.time_slot or "未知"
            schedules.append(AvailableScheduleForSuspension(
                schedule_id=s.id,
                time_slot=time_slot,
                schedule_type="custom",
                booked_count=s.booked_slots,
                max_patients=s.total_slots
            ))

        return schedules

    async def check_suspension(
        self,
        doctor_id: str,
        suspension_date: date,
        time_slot: Optional[str] = None
    ) -> Optional[ScheduleSuspension]:
        """检查指定时间是否已停诊"""
        tenant_id = get_current_tenant_id()
        conditions = [
            ScheduleSuspension.doctor_id == doctor_id,
            ScheduleSuspension.suspension_date == suspension_date,
            ScheduleSuspension.status == 1
        ]
        if tenant_id:
            conditions.append(ScheduleSuspension.tenant_id == tenant_id)

        result = await self.db.execute(
            select(ScheduleSuspension).where(and_(*conditions))
        )
        suspensions = result.scalars().all()

        for s in suspensions:
            # 如果没有指定时段，说明全天停诊
            if s.time_slots is None:
                return s

            # 如果指定了时段，检查是否匹配
            if time_slot:
                try:
                    time_slots_list = json.loads(s.time_slots)
                    if time_slot in time_slots_list:
                        return s
                except Exception:
                    pass

        return None
