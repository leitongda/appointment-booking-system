"""CRUD operations for schedule templates."""

import json
import uuid
from datetime import datetime

from sqlalchemy import select

from app.middleware.tenant_context import get_current_tenant_id
from app.models.schedule_template import ScheduleTemplate
from app.schemas.schedule_template import ScheduleTemplateCreate, ScheduleTemplateUpdate
from app.utils.audit import set_create_audit, set_update_audit


class ScheduleTemplateMutationMixin:
    async def _get_template_with_tenant(self, template_id: str) -> ScheduleTemplate | None:
        """根据 ID 查询排班模板，同时过滤租户（与 service_query 保持一致）。"""
        from sqlalchemy import and_

        conditions = [ScheduleTemplate.id == template_id]
        tenant_id = get_current_tenant_id()
        if tenant_id is not None:
            conditions.append(ScheduleTemplate.tenant_id == tenant_id)

        result = await self.db.execute(
            select(ScheduleTemplate).where(and_(*conditions))
        )
        return result.scalar_one_or_none()

    async def create(self, data: ScheduleTemplateCreate) -> ScheduleTemplate:
        from app.models.department import Department
        from app.models.doctor import Doctor
        from app.models.rule_set import ShiftType
        from app.models.store import Store

        if not data.name or not data.name.strip():
            raise ValueError("模板名称不能为空")
        if not data.store_id:
            raise ValueError("门店ID不能为空")
        if not data.doctor_id:
            raise ValueError("医生ID不能为空")
        if not data.department_id:
            raise ValueError("科室ID不能为空")
        if not data.shift_type_id:
            raise ValueError("班次类型不能为空")
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
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            raise ValueError("医生不存在")

        department_result = await self.db.execute(
            select(Department).where(Department.id == data.department_id)
        )
        department = department_result.scalar_one_or_none()
        if not department:
            raise ValueError("科室不存在")

        shift_type_result = await self.db.execute(
            select(ShiftType).where(ShiftType.id == data.shift_type_id, ShiftType.enabled == True)
        )
        if not shift_type_result.scalar_one_or_none():
            raise ValueError("班次类型不存在或已禁用")

        # 可选：校验 rule_set_id
        if data.rule_set_id:
            from app.models.rule_set import RuleSet
            rule_set_result = await self.db.execute(
                select(RuleSet).where(RuleSet.id == data.rule_set_id, RuleSet.enabled == True, RuleSet.deleted_at.is_(None))
            )
            if not rule_set_result.scalar_one_or_none():
                raise ValueError("规则组不存在或已禁用")

        if doctor.store_id != data.store_id:
            raise ValueError("所选医生不属于当前门店")
        if doctor.department_id != data.department_id:
            raise ValueError("所选医生不属于当前科室")
        if getattr(department, "store_id", None) and department.store_id != data.store_id:
            raise ValueError("所选科室不属于当前门店")

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

        if start_time >= end_time:
            raise ValueError("结束时间必须晚于开始时间")

        break_times_json = None
        if data.break_times:
            break_times_list = []
            normalized_breaks = []
            for bt in data.break_times:
                bt_start = bt.start_time
                bt_end = bt.end_time
                if bt_start >= bt_end:
                    raise ValueError("排除时间段结束时间必须晚于开始时间")
                if bt_start < start_time or bt_end > end_time:
                    raise ValueError("排除时间段必须在排班时间范围内")
                normalized_breaks.append((bt_start, bt_end))
                break_times_list.append(
                    {
                        "startTime": bt_start.strftime("%H:%M")
                        if hasattr(bt_start, "strftime")
                        else str(bt_start),
                        "endTime": bt_end.strftime("%H:%M")
                        if hasattr(bt_end, "strftime")
                        else str(bt_end),
                    }
                )
            normalized_breaks.sort(key=lambda item: item[0])
            for previous, current in zip(normalized_breaks, normalized_breaks[1:], strict=False):
                if current[0] < previous[1]:
                    raise ValueError("排除时间段不能重叠")
            break_times_json = json.dumps(break_times_list)

        template = ScheduleTemplate(
            id=str(uuid.uuid4()),
            name=data.name,
            tenant_id=get_current_tenant_id(),
            store_id=data.store_id,
            doctor_id=data.doctor_id,
            department_id=data.department_id,
            shift_type_id=data.shift_type_id,
            rule_set_id=data.rule_set_id,
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
        self, template_id: str, data: ScheduleTemplateUpdate, operator_id: str | None = None
    ) -> ScheduleTemplate | None:
        template = await self._get_template_with_tenant(template_id)
        if not template:
            return None

        update_data = data.model_dump(exclude_unset=True)

        if "appointment_type" in update_data and update_data["appointment_type"]:
            update_data["appointment_type"] = update_data["appointment_type"].value
        if "schedule_mode" in update_data and update_data["schedule_mode"]:
            update_data["schedule_mode"] = update_data["schedule_mode"].value
        if "weekdays" in update_data and update_data["weekdays"] is not None:
            update_data["weekdays"] = json.dumps(update_data["weekdays"])

        # 可选：校验 rule_set_id
        if "rule_set_id" in update_data and update_data["rule_set_id"]:
            from app.models.rule_set import RuleSet
            rule_set_result = await self.db.execute(
                select(RuleSet).where(
                    RuleSet.id == update_data["rule_set_id"],
                    RuleSet.enabled == True,
                    RuleSet.deleted_at.is_(None),
                )
            )
            if not rule_set_result.scalar_one_or_none():
                raise ValueError("规则组不存在或已禁用")

        if "start_time" in update_data or "end_time" in update_data:
            start_time = update_data.get("start_time", template.start_time)
            end_time = update_data.get("end_time", template.end_time)
            if start_time >= end_time:
                raise ValueError("结束时间必须晚于开始时间")

        if "break_times" in update_data:
            if update_data["break_times"] is not None:
                break_times_list = []
                normalized_breaks = []
                start_time = update_data.get("start_time", template.start_time)
                end_time = update_data.get("end_time", template.end_time)
                for bt in update_data["break_times"]:
                    if hasattr(bt, "start_time"):
                        bt_start = bt.start_time
                        bt_end = bt.end_time
                        bt_dict = {
                            "startTime": bt_start.strftime("%H:%M")
                            if hasattr(bt_start, "strftime")
                            else str(bt_start),
                            "endTime": bt_end.strftime("%H:%M")
                            if hasattr(bt_end, "strftime")
                            else str(bt_end),
                        }
                    elif isinstance(bt, dict):
                        bt_start = bt.get("start_time") or bt.get("startTime")
                        bt_end = bt.get("end_time") or bt.get("endTime")
                        bt_dict = {
                            "startTime": bt_start.strftime("%H:%M")
                            if hasattr(bt_start, "strftime")
                            else str(bt_start),
                            "endTime": bt_end.strftime("%H:%M")
                            if hasattr(bt_end, "strftime")
                            else str(bt_end),
                        }
                    else:
                        bt_dict = bt
                        bt_start = None
                        bt_end = None
                    if bt_start is not None and bt_end is not None:
                        if bt_start >= bt_end:
                            raise ValueError("排除时间段结束时间必须晚于开始时间")
                        if bt_start < start_time or bt_end > end_time:
                            raise ValueError("排除时间段必须在排班时间范围内")
                        normalized_breaks.append((bt_start, bt_end))
                    break_times_list.append(bt_dict)
                normalized_breaks.sort(key=lambda item: item[0])
                for previous, current in zip(normalized_breaks, normalized_breaks[1:], strict=False):
                    if current[0] < previous[1]:
                        raise ValueError("排除时间段不能重叠")
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
        template = await self._get_template_with_tenant(template_id)
        if not template:
            return False

        await self.db.delete(template)
        await self.db.commit()
        return True
