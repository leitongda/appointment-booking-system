"""随访服务"""
import json
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.follow_up_plan import FollowUpPlan, FollowUpPlanStep
from app.models.follow_up_record import FollowUpRecord
from app.models.follow_up_self_report import FollowUpSelfReport
from app.models.follow_up_task import FollowUpTask
from app.models.user import Patient
from app.utils.audit import set_create_audit, set_update_audit


def generate_task_no() -> str:
    now = datetime.now()
    return f"FU{now.strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"


# ========== 随访计划服务 ==========

class FollowUpPlanService:
    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    def _scope(self) -> str | None:
        """显式锚点优先；未传时回退请求上下文（灰度兼容）"""
        return self.tenant_id if self.tenant_id is not None else get_current_tenant_id()

    async def create(self, data, operator_id: str | None = None) -> FollowUpPlan:
        tenant_id = self._scope()
        plan = FollowUpPlan(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            department_id=data.department_id,
            diagnosis_code=data.diagnosis_code,
            diagnosis_name=data.diagnosis_name,
        )
        set_create_audit(plan, operator_id)

        for step_data in data.steps:
            step = FollowUpPlanStep(
                id=str(uuid.uuid4()),
                step_order=step_data.step_order,
                name=step_data.name,
                days_after_visit=step_data.days_after_visit,
                description=step_data.description,
            )
            plan.steps.append(step)

        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def get_by_id(self, plan_id: str) -> FollowUpPlan | None:
        stmt = (
            select(FollowUpPlan)
            .options(selectinload(FollowUpPlan.steps))
            .where(FollowUpPlan.id == plan_id, FollowUpPlan.deleted_at.is_(None))
        )
        tenant_id = self._scope()
        if tenant_id:
            stmt = stmt.where(FollowUpPlan.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_list(
        self,
        department_id: str | None = None,
        diagnosis_code: str | None = None,
        status: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[FollowUpPlan], int]:
        query = select(FollowUpPlan).options(selectinload(FollowUpPlan.steps))
        conditions = [FollowUpPlan.deleted_at.is_(None)]

        tenant_id = self._scope()
        if tenant_id:
            conditions.append(FollowUpPlan.tenant_id == tenant_id)
        if department_id:
            conditions.append(FollowUpPlan.department_id == department_id)
        if diagnosis_code:
            conditions.append(FollowUpPlan.diagnosis_code == diagnosis_code)
        if status is not None:
            conditions.append(FollowUpPlan.status == status)
        if keyword:
            conditions.append(FollowUpPlan.name.ilike(f"%{keyword}%"))

        query = query.where(and_(*conditions))

        count_query = select(func.count(FollowUpPlan.id)).where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(FollowUpPlan.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        plans = list(result.unique().scalars().all())
        return plans, total or 0

    async def update(self, plan_id: str, data, operator_id: str | None = None) -> FollowUpPlan | None:
        plan = await self.db.get(FollowUpPlan, plan_id)
        scope = self._scope()
        if not plan or plan.deleted_at is not None:
            return None
        if scope and plan.tenant_id != scope:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(plan, key, value)

        set_update_audit(plan, operator_id)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def update_steps(self, plan_id: str, steps_data, operator_id: str | None = None) -> FollowUpPlan | None:
        plan = await self.get_by_id(plan_id)
        if not plan:
            return None

        # 删除旧步骤
        for step in plan.steps:
            await self.db.delete(step)

        # 添加新步骤
        for step_data in steps_data:
            step = FollowUpPlanStep(
                id=str(uuid.uuid4()),
                plan_id=plan_id,
                step_order=step_data.step_order,
                name=step_data.name,
                days_after_visit=step_data.days_after_visit,
                description=step_data.description,
            )
            self.db.add(step)

        set_update_audit(plan, operator_id)
        await self.db.commit()
        return await self.get_by_id(plan_id)

    async def delete(self, plan_id: str, operator_id: str | None = None) -> bool:
        plan = await self.db.get(FollowUpPlan, plan_id)
        scope = self._scope()
        if not plan or plan.deleted_at is not None:
            return False
        if scope and plan.tenant_id != scope:
            return False

        plan.deleted_at = datetime.now()
        set_update_audit(plan, operator_id)
        await self.db.commit()
        return True


# ========== 随访任务服务 ==========

class FollowUpTaskService:
    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    def _scope(self) -> str | None:
        """显式锚点优先；未传时回退请求上下文（灰度兼容）"""
        return self.tenant_id if self.tenant_id is not None else get_current_tenant_id()

    async def create(self, data, operator_id: str | None = None) -> FollowUpTask:
        tenant_id = self._scope()
        task = FollowUpTask(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            task_no=generate_task_no(),
            patient_id=data.patient_id,
            doctor_id=data.doctor_id,
            department_id=data.department_id,
            appointment_id=data.appointment_id,
            medical_record_id=data.medical_record_id,
            scheduled_date=data.scheduled_date,
            status="pending",
        )
        set_create_audit(task, operator_id)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def generate_from_plan(
        self,
        patient_id: str,
        doctor_id: str,
        department_id: str,
        plan_id: str,
        appointment_id: str | None = None,
        medical_record_id: str | None = None,
        base_date: date | None = None,
        operator_id: str | None = None,
    ) -> list[FollowUpTask]:
        plan = await self.db.get(FollowUpPlan, plan_id)
        scope = self._scope()
        if not plan or plan.deleted_at is not None:
            raise ValueError("随访计划不存在")
        if scope and plan.tenant_id != scope:
            raise ValueError("随访计划不存在")

        # 加载步骤
        stmt = (
            select(FollowUpPlanStep)
            .where(FollowUpPlanStep.plan_id == plan_id)
            .order_by(FollowUpPlanStep.step_order)
        )
        result = await self.db.execute(stmt)
        steps = list(result.scalars().all())
        if not steps:
            raise ValueError("随访计划无步骤")

        if base_date is None:
            base_date = date.today()

        tenant_id = self._scope()
        today = date.today()
        tasks = []

        for step in steps:
            scheduled = base_date + timedelta(days=step.days_after_visit)
            task = FollowUpTask(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                task_no=generate_task_no(),
                patient_id=patient_id,
                doctor_id=doctor_id,
                department_id=department_id,
                appointment_id=appointment_id,
                medical_record_id=medical_record_id,
                plan_id=plan_id,
                plan_step_id=step.id,
                step_order=step.step_order,
                scheduled_date=scheduled,
                status="overdue" if scheduled < today else "pending",
            )
            set_create_audit(task, operator_id)
            self.db.add(task)
            tasks.append(task)

        await self.db.commit()
        for task in tasks:
            await self.db.refresh(task)
        return tasks

    async def get_by_id(self, task_id: str) -> FollowUpTask | None:
        stmt = (
            select(FollowUpTask)
            .options(
                joinedload(FollowUpTask.patient),
                joinedload(FollowUpTask.doctor),
                joinedload(FollowUpTask.department),
                joinedload(FollowUpTask.plan),
                selectinload(FollowUpTask.records),
            )
            .where(FollowUpTask.id == task_id, FollowUpTask.deleted_at.is_(None))
        )
        tenant_id = self._scope()
        if tenant_id:
            stmt = stmt.where(FollowUpTask.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_list(
        self,
        doctor_id: str | None = None,
        patient_id: str | None = None,
        department_id: str | None = None,
        status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[FollowUpTask], int]:
        query = select(FollowUpTask).options(
            joinedload(FollowUpTask.patient),
            joinedload(FollowUpTask.doctor),
            joinedload(FollowUpTask.department),
            joinedload(FollowUpTask.plan),
        )
        conditions = [FollowUpTask.deleted_at.is_(None)]

        tenant_id = self._scope()
        if tenant_id:
            conditions.append(FollowUpTask.tenant_id == tenant_id)
        if doctor_id:
            conditions.append(FollowUpTask.doctor_id == doctor_id)
        if patient_id:
            conditions.append(FollowUpTask.patient_id == patient_id)
        if department_id:
            conditions.append(FollowUpTask.department_id == department_id)
        if status:
            conditions.append(FollowUpTask.status == status)
        if start_date:
            conditions.append(FollowUpTask.scheduled_date >= start_date)
        if end_date:
            conditions.append(FollowUpTask.scheduled_date <= end_date)
        if keyword:
            conditions.append(
                FollowUpTask.task_no.ilike(f"%{keyword}%") |
                FollowUpTask.patient.has(Patient.name.ilike(f"%{keyword}%"))
            )

        query = query.where(and_(*conditions))
        count_query = select(func.count(FollowUpTask.id)).where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(FollowUpTask.scheduled_date.asc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        tasks = list(result.unique().scalars().all())
        return tasks, total or 0

    async def complete_task(self, task_id: str, operator_id: str | None = None) -> FollowUpTask | None:
        task = await self.db.get(FollowUpTask, task_id)
        scope = self._scope()
        if not task or task.deleted_at is not None:
            return None
        if scope and task.tenant_id != scope:
            return None
        if task.status not in ("pending", "overdue"):
            raise ValueError("任务非待处理状态，无法完成")

        task.status = "completed"
        task.completed_at = datetime.now()
        task.completed_by = operator_id
        set_update_audit(task, operator_id)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def skip_task(self, task_id: str, reason: str, operator_id: str | None = None) -> FollowUpTask | None:
        task = await self.db.get(FollowUpTask, task_id)
        scope = self._scope()
        if not task or task.deleted_at is not None:
            return None
        if scope and task.tenant_id != scope:
            return None
        if task.status not in ("pending", "overdue"):
            raise ValueError("任务非待处理状态，无法跳过")

        task.status = "skipped"
        task.skip_reason = reason
        set_update_audit(task, operator_id)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def mark_overdue(self, tenant_id: str | None = None) -> int:
        conditions = [
            FollowUpTask.status == "pending",
            FollowUpTask.scheduled_date < date.today(),
            FollowUpTask.deleted_at.is_(None),
        ]
        if tenant_id:
            conditions.append(FollowUpTask.tenant_id == tenant_id)

        from sqlalchemy import update
        stmt = (
            update(FollowUpTask)
            .where(and_(*conditions))
            .values(status="overdue", updated_at=datetime.now())
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def delete(self, task_id: str, operator_id: str | None = None) -> bool:
        task = await self.db.get(FollowUpTask, task_id)
        scope = self._scope()
        if not task or task.deleted_at is not None:
            return False
        if scope and task.tenant_id != scope:
            return False

        task.deleted_at = datetime.now()
        set_update_audit(task, operator_id)
        await self.db.commit()
        return True


# ========== 随访记录服务 ==========

class FollowUpRecordService:
    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    def _scope(self) -> str | None:
        """显式锚点优先；未传时回退请求上下文（灰度兼容）"""
        return self.tenant_id if self.tenant_id is not None else get_current_tenant_id()

    async def create(self, data, operator_id: str | None = None) -> FollowUpRecord:
        tenant_id = self._scope()

        # 解析附件
        attachments_str = None
        if data.attachments:
            import json
            attachments_str = json.dumps(data.attachments)

        record = FollowUpRecord(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            task_id=data.task_id,
            patient_id=data.patient_id,
            doctor_id=data.doctor_id,
            appointment_id=data.appointment_id,
            medical_record_id=data.medical_record_id,
            follow_up_date=data.follow_up_date,
            content=data.content,
            patient_condition=data.patient_condition.value if data.patient_condition else None,
            next_action=data.next_action,
            next_follow_up_date=data.next_follow_up_date,
            attachments=attachments_str,
        )
        set_create_audit(record, operator_id)
        self.db.add(record)

        # 自动完成关联任务
        if data.task_id:
            task = await self.db.get(FollowUpTask, data.task_id)
            if task and task.status == "pending":
                task.status = "completed"
                task.completed_at = datetime.now()
                task.completed_by = operator_id
                set_update_audit(task, operator_id)

        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_by_id(self, record_id: str) -> FollowUpRecord | None:
        stmt = (
            select(FollowUpRecord)
            .options(
                joinedload(FollowUpRecord.patient),
                joinedload(FollowUpRecord.doctor),
            )
            .where(FollowUpRecord.id == record_id, FollowUpRecord.deleted_at.is_(None))
        )
        tenant_id = self._scope()
        if tenant_id:
            stmt = stmt.where(FollowUpRecord.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_list(
        self,
        doctor_id: str | None = None,
        patient_id: str | None = None,
        task_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[FollowUpRecord], int]:
        query = select(FollowUpRecord).options(
            joinedload(FollowUpRecord.patient),
            joinedload(FollowUpRecord.doctor),
        )
        conditions = [FollowUpRecord.deleted_at.is_(None)]

        tenant_id = self._scope()
        if tenant_id:
            conditions.append(FollowUpRecord.tenant_id == tenant_id)
        if doctor_id:
            conditions.append(FollowUpRecord.doctor_id == doctor_id)
        if patient_id:
            conditions.append(FollowUpRecord.patient_id == patient_id)
        if task_id:
            conditions.append(FollowUpRecord.task_id == task_id)
        if start_date:
            conditions.append(func.date(FollowUpRecord.follow_up_date) >= start_date)
        if end_date:
            conditions.append(func.date(FollowUpRecord.follow_up_date) <= end_date)
        if keyword:
            conditions.append(
                FollowUpRecord.content.ilike(f"%{keyword}%") |
                FollowUpRecord.patient.has(Patient.name.ilike(f"%{keyword}%"))
            )

        query = query.where(and_(*conditions))
        count_query = select(func.count(FollowUpRecord.id)).where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(FollowUpRecord.follow_up_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        records = list(result.unique().scalars().all())
        return records, total or 0

    async def update(self, record_id: str, data, operator_id: str | None = None) -> FollowUpRecord | None:
        record = await self.db.get(FollowUpRecord, record_id)
        scope = self._scope()
        if not record or record.deleted_at is not None:
            return None
        if scope and record.tenant_id != scope:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "attachments" in update_data and update_data["attachments"] is not None:
            import json
            update_data["attachments"] = json.dumps(update_data["attachments"])
        if "patient_condition" in update_data and update_data["patient_condition"] is not None:
            update_data["patient_condition"] = update_data["patient_condition"].value

        for key, value in update_data.items():
            setattr(record, key, value)

        set_update_audit(record, operator_id)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def delete(self, record_id: str, operator_id: str | None = None) -> bool:
        record = await self.db.get(FollowUpRecord, record_id)
        scope = self._scope()
        if not record or record.deleted_at is not None:
            return False
        if scope and record.tenant_id != scope:
            return False

        record.deleted_at = datetime.now()
        set_update_audit(record, operator_id)
        await self.db.commit()
        return True


# ========== 患者自报告服务 ==========

class SelfReportService:
    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    def _scope(self) -> str | None:
        """显式锚点优先；未传时回退请求上下文（灰度兼容）"""
        return self.tenant_id if self.tenant_id is not None else get_current_tenant_id()

    async def create(self, data, patient_id: str, operator_id: str | None = None) -> FollowUpSelfReport:
        """创建患者自报告"""
        tenant_id = self._scope()
        report = FollowUpSelfReport(
            tenant_id=tenant_id,
            task_id=data.task_id,
            patient_id=patient_id,
            report_date=data.report_date or datetime.now(),
            systolic_bp=data.systolic_bp,
            diastolic_bp=data.diastolic_bp,
            blood_glucose=data.blood_glucose,
            heart_rate=data.heart_rate,
            temperature=data.temperature,
            symptoms=data.symptoms,
            patient_condition=data.patient_condition.value if data.patient_condition else None,
            notes=data.notes,
            attachments=json.dumps(data.attachments) if data.attachments else None,
            status="pending",
        )
        set_create_audit(report, operator_id)
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_by_id(self, report_id: str) -> FollowUpSelfReport | None:
        stmt = select(FollowUpSelfReport).where(
            FollowUpSelfReport.id == report_id,
            FollowUpSelfReport.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        report = result.scalar_one_or_none()
        scope = self._scope()
        if report and scope and report.tenant_id != scope:
            return None
        return report

    async def get_list(
        self,
        patient_id: str | None = None,
        task_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[FollowUpSelfReport], int]:
        """查询自报告列表"""
        tenant_id = self._scope()
        conditions = [FollowUpSelfReport.deleted_at.is_(None)]
        if tenant_id:
            conditions.append(FollowUpSelfReport.tenant_id == tenant_id)
        if patient_id:
            conditions.append(FollowUpSelfReport.patient_id == patient_id)
        if task_id:
            conditions.append(FollowUpSelfReport.task_id == task_id)
        if status:
            conditions.append(FollowUpSelfReport.status == status)

        where = and_(*conditions)

        # 总数
        count_stmt = select(func.count(FollowUpSelfReport.id)).where(where)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 分页
        stmt = (
            select(FollowUpSelfReport)
            .where(where)
            .order_by(FollowUpSelfReport.report_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        reports = list(result.scalars().all())
        return reports, total

    async def review(self, report_id: str, reviewer_id: str) -> FollowUpSelfReport | None:
        """审核自报告"""
        report = await self.get_by_id(report_id)
        if not report:
            return None
        report.status = "reviewed"
        report.reviewed_at = datetime.now()
        report.reviewed_by = reviewer_id
        set_update_audit(report, reviewer_id)
        await self.db.commit()
        await self.db.refresh(report)
        return report
