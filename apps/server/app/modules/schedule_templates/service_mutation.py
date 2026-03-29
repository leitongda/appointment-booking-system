"""CRUD operations for schedule templates."""

import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.models.schedule_template import ScheduleTemplate
from app.schemas.schedule_template import ScheduleTemplateCreate, ScheduleTemplateUpdate
from app.utils.audit import set_create_audit, set_update_audit


class ScheduleTemplateMutationMixin:
    async def create(self, data: ScheduleTemplateCreate) -> ScheduleTemplate:
        from app.models.department import Department
        from app.models.doctor import Doctor
        from app.models.store import Store

        if not data.name or not data.name.strip():
            raise ValueError("模板名称不能为空")
        if not data.store_id:
            raise ValueError("门店ID不能为空")
        if not data.doctor_id:
            raise ValueError("医生ID不能为空")
        if not data.department_id:
            raise ValueError("科室ID不能为空")
        if not data.weekdays or len(data.weekdays) == 0:
            raise ValueError("星期数组不能为空")
        if not data.start_time:
            raise ValueError("开始时间不能为空")
        if not data.end_time:
            raise ValueError("结束时间不能为空")

        store_result = await self.db.execute(select(Store).where(Store.id == data.store_id))
        if not store_result.scalar_one_or_none():
            raise ValueError("门店不存在")

        doctor_result = await self.db.execute(select(Doctor).where(Doctor.id == data.doctor_id, Doctor.deleted_at.is_(None)))
        if not doctor_result.scalar_one_or_none():
            raise ValueError("医生不存在")

        department_result = await self.db.execute(
            select(Department).where(Department.id == data.department_id)
        )
        if not department_result.scalar_one_or_none():
            raise ValueError("科室不存在")

        start_time = data.start_time
        end_time = data.end_time

        if isinstance(start_time, str):
            try:
                start_time = datetime.strptime(start_time, "%H:%M").time()
            except ValueError:
                start_time = datetime.strptime(start_time, "%H:%M:%S").time()

        if isinstance(end_time, str):
            try:
                end_time = datetime.strptime(end_time, "%H:%M").time()
            except ValueError:
                end_time = datetime.strptime(end_time, "%H:%M:%S").time()

        break_times_json = None
        if data.break_times:
            break_times_list = []
            for bt in data.break_times:
                break_times_list.append(
                    {
                        "startTime": bt.start_time.strftime("%H:%M")
                        if hasattr(bt.start_time, "strftime")
                        else str(bt.start_time),
                        "endTime": bt.end_time.strftime("%H:%M")
                        if hasattr(bt.end_time, "strftime")
                        else str(bt.end_time),
                    }
                )
            break_times_json = json.dumps(break_times_list)

        template = ScheduleTemplate(
            id=str(uuid.uuid4()),
            name=data.name,
            store_id=data.store_id,
            doctor_id=data.doctor_id,
            department_id=data.department_id,
            weekdays=json.dumps(data.weekdays),
            appointment_type=data.appointment_type.value
            if hasattr(data.appointment_type, "value")
            else str(data.appointment_type),
            start_time=start_time,
            end_time=end_time,
            slot_count=data.slot_count or 1,
            slot_capacity=data.slot_capacity or 10,
            schedule_mode=data.schedule_mode.value
            if hasattr(data.schedule_mode, "value")
            else str(data.schedule_mode),
            break_times=break_times_json,
            status=1,
        )
        set_create_audit(template, data.operator_id if hasattr(data, "operator_id") else None)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update(
        self, template_id: str, data: ScheduleTemplateUpdate, operator_id: Optional[str] = None
    ) -> Optional[ScheduleTemplate]:
        template = await self.get_by_id(template_id)
        if not template:
            return None

        update_data = data.model_dump(exclude_unset=True)

        if "appointment_type" in update_data and update_data["appointment_type"]:
            update_data["appointment_type"] = update_data["appointment_type"].value
        if "schedule_mode" in update_data and update_data["schedule_mode"]:
            update_data["schedule_mode"] = update_data["schedule_mode"].value
        if "weekdays" in update_data and update_data["weekdays"] is not None:
            update_data["weekdays"] = json.dumps(update_data["weekdays"])

        if "break_times" in update_data:
            if update_data["break_times"] is not None:
                break_times_list = []
                for bt in update_data["break_times"]:
                    if hasattr(bt, "start_time"):
                        bt_dict = {
                            "startTime": bt.start_time.strftime("%H:%M")
                            if hasattr(bt.start_time, "strftime")
                            else str(bt.start_time),
                            "endTime": bt.end_time.strftime("%H:%M")
                            if hasattr(bt.end_time, "strftime")
                            else str(bt.end_time),
                        }
                    elif isinstance(bt, dict):
                        start_time = bt.get("start_time") or bt.get("startTime")
                        end_time = bt.get("end_time") or bt.get("endTime")
                        bt_dict = {
                            "startTime": start_time.strftime("%H:%M")
                            if hasattr(start_time, "strftime")
                            else str(start_time),
                            "endTime": end_time.strftime("%H:%M")
                            if hasattr(end_time, "strftime")
                            else str(end_time),
                        }
                    else:
                        bt_dict = bt
                    break_times_list.append(bt_dict)
                update_data["break_times"] = json.dumps(break_times_list)
            else:
                update_data["break_times"] = None

        for field, value in update_data.items():
            setattr(template, field, value)

        set_update_audit(template, operator_id)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete(self, template_id: str) -> bool:
        template = await self.get_by_id(template_id)
        if not template:
            return False

        await self.db.delete(template)
        await self.db.commit()
        return True
