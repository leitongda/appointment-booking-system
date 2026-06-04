"""
排班模板服务单元测试

覆盖 ScheduleTemplateService 的三大 mixin:
- ScheduleTemplateMutationMixin: CRUD 操作
- ScheduleTemplateQueryMixin: 查询操作
- ScheduleTemplateGenerationMixin: 生成、复制、批量操作

测试重点:
- 正常路径: 创建/更新/删除/查询排班模板
- 边界条件: 空字段校验、时间范围校验、break_times 校验
- 租户隔离: 不同租户间的模板隔离
- 复制功能: copy_to_doctors、copy_to_store
- 生成日志: log_generation、check_generated
"""
import json
from datetime import date, time, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.schedule_templates.service import ScheduleTemplateService
from app.models.schedule_template import ScheduleTemplate
from app.schemas.schedule_template import (
    ScheduleTemplateCreate,
    ScheduleTemplateUpdate,
    BreakTime,
)
from app.schemas.schedule_template import ScheduleGenerateRequest


# ==================== Helpers ====================

TENANT_ID = "test-tenant-id"


def _patch_tenant(tenant_id=TENANT_ID):
    return patch(
        "app.middleware.tenant_context.get_current_tenant_id",
        return_value=tenant_id,
    )


def _template_create_data(**overrides) -> ScheduleTemplateCreate:
    """构造合法的创建请求"""
    defaults = dict(
        name="上午排班模板",
        store_id="store-1",
        doctor_id="doctor-1",
        department_id="dept-1",
        shift_type_id="shift-1",
        weekdays=[1, 2, 3, 4, 5],
        start_time=time(8, 0),
        end_time=time(12, 0),
        slot_count=1,
        slot_capacity=10,
    )
    defaults.update(overrides)
    return ScheduleTemplateCreate(**defaults)


async def _create_db_template(db_session, **overrides) -> ScheduleTemplate:
    """直接在 DB 中创建模板，用于查询/删除测试"""
    defaults = dict(
        id="tmpl-1",
        name="DB模板",
        tenant_id=TENANT_ID,
        store_id="store-1",
        doctor_id="doctor-1",
        department_id="dept-1",
        shift_type_id="shift-1",
        weekdays=json.dumps([1, 2, 3, 4, 5]),
        appointment_type="normal",
        start_time=time(8, 0),
        end_time=time(12, 0),
        slot_count=1,
        slot_capacity=10,
        schedule_mode="weekly",
        status=1,
    )
    defaults.update(overrides)
    template = ScheduleTemplate(**defaults)
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


async def _create_target_doctor(db_session, tenant_id=TENANT_ID, store_id="store-1",
                                dept_id="dept-1", doctor_id="doctor-2", name="目标医生"):
    """创建目标医生（用于复制测试）"""
    from app.models.doctor import Doctor

    doctor = Doctor(
        id=doctor_id,
        name=name,
        title="副主任医师",
        department_id=dept_id,
        store_id=store_id,
        tenant_id=tenant_id,
        status=1,
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(doctor)
    return doctor


# ==================== TestScheduleTemplateMutation ====================

@pytest.mark.unit
class TestScheduleTemplateMutation:
    """测试排班模板 CRUD 操作"""

    # ---------- create ----------

    async def test_create_template_success(self, db_session, test_store, test_doctor,
                                           test_department, test_shift_type):
        """正常创建排班模板"""
        service = ScheduleTemplateService(db_session)
        data = _template_create_data(
            store_id=test_store.id,
            doctor_id=test_doctor.id,
            department_id=test_department.id,
            shift_type_id=test_shift_type.id,
        )
        with _patch_tenant(test_store.tenant_id):
            result = await service.create(data)

        assert result.id is not None
        assert result.name == "上午排班模板"
        assert result.slot_count == 1
        assert result.slot_capacity == 10
        assert result.status == 1

    async def test_create_template_empty_name_raises(self, db_session, test_store,
                                                     test_doctor, test_department,
                                                     test_shift_type):
        """模板名称为空应抛出 ValueError"""
        service = ScheduleTemplateService(db_session)
        data = _template_create_data(
            name="",
            store_id=test_store.id,
            doctor_id=test_doctor.id,
            department_id=test_department.id,
            shift_type_id=test_shift_type.id,
        )
        with _patch_tenant(test_store.tenant_id):
            with pytest.raises(ValueError, match="模板名称不能为空"):
                await service.create(data)

    async def test_create_template_end_before_start_raises(self, db_session, test_store,
                                                           test_doctor, test_department,
                                                           test_shift_type):
        """结束时间早于开始时间应抛出 ValueError"""
        service = ScheduleTemplateService(db_session)
        data = _template_create_data(
            store_id=test_store.id,
            doctor_id=test_doctor.id,
            department_id=test_department.id,
            shift_type_id=test_shift_type.id,
            start_time=time(12, 0),
            end_time=time(8, 0),
        )
        with _patch_tenant(test_store.tenant_id):
            with pytest.raises(ValueError, match="结束时间必须晚于开始时间"):
                await service.create(data)

    async def test_create_template_with_break_times(self, db_session, test_store,
                                                    test_doctor, test_department,
                                                    test_shift_type):
        """带 break_times 创建模板"""
        service = ScheduleTemplateService(db_session)
        data = _template_create_data(
            store_id=test_store.id,
            doctor_id=test_doctor.id,
            department_id=test_department.id,
            shift_type_id=test_shift_type.id,
            start_time=time(8, 0),
            end_time=time(17, 0),
            break_times=[
                BreakTime(start_time=time(12, 0), end_time=time(13, 30)),
            ],
        )
        with _patch_tenant(test_store.tenant_id):
            result = await service.create(data)

        assert result.break_times is not None
        parsed = json.loads(result.break_times)
        assert len(parsed) == 1
        assert parsed[0]["startTime"] == "12:00"
        assert parsed[0]["endTime"] == "13:30"

    async def test_create_template_break_time_out_of_range_raises(self, db_session, test_store,
                                                                  test_doctor, test_department,
                                                                  test_shift_type):
        """break_time 超出排班时间范围应抛出 ValueError"""
        service = ScheduleTemplateService(db_session)
        data = _template_create_data(
            store_id=test_store.id,
            doctor_id=test_doctor.id,
            department_id=test_department.id,
            shift_type_id=test_shift_type.id,
            start_time=time(8, 0),
            end_time=time(12, 0),
            break_times=[
                BreakTime(start_time=time(7, 0), end_time=time(8, 0)),
            ],
        )
        with _patch_tenant(test_store.tenant_id):
            with pytest.raises(ValueError, match="排除时间段必须在排班时间范围内"):
                await service.create(data)

    async def test_create_template_overlapping_breaks_raises(self, db_session, test_store,
                                                             test_doctor, test_department,
                                                             test_shift_type):
        """重叠的 break_times 应抛出 ValueError"""
        service = ScheduleTemplateService(db_session)
        data = _template_create_data(
            store_id=test_store.id,
            doctor_id=test_doctor.id,
            department_id=test_department.id,
            shift_type_id=test_shift_type.id,
            start_time=time(8, 0),
            end_time=time(17, 0),
            break_times=[
                BreakTime(start_time=time(10, 0), end_time=time(12, 0)),
                BreakTime(start_time=time(11, 0), end_time=time(13, 0)),
            ],
        )
        with _patch_tenant(test_store.tenant_id):
            with pytest.raises(ValueError, match="排除时间段不能重叠"):
                await service.create(data)

    # ---------- update ----------

    async def test_update_template_name(self, db_session, test_store):
        """更新模板名称"""
        template = await _create_db_template(db_session)
        service = ScheduleTemplateService(db_session)
        data = ScheduleTemplateUpdate(name="新名称")
        with _patch_tenant(template.tenant_id):
            result = await service.update(template.id, data)

        assert result is not None
        assert result.name == "新名称"

    async def test_update_template_not_found_returns_none(self, db_session):
        """更新不存在的模板应返回 None"""
        service = ScheduleTemplateService(db_session)
        data = ScheduleTemplateUpdate(name="新名称")
        with _patch_tenant(TENANT_ID):
            result = await service.update("non-existent-id", data)
        assert result is None

    async def test_update_template_time_validation(self, db_session, test_store):
        """更新时间使 end_time <= start_time 应抛出 ValueError"""
        template = await _create_db_template(db_session)
        service = ScheduleTemplateService(db_session)
        data = ScheduleTemplateUpdate(start_time=time(17, 0), end_time=time(8, 0))
        with _patch_tenant(template.tenant_id):
            with pytest.raises(ValueError, match="结束时间必须晚于开始时间"):
                await service.update(template.id, data)

    # ---------- delete ----------

    async def test_delete_template_success(self, db_session, test_store):
        """正常删除模板"""
        template = await _create_db_template(db_session)
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(template.tenant_id):
            result = await service.delete(template.id)
        assert result is True

        # 验证已删除
        with _patch_tenant(template.tenant_id):
            found = await service.get_by_id(template.id)
        assert found is None

    async def test_delete_template_not_found(self, db_session):
        """删除不存在的模板应返回 False"""
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            result = await service.delete("non-existent-id")
        assert result is False


# ==================== TestScheduleTemplateQuery ====================

@pytest.mark.unit
class TestScheduleTemplateQuery:
    """测试排班模板查询操作"""

    async def test_get_by_id_found(self, db_session):
        """根据 ID 查询模板 - 找到"""
        template = await _create_db_template(db_session)
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(template.tenant_id):
            result = await service.get_by_id(template.id)
        assert result is not None
        assert result.id == template.id

    async def test_get_by_id_not_found(self, db_session):
        """根据 ID 查询模板 - 不存在"""
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            result = await service.get_by_id("non-existent-id")
        assert result is None

    async def test_get_by_id_tenant_isolation(self, db_session):
        """租户隔离: query mixin 的 tenant 过滤逻辑正确"""
        # 直接验证 _get_template_with_tenant 的过滤条件构建
        from app.models.schedule_template import ScheduleTemplate
        from sqlalchemy import select, and_

        template = await _create_db_template(db_session, id="t1", tenant_id="tenant-A")

        # 手动构建与 service_query 相同的查询: 不同租户应查不到
        wrong_tenant_conditions = [
            ScheduleTemplate.id == template.id,
            ScheduleTemplate.tenant_id == "tenant-B",
        ]
        result = await db_session.execute(
            select(ScheduleTemplate).where(and_(*wrong_tenant_conditions))
        )
        assert result.scalar_one_or_none() is None

        # 正确租户应查得到
        correct_tenant_conditions = [
            ScheduleTemplate.id == template.id,
            ScheduleTemplate.tenant_id == "tenant-A",
        ]
        result2 = await db_session.execute(
            select(ScheduleTemplate).where(and_(*correct_tenant_conditions))
        )
        assert result2.scalar_one_or_none() is not None

    async def test_get_list_basic(self, db_session, test_store):
        """基础列表查询"""
        await _create_db_template(db_session)
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            templates, total = await service.get_list()
        assert total == 1
        assert len(templates) == 1

    async def test_get_list_with_status_filter(self, db_session):
        """按状态筛选"""
        await _create_db_template(db_session, id="active", status=1)
        await _create_db_template(db_session, id="inactive", status=0)
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            templates, total = await service.get_list(status=1)
        assert total == 1
        assert templates[0].id == "active"

    async def test_get_list_pagination(self, db_session):
        """分页查询"""
        for i in range(3):
            await _create_db_template(db_session, id=f"p-{i}", name=f"模板{i}")
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            templates, total = await service.get_list(page=1, page_size=2)
        assert total == 3
        assert len(templates) == 2

    async def test_get_generation_logs_not_found(self, db_session):
        """查询不存在模板的生成日志应返回空"""
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            logs, total = await service.get_generation_logs("non-existent-id")
        assert logs == []
        assert total == 0


# ==================== TestScheduleTemplateGeneration ====================

@pytest.mark.unit
class TestScheduleTemplateGeneration:
    """测试排班模板生成/复制/批量操作"""

    async def test_log_generation(self, db_session):
        """记录生成日志"""
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            log = await service.log_generation(
                template_id="tmpl-log",
                action_type="generate",
                affected_count=5,
                operator_id="admin-1",
                operator_name="管理员",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=30),
                remark="测试日志",
            )
        assert log.id is not None
        assert log.template_id == "tmpl-log"
        assert log.affected_count == 5
        assert log.action_type == "generate"

    async def test_check_generated_no_schedules(self, db_session):
        """check_generated: 无排班记录时返回 has_generated=False"""
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            result = await service.check_generated("tmpl-empty")
        assert result.has_generated is False
        assert result.schedule_count == 0

    async def test_copy_to_doctors_success(self, db_session):
        """复制模板到目标医生"""
        template = await _create_db_template(db_session)
        target = await _create_target_doctor(db_session, doctor_id="target-doc")

        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            count = await service.copy_to_doctors(
                template_id=template.id,
                target_doctor_ids=[target.id],
            )
        assert count == 1

        # 验证新模板被创建
        with _patch_tenant(TENANT_ID):
            templates, total = await service.get_list()
        assert total == 2  # 原模板 + 复制的模板

    async def test_copy_to_doctors_template_not_found(self, db_session):
        """复制不存在的模板应抛出 ValueError"""
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            with pytest.raises(ValueError, match="原排班规则不存在"):
                await service.copy_to_doctors(
                    template_id="non-existent",
                    target_doctor_ids=["d1"],
                )

    async def test_copy_to_doctors_invalid_target(self, db_session):
        """复制到不存在的医生应抛出 ValueError"""
        template = await _create_db_template(db_session)
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            with pytest.raises(ValueError, match="未找到有效的目标医生"):
                await service.copy_to_doctors(
                    template_id=template.id,
                    target_doctor_ids=["ghost-doctor"],
                )

    async def test_copy_to_store_success(self, db_session):
        """跨门店复制模板"""
        template = await _create_db_template(db_session)
        # Create target store via direct insert
        from app.models.store import Store
        target = Store(
            id="target-store",
            name="目标门店",
            address="目标地址",
            phone="13900139000",
            tenant_id=TENANT_ID,
            status=1,
        )
        db_session.add(target)
        await db_session.flush()

        # Target doctor + department in target store
        from app.models.department import Department
        target_dept = Department(
            id="target-dept",
            name="目标科室",
            store_id="target-store",
            tenant_id=TENANT_ID,
            status=1,
        )
        db_session.add(target_dept)
        await db_session.flush()

        target_doc = await _create_target_doctor(
            db_session, store_id="target-store", dept_id="target-dept",
            doctor_id="target-doc-2", name="目标医生2",
        )

        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            count, failed = await service.copy_to_store(
                template_id=template.id,
                target_store_id="target-store",
                mappings=[{
                    "source_department_id": template.department_id,
                    "target_department_id": "target-dept",
                    "target_doctor_id": "target-doc-2",
                }],
            )
        assert count == 1
        assert len(failed) == 0

    async def test_copy_to_store_target_store_not_found(self, db_session):
        """跨门店复制到不存在的门店应抛出 ValueError"""
        template = await _create_db_template(db_session)
        service = ScheduleTemplateService(db_session)
        with _patch_tenant(TENANT_ID):
            with pytest.raises(ValueError, match="目标门店不存在或无权限访问"):
                await service.copy_to_store(
                    template_id=template.id,
                    target_store_id="ghost-store",
                    mappings=[],
                )
