"""FollowUp 服务单元测试

覆盖范围:
- FollowUpPlanService: CRUD、步骤替换、软删除
- FollowUpTaskService: 手动创建、从计划生成、完成/跳过状态转换、逾期标记
- FollowUpRecordService: 创建记录、自动完成关联任务、附件序列化
- SelfReportService: 患者自报告提交、审核、列表筛选
- 边界场景: 不存在的计划/任务、已完成任务无法重复操作、逾期升级
"""

from datetime import datetime, date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follow_up_plan import FollowUpPlan, FollowUpPlanStep
from app.models.follow_up_task import FollowUpTask
from app.models.follow_up_record import FollowUpRecord
from app.models.follow_up_self_report import FollowUpSelfReport
from app.enums.general import PatientCondition
from app.modules.follow_up.service import (
    FollowUpPlanService,
    FollowUpTaskService,
    FollowUpRecordService,
    SelfReportService,
    generate_task_no,
)
from app.schemas.follow_up import FollowUpPlanUpdate, FollowUpRecordUpdate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plan_data(name="术后随访计划", department_id=None, steps=None):
    """构建 FollowUpPlanCreate 风格的 SimpleNamespace 输入"""
    if steps is None:
        steps = [
            SimpleNamespace(step_order=1, name="术后3天电话随访", days_after_visit=3, description="电话了解恢复情况"),
            SimpleNamespace(step_order=2, name="术后7天复查", days_after_visit=7, description="门诊复查"),
            SimpleNamespace(step_order=3, name="术后30天复查", days_after_visit=30, description="全面复查"),
        ]
    return SimpleNamespace(
        name=name,
        description="随访计划描述",
        department_id=department_id,
        diagnosis_code="I10",
        diagnosis_name="高血压",
        steps=steps,
    )


def _make_task_data(patient_id, doctor_id, department_id, scheduled_date=None, **overrides):
    """构建 FollowUpTaskCreate 风格的 SimpleNamespace 输入"""
    if scheduled_date is None:
        scheduled_date = date.today() + timedelta(days=7)
    defaults = dict(
        patient_id=patient_id,
        doctor_id=doctor_id,
        department_id=department_id,
        appointment_id=None,
        medical_record_id=None,
        scheduled_date=scheduled_date,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_record_data(patient_id, doctor_id, task_id=None, content="随访内容", **overrides):
    """构建 FollowUpRecordCreate 风格的 SimpleNamespace 输入"""
    defaults = dict(
        task_id=task_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_id=None,
        medical_record_id=None,
        follow_up_date=datetime.now(),
        content=content,
        patient_condition=SimpleNamespace(value="improved"),
        next_action=None,
        next_follow_up_date=None,
        attachments=["http://example.com/file1.jpg"],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_self_report_data(**overrides):
    """构建 SelfReportCreate 风格的 SimpleNamespace 输入"""
    defaults = dict(
        task_id=None,
        report_date=None,
        systolic_bp=120,
        diastolic_bp=80,
        blood_glucose=5.5,
        heart_rate=72,
        temperature=36.5,
        symptoms="轻微头痛",
        patient_condition=SimpleNamespace(value="improved"),
        notes="感觉良好",
        attachments=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.fixture
def tenant_id():
    """返回固定的租户 ID"""
    return "test-tenant-001"


# ---------------------------------------------------------------------------
# TestFollowUpPlanService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFollowUpPlanService:
    """FollowUpPlanService 核心逻辑测试"""

    @pytest.mark.asyncio
    async def test_create_plan_with_steps(self, db_session: AsyncSession, tenant_id):
        """创建随访计划并携带步骤"""
        data = _make_plan_data()
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpPlanService(db_session)
            plan = await svc.create(data, operator_id="op-001")

        assert plan is not None
        assert plan.id is not None
        assert plan.tenant_id == tenant_id
        assert plan.name == "术后随访计划"
        assert plan.diagnosis_code == "I10"
        assert plan.diagnosis_name == "高血压"

        # 验证步骤已持久化
        plan = await svc.get_by_id(plan.id)
        assert plan is not None
        assert len(plan.steps) == 3
        assert plan.steps[0].name == "术后3天电话随访"
        assert plan.steps[0].days_after_visit == 3
        assert plan.steps[2].step_order == 3

    @pytest.mark.asyncio
    async def test_get_plan_by_id(self, db_session: AsyncSession, tenant_id):
        """通过 ID 获取随访计划"""
        data = _make_plan_data(name="高血压随访")
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpPlanService(db_session)
            plan = await svc.create(data)

            fetched = await svc.get_by_id(plan.id)
            assert fetched is not None
            assert fetched.name == "高血压随访"
            assert len(fetched.steps) == 3

    @pytest.mark.asyncio
    async def test_get_plan_by_id_not_found(self, db_session: AsyncSession, tenant_id):
        """获取不存在的计划返回 None"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpPlanService(db_session)
            result = await svc.get_by_id("nonexistent_id")
            assert result is None

    @pytest.mark.asyncio
    async def test_update_plan(self, db_session: AsyncSession, tenant_id):
        """更新计划基本信息"""
        data = _make_plan_data()
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpPlanService(db_session)
            plan = await svc.create(data)

            update_data = FollowUpPlanUpdate(name="更新后的随访计划")
            updated = await svc.update(plan.id, update_data, operator_id="op-002")
            assert updated is not None
            assert updated.name == "更新后的随访计划"

    @pytest.mark.asyncio
    async def test_update_plan_not_found(self, db_session: AsyncSession, tenant_id):
        """更新不存在的计划返回 None"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpPlanService(db_session)
            update_data = SimpleNamespace(name="x")
            result = await svc.update("nonexistent_id", update_data)
            assert result is None

    @pytest.mark.asyncio
    async def test_update_plan_steps(self, db_session: AsyncSession, tenant_id):
        """替换计划步骤（全量更新）"""
        data = _make_plan_data()
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpPlanService(db_session)
            plan = await svc.create(data)
            # create 返回的 plan 未 eager load steps，用 get_by_id 获取完整数据
            plan = await svc.get_by_id(plan.id)
            assert len(plan.steps) == 3

            new_steps = [
                SimpleNamespace(step_order=1, name="新步骤1", days_after_visit=1, description=None),
                SimpleNamespace(step_order=2, name="新步骤2", days_after_visit=14, description=None),
            ]
            updated = await svc.update_steps(plan.id, new_steps, operator_id="op-003")
            assert updated is not None

            # 直接查询数据库验证步骤已正确替换（避免 identity map 缓存问题）
            from sqlalchemy import select, func
            count_stmt = select(func.count(FollowUpPlanStep.id)).where(
                FollowUpPlanStep.plan_id == plan.id
            )
            count_result = await db_session.execute(count_stmt)
            step_count = count_result.scalar()
            assert step_count == 2

            # 验证新步骤名称
            stmt = select(FollowUpPlanStep).where(
                FollowUpPlanStep.plan_id == plan.id
            ).order_by(FollowUpPlanStep.step_order)
            result = await db_session.execute(stmt)
            steps = list(result.scalars().all())
            assert steps[0].name == "新步骤1"
            assert steps[1].days_after_visit == 14

    @pytest.mark.asyncio
    async def test_delete_plan(self, db_session: AsyncSession, tenant_id):
        """软删除计划"""
        data = _make_plan_data()
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpPlanService(db_session)
            plan = await svc.create(data)

            success = await svc.delete(plan.id)
            assert success is True

            # 删除后不应再查到
            result = await svc.get_by_id(plan.id)
            assert result is None

    @pytest.mark.asyncio
    async def test_delete_plan_not_found(self, db_session: AsyncSession, tenant_id):
        """删除不存在的计划返回 False"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpPlanService(db_session)
            result = await svc.delete("nonexistent_id")
            assert result is False

    @pytest.mark.asyncio
    async def test_get_list_with_filters(self, db_session: AsyncSession, tenant_id):
        """按条件筛选计划列表"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpPlanService(db_session)
            await svc.create(_make_plan_data(name="高血压随访"))
            await svc.create(_make_plan_data(name="糖尿病随访"))

            # 关键字搜索
            plans, total = await svc.get_list(keyword="高血压")
            assert total == 1
            assert plans[0].name == "高血压随访"

            # 全部
            plans, total = await svc.get_list()
            assert total == 2


# ---------------------------------------------------------------------------
# TestFollowUpTaskService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFollowUpTaskService:
    """FollowUpTaskService 核心逻辑测试"""

    @pytest.mark.asyncio
    async def test_create_task(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """手动创建随访任务"""
        data = _make_task_data(test_patient.id, test_doctor.id, test_department.id)
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpTaskService(db_session)
            task = await svc.create(data, operator_id="op-001")

        assert task is not None
        assert task.id is not None
        assert task.tenant_id == tenant_id
        assert task.patient_id == test_patient.id
        assert task.doctor_id == test_doctor.id
        assert task.status == "pending"
        assert task.task_no.startswith("FU")

    @pytest.mark.asyncio
    async def test_generate_task_no_format(self):
        """验证任务编号格式: FU + 时间戳 + 4位随机"""
        task_no = generate_task_no()
        assert task_no.startswith("FU")
        assert len(task_no) == len("FU") + 14 + 4  # FU + YYYYMMDDHHMMSS + 4hex

    @pytest.mark.asyncio
    async def test_generate_from_plan(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """从计划生成任务"""
        # 先创建计划
        plan_data = _make_plan_data()
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            plan_svc = FollowUpPlanService(db_session)
            plan = await plan_svc.create(plan_data)

            # 生成任务
            task_svc = FollowUpTaskService(db_session)
            tasks = await task_svc.generate_from_plan(
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                department_id=test_department.id,
                plan_id=plan.id,
                base_date=date.today(),
            )

        assert len(tasks) == 3
        assert tasks[0].plan_id == plan.id
        assert tasks[0].step_order == 1
        assert tasks[0].status == "pending"  # today + 3 > today -> pending
        assert tasks[2].step_order == 3

    @pytest.mark.asyncio
    async def test_generate_from_plan_past_steps_marked_overdue(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """计划步骤的随访日期已过时，任务应标记为 overdue"""
        plan_data = _make_plan_data(steps=[
            SimpleNamespace(step_order=1, name="步骤1", days_after_visit=3, description=None),
        ])
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            plan_svc = FollowUpPlanService(db_session)
            plan = await plan_svc.create(plan_data)

            task_svc = FollowUpTaskService(db_session)
            # base_date 设为 30 天前，使得 scheduled_date = base_date + 3 = 27天前 < today
            tasks = await task_svc.generate_from_plan(
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                department_id=test_department.id,
                plan_id=plan.id,
                base_date=date.today() - timedelta(days=30),
            )

        assert len(tasks) == 1
        assert tasks[0].status == "overdue"

    @pytest.mark.asyncio
    async def test_generate_from_plan_not_found(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """从不存在的计划生成任务应抛出 ValueError"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpTaskService(db_session)
            with pytest.raises(ValueError, match="随访计划不存在"):
                await svc.generate_from_plan(
                    patient_id=test_patient.id,
                    doctor_id=test_doctor.id,
                    department_id=test_department.id,
                    plan_id="nonexistent_plan",
                )

    @pytest.mark.asyncio
    async def test_generate_from_plan_no_steps(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """计划无步骤时应抛出 ValueError"""
        # 创建一个空步骤的计划
        plan = FollowUpPlan(
            id="plan_no_steps",
            tenant_id=tenant_id,
            name="空步骤计划",
            status=1,
        )
        db_session.add(plan)
        await db_session.commit()

        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpTaskService(db_session)
            with pytest.raises(ValueError, match="随访计划无步骤"):
                await svc.generate_from_plan(
                    patient_id=test_patient.id,
                    doctor_id=test_doctor.id,
                    department_id=test_department.id,
                    plan_id=plan.id,
                )

    @pytest.mark.asyncio
    async def test_complete_task(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """完成一个 pending 状态的任务"""
        data = _make_task_data(test_patient.id, test_doctor.id, test_department.id)
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpTaskService(db_session)
            task = await svc.create(data, operator_id="op-001")
            completed = await svc.complete_task(task.id, operator_id="op-002")

        assert completed is not None
        assert completed.status == "completed"
        assert completed.completed_by == "op-002"
        assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_complete_task_already_completed_raises(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """已完成的任务无法再次完成"""
        data = _make_task_data(test_patient.id, test_doctor.id, test_department.id)
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpTaskService(db_session)
            task = await svc.create(data)
            await svc.complete_task(task.id)

            with pytest.raises(ValueError, match="任务非待处理状态"):
                await svc.complete_task(task.id)

    @pytest.mark.asyncio
    async def test_skip_task(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """跳过任务"""
        data = _make_task_data(test_patient.id, test_doctor.id, test_department.id)
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpTaskService(db_session)
            task = await svc.create(data)
            skipped = await svc.skip_task(task.id, reason="患者拒绝随访", operator_id="op-003")

        assert skipped is not None
        assert skipped.status == "skipped"
        assert skipped.skip_reason == "患者拒绝随访"

    @pytest.mark.asyncio
    async def test_complete_overdue_task(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """overdue 状态的任务也可以完成"""
        data = _make_task_data(test_patient.id, test_doctor.id, test_department.id)
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpTaskService(db_session)
            task = await svc.create(data)
            # 手动设置为 overdue
            task.status = "overdue"
            await db_session.commit()
            await db_session.refresh(task)

            completed = await svc.complete_task(task.id)
            assert completed.status == "completed"

    @pytest.mark.asyncio
    async def test_mark_overdue(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """批量标记逾期任务"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpTaskService(db_session)
            # 创建一个 scheduled_date 在昨天的任务
            data = _make_task_data(
                test_patient.id, test_doctor.id, test_department.id,
                scheduled_date=date.today() - timedelta(days=1),
            )
            task = await svc.create(data)
            assert task.status == "pending"

            count = await svc.mark_overdue(tenant_id=tenant_id)
            assert count >= 1

            # 验证任务状态已变为 overdue
            await db_session.refresh(task)
            assert task.status == "overdue"

    @pytest.mark.asyncio
    async def test_delete_task(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """软删除任务"""
        data = _make_task_data(test_patient.id, test_doctor.id, test_department.id)
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpTaskService(db_session)
            task = await svc.create(data)

            success = await svc.delete(task.id)
            assert success is True

            result = await svc.get_by_id(task.id)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_task_list_filter_by_status(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """按状态筛选任务列表"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpTaskService(db_session)
            # 创建 pending 任务
            data1 = _make_task_data(test_patient.id, test_doctor.id, test_department.id)
            await svc.create(data1)
            # 创建另一个并完成
            data2 = _make_task_data(test_patient.id, test_doctor.id, test_department.id)
            task2 = await svc.create(data2)
            await svc.complete_task(task2.id)

            # 筛选 pending
            tasks, total = await svc.get_list(status="pending")
            assert total >= 1
            assert all(t.status == "pending" for t in tasks)

            # 筛选 completed
            tasks, total = await svc.get_list(status="completed")
            assert total >= 1
            assert all(t.status == "completed" for t in tasks)


# ---------------------------------------------------------------------------
# TestFollowUpRecordService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFollowUpRecordService:
    """FollowUpRecordService 核心逻辑测试"""

    @pytest.mark.asyncio
    async def test_create_record(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor):
        """创建随访记录"""
        data = _make_record_data(test_patient.id, test_doctor.id)
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpRecordService(db_session)
            record = await svc.create(data, operator_id="op-001")

        assert record is not None
        assert record.id is not None
        assert record.tenant_id == tenant_id
        assert record.content == "随访内容"
        assert record.patient_condition == "improved"
        # 附件应被序列化为 JSON 字符串
        assert record.attachments is not None
        assert "example.com" in record.attachments

    @pytest.mark.asyncio
    async def test_create_record_auto_completes_pending_task(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor, test_department):
        """创建随访记录时，如果关联了 pending 任务，应自动完成该任务"""
        # 先创建任务
        task_data = _make_task_data(test_patient.id, test_doctor.id, test_department.id)
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            task_svc = FollowUpTaskService(db_session)
            task = await task_svc.create(task_data)
            assert task.status == "pending"

            # 创建随访记录，关联该任务
            record_data = _make_record_data(test_patient.id, test_doctor.id, task_id=task.id)
            record_svc = FollowUpRecordService(db_session)
            record = await record_svc.create(record_data, operator_id="op-002")

        # 验证任务被自动完成
        await db_session.refresh(task)
        assert task.status == "completed"
        assert task.completed_by == "op-002"
        assert record.task_id == task.id

    @pytest.mark.asyncio
    async def test_create_record_no_task(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor):
        """创建独立随访记录（不关联任务）"""
        data = _make_record_data(test_patient.id, test_doctor.id, task_id=None, content="独立记录")
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpRecordService(db_session)
            record = await svc.create(data)

        assert record.task_id is None
        assert record.content == "独立记录"

    @pytest.mark.asyncio
    async def test_get_record_by_id(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor):
        """通过 ID 获取随访记录"""
        data = _make_record_data(test_patient.id, test_doctor.id)
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpRecordService(db_session)
            record = await svc.create(data)

            fetched = await svc.get_by_id(record.id)
            assert fetched is not None
            assert fetched.content == "随访内容"

    @pytest.mark.asyncio
    async def test_get_record_not_found(self, db_session: AsyncSession, tenant_id):
        """获取不存在的记录返回 None"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpRecordService(db_session)
            result = await svc.get_by_id("nonexistent_id")
            assert result is None

    @pytest.mark.asyncio
    async def test_update_record(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor):
        """更新随访记录"""
        data = _make_record_data(test_patient.id, test_doctor.id)
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpRecordService(db_session)
            record = await svc.create(data)

            update_data = FollowUpRecordUpdate(
                content="更新后的随访内容",
                patient_condition=PatientCondition("worsened"),
                next_action="调整治疗方案",
                next_follow_up_date=date.today() + timedelta(days=14),
                attachments=["http://example.com/new_file.pdf"],
            )
            updated = await svc.update(record.id, update_data, operator_id="op-003")

        assert updated is not None
        assert updated.content == "更新后的随访内容"
        assert updated.patient_condition == "worsened"
        assert updated.next_action == "调整治疗方案"

    @pytest.mark.asyncio
    async def test_delete_record(self, db_session: AsyncSession, tenant_id, test_patient, test_doctor):
        """软删除随访记录"""
        data = _make_record_data(test_patient.id, test_doctor.id)
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = FollowUpRecordService(db_session)
            record = await svc.create(data)

            success = await svc.delete(record.id)
            assert success is True

            result = await svc.get_by_id(record.id)
            assert result is None


# ---------------------------------------------------------------------------
# TestSelfReportService
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSelfReportService:
    """SelfReportService 核心逻辑测试"""

    @pytest.mark.asyncio
    async def test_create_self_report(self, db_session: AsyncSession, tenant_id, test_patient):
        """患者提交自报告"""
        data = _make_self_report_data()
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = SelfReportService(db_session)
            report = await svc.create(data, patient_id=test_patient.id, operator_id="user-001")

        assert report is not None
        assert report.id is not None
        assert report.tenant_id == tenant_id
        assert report.patient_id == test_patient.id
        assert report.status == "pending"
        assert report.systolic_bp == 120
        assert report.diastolic_bp == 80
        assert report.blood_glucose == 5.5
        assert report.heart_rate == 72
        assert report.temperature == 36.5
        assert report.symptoms == "轻微头痛"
        assert report.patient_condition == "improved"

    @pytest.mark.asyncio
    async def test_create_self_report_with_task(self, db_session: AsyncSession, tenant_id, test_patient):
        """自报告关联随访任务"""
        data = _make_self_report_data(task_id="some-task-id")
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = SelfReportService(db_session)
            report = await svc.create(data, patient_id=test_patient.id)

        assert report.task_id == "some-task-id"

    @pytest.mark.asyncio
    async def test_review_self_report(self, db_session: AsyncSession, tenant_id, test_patient):
        """医生审核自报告"""
        data = _make_self_report_data()
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = SelfReportService(db_session)
            report = await svc.create(data, patient_id=test_patient.id)
            assert report.status == "pending"

            reviewed = await svc.review(report.id, reviewer_id="doctor-001")
            assert reviewed is not None
            assert reviewed.status == "reviewed"
            assert reviewed.reviewed_by == "doctor-001"
            assert reviewed.reviewed_at is not None

    @pytest.mark.asyncio
    async def test_review_self_report_not_found(self, db_session: AsyncSession, tenant_id):
        """审核不存在的报告返回 None"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = SelfReportService(db_session)
            result = await svc.review("nonexistent_id", reviewer_id="doctor-001")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_self_report_list(self, db_session: AsyncSession, tenant_id, test_patient):
        """查询自报告列表"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = SelfReportService(db_session)
            # 提交两份报告
            data1 = _make_self_report_data(systolic_bp=130, diastolic_bp=85)
            data2 = _make_self_report_data(systolic_bp=140, diastolic_bp=90)
            await svc.create(data1, patient_id=test_patient.id)
            await svc.create(data2, patient_id=test_patient.id)

            reports, total = await svc.get_list(patient_id=test_patient.id)
            assert total == 2

    @pytest.mark.asyncio
    async def test_get_self_report_list_filter_status(self, db_session: AsyncSession, tenant_id, test_patient):
        """按状态筛选自报告列表"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = SelfReportService(db_session)
            data = _make_self_report_data()
            report = await svc.create(data, patient_id=test_patient.id)
            await svc.review(report.id, reviewer_id="doctor-001")

            # 筛选 reviewed
            reports, total = await svc.get_list(patient_id=test_patient.id, status="reviewed")
            assert total == 1
            assert reports[0].status == "reviewed"

            # 筛选 pending
            reports, total = await svc.get_list(patient_id=test_patient.id, status="pending")
            assert total == 0

    @pytest.mark.asyncio
    async def test_get_self_report_by_id(self, db_session: AsyncSession, tenant_id, test_patient):
        """通过 ID 获取自报告"""
        data = _make_self_report_data()
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = SelfReportService(db_session)
            report = await svc.create(data, patient_id=test_patient.id)

            fetched = await svc.get_by_id(report.id)
            assert fetched is not None
            assert fetched.systolic_bp == 120
            assert fetched.status == "pending"

    @pytest.mark.asyncio
    async def test_get_self_report_by_id_not_found(self, db_session: AsyncSession, tenant_id):
        """获取不存在的自报告返回 None"""
        with patch(
            "app.modules.follow_up.service.get_current_tenant_id",
            return_value=tenant_id,
        ):
            svc = SelfReportService(db_session)
            result = await svc.get_by_id("nonexistent_id")
            assert result is None
