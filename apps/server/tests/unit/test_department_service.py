"""科室服务单元测试

测试科室 CRUD、树形结构、批量绑定医生等功能。
"""

import pytest
from uuid import uuid4

from app.modules.departments.service import DepartmentService
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.models.department import Department
from app.models.doctor import Doctor


@pytest.mark.unit
class TestDepartmentServiceQuery:
    """科室查询服务测试"""

    async def test_get_by_id(self, db_session, test_department):
        """测试通过ID获取科室"""
        service = DepartmentService(db_session)
        dept = await service.get_by_id(test_department.id)

        assert dept is not None
        assert dept.id == test_department.id
        assert dept.name == "测试科室"

    async def test_get_by_id_not_found(self, db_session):
        """测试获取不存在的科室"""
        service = DepartmentService(db_session)
        dept = await service.get_by_id(str(uuid4()))
        assert dept is None

    async def test_get_list(self, db_session, test_tenant, test_department):
        """测试获取科室列表"""
        # 创建多个科室
        for i in range(3):
            dept = Department(
                id=str(uuid4()),
                name=f"科室{i}",
                tenant_id=test_tenant.id,
                status=1,
                created_at=test_department.created_at,
            )
            db_session.add(dept)
        await db_session.commit()

        service = DepartmentService(db_session)
        departments, total = await service.get_list(page=1, page_size=10)

        assert total >= 4
        assert len(departments) <= 10

    async def test_get_list_with_name_filter(self, db_session, test_department):
        """测试按名称过滤"""
        service = DepartmentService(db_session)
        departments, total = await service.get_list(name="测试")

        assert total >= 1
        assert any(d.name == "测试科室" for d in departments)

    async def test_get_list_with_status_filter(self, db_session, test_tenant, test_department):
        """测试按状态过滤"""
        from datetime import datetime
        # 创建不同状态的科室
        active_dept = Department(
            id=str(uuid4()),
            name="活跃科室",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        inactive_dept = Department(
            id=str(uuid4()),
            name="停用科室",
            tenant_id=test_tenant.id,
            status=0,
            created_at=datetime.now(),
        )
        db_session.add_all([active_dept, inactive_dept])
        await db_session.commit()

        service = DepartmentService(db_session)
        departments, total = await service.get_list(status=1)

        assert all(d.status == 1 for d in departments)

    async def test_get_list_with_parent_filter(self, db_session, test_tenant, test_department):
        """测试按父级过滤"""
        # 创建子科室
        child_dept = Department(
            id=str(uuid4()),
            name="子科室",
            parent_id=test_department.id,
            tenant_id=test_tenant.id,
            status=1,
            created_at=test_department.created_at,
        )
        db_session.add(child_dept)
        await db_session.commit()

        service = DepartmentService(db_session)
        departments, total = await service.get_list(parent_id=test_department.id)

        assert total == 1
        assert departments[0].name == "子科室"

    async def test_get_tree(self, db_session, test_tenant, test_department):
        """测试获取科室树"""
        # 创建父子科室
        parent = Department(
            id=str(uuid4()),
            name="内科",
            tenant_id=test_tenant.id,
            status=1,
            sort_order=10,
            created_at=test_department.created_at,
        )
        child = Department(
            id=str(uuid4()),
            name="心内科",
            parent_id=parent.id,
            tenant_id=test_tenant.id,
            status=1,
            sort_order=5,
            created_at=test_department.created_at,
        )
        db_session.add_all([parent, child])
        await db_session.commit()

        service = DepartmentService(db_session)
        tree = await service.get_tree()

        # 验证树结构
        assert len(tree) > 0
        # 找到内科节点
        internal_node = next((n for n in tree if n.name == "内科"), None)
        assert internal_node is not None
        # 验证子节点
        assert len(internal_node.children) > 0
        assert any(c.name == "心内科" for c in internal_node.children)

    async def test_get_tree_with_store_filter(self, db_session, test_tenant, test_store, test_department):
        """测试按门店过滤科室树"""
        service = DepartmentService(db_session)
        tree = await service.get_tree(store_id=test_store.id)

        assert len(tree) >= 1
        # 验证所有科室都属于指定门店
        for node in tree:
            # 这里需要通过数据库验证，因为树节点只包含基本信息
            dept = await service.get_by_id(node.id)
            assert dept.store_id == test_store.id

    async def test_get_hot(self, db_session, test_tenant, test_store, test_department):
        """测试获取热门科室"""
        from datetime import datetime
        # 创建热门科室
        hot_dept = Department(
            id=str(uuid4()),
            name="热门科室",
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            is_hot=1,
            status=1,
            sort_order=10,
            created_at=datetime.now(),
        )
        db_session.add(hot_dept)
        await db_session.commit()

        service = DepartmentService(db_session)
        hot_depts = await service.get_hot(limit=5)

        assert any(d.name == "热门科室" for d in hot_depts)

    async def test_get_all_active(self, db_session, test_tenant, test_store):
        """测试获取所有启用的科室"""
        service = DepartmentService(db_session)
        departments = await service.get_all_active(store_id=test_store.id)

        assert all(d.status == 1 for d in departments)

    async def test_get_doctors(self, db_session, test_tenant, test_department, test_store):
        """测试获取科室的医生列表"""
        # 创建医生
        doctor = Doctor(
            id=str(uuid4()),
            name="测试医生2",
            tenant_id=test_tenant.id,
            department_id=test_department.id,
            store_id=test_store.id,
            status=1,
            created_at=test_department.created_at,
        )
        db_session.add(doctor)
        await db_session.commit()

        service = DepartmentService(db_session)
        doctors = await service.get_doctors(test_department.id)

        assert len(doctors) >= 1

    async def test_get_all_doctors(self, db_session, test_tenant, test_store, test_doctor, test_department):
        """测试获取所有可绑定的医生"""
        from datetime import datetime
        # 创建一个临时科室，用于创建未绑定的医生
        temp_dept = Department(
            id=str(uuid4()),
            name="临时科室",
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(temp_dept)
        await db_session.flush()

        # 创建未绑定到目标科室的医生
        doctor = Doctor(
            id=str(uuid4()),
            name="待绑定医生",
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            department_id=temp_dept.id,  # 绑定到临时科室
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(doctor)
        await db_session.commit()

        service = DepartmentService(db_session)
        # get_all_doctors 返回所有启用的医生，不按科室过滤
        doctors = await service.get_all_doctors(store_id=test_store.id)

        assert any(d.name == "待绑定医生" for d in doctors)


@pytest.mark.unit
class TestDepartmentServiceMutation:
    """科室变更服务测试"""

    async def test_create_department(self, db_session, test_tenant, test_store):
        """测试创建科室"""
        service = DepartmentService(db_session)
        data = DepartmentCreate(
            name="新科室",
            store_id=test_store.id,
            description="科室描述",
            status=1,
        )

        dept = await service.create(data)

        assert dept.name == "新科室"
        assert dept.store_id == test_store.id

    async def test_create_department_with_parent(self, db_session, test_tenant, test_department):
        """测试创建子科室"""
        service = DepartmentService(db_session)
        data = DepartmentCreate(
            name="子科室",
            parent_id=test_department.id,
            status=1,
        )

        dept = await service.create(data)

        assert dept.name == "子科室"
        assert dept.parent_id == test_department.id

    async def test_update_department(self, db_session, test_department):
        """测试更新科室"""
        service = DepartmentService(db_session)
        data = DepartmentUpdate(name="更新后的科室")

        dept = await service.update(test_department.id, data)

        assert dept is not None
        assert dept.name == "更新后的科室"

    async def test_update_department_not_found(self, db_session):
        """测试更新不存在的科室"""
        service = DepartmentService(db_session)
        data = DepartmentUpdate(name="新名称")

        dept = await service.update(str(uuid4()), data)

        assert dept is None

    async def test_delete_department(self, db_session, test_department):
        """测试删除科室"""
        service = DepartmentService(db_session)
        result = await service.delete(test_department.id)

        assert result is True

        # 验证已删除
        deleted_dept = await service.get_by_id(test_department.id)
        assert deleted_dept is None

    async def test_delete_department_with_children(self, db_session, test_tenant, test_department):
        """测试删除有子科室的科室"""
        # 创建子科室
        child = Department(
            id=str(uuid4()),
            name="子科室",
            parent_id=test_department.id,
            tenant_id=test_tenant.id,
            status=1,
            created_at=test_department.created_at,
        )
        db_session.add(child)
        await db_session.commit()

        service = DepartmentService(db_session)

        with pytest.raises(ValueError, match="该科室下有子科室"):
            await service.delete(test_department.id)

    async def test_batch_bind_doctors(self, db_session, test_tenant, test_store, test_department):
        """测试批量绑定医生"""
        from datetime import datetime
        # 创建临时科室
        temp_dept = Department(
            id=str(uuid4()),
            name="临时科室",
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(temp_dept)
        await db_session.flush()

        # 创建未绑定到目标科室的医生
        doctor1 = Doctor(
            id=str(uuid4()),
            name="医生1",
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            department_id=temp_dept.id,
            status=1,
            created_at=datetime.now(),
        )
        doctor2 = Doctor(
            id=str(uuid4()),
            name="医生2",
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            department_id=temp_dept.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add_all([doctor1, doctor2])
        await db_session.commit()

        service = DepartmentService(db_session)
        count = await service.batch_bind_doctors(
            test_department.id, [doctor1.id, doctor2.id]
        )

        assert count == 2

        # 验证绑定成功
        doctor1_updated = await db_session.get(Doctor, doctor1.id)
        doctor2_updated = await db_session.get(Doctor, doctor2.id)
        assert doctor1_updated.department_id == test_department.id
        assert doctor2_updated.department_id == test_department.id

    async def test_batch_bind_doctors_store_mismatch(
        self, db_session, test_tenant, test_department, test_store
    ):
        """测试绑定医生时门店不匹配"""
        from datetime import datetime
        from app.models.store import Store
        # 创建不同门店
        other_store = Store(
            id=str(uuid4()),
            name="其他门店",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(other_store)
        await db_session.flush()

        # 创建临时科室
        temp_dept = Department(
            id=str(uuid4()),
            name="临时科室",
            tenant_id=test_tenant.id,
            store_id=other_store.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(temp_dept)
        await db_session.flush()

        # 创建不同门店的医生
        doctor = Doctor(
            id=str(uuid4()),
            name="其他门店医生",
            tenant_id=test_tenant.id,
            store_id=other_store.id,
            department_id=temp_dept.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(doctor)
        await db_session.commit()

        service = DepartmentService(db_session)

        with pytest.raises(ValueError, match="所属门店与科室门店不一致"):
            await service.batch_bind_doctors(test_department.id, [doctor.id])

    async def _create_store(self, db_session, test_tenant):
        """辅助方法：创建门店"""
        from app.models.store import Store
        from datetime import datetime

        store = Store(
            id=str(uuid4()),
            name="其他门店",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(store)
        await db_session.commit()
        await db_session.refresh(store)
        return store

    async def test_batch_bind_doctors_unbind(self, db_session, test_tenant, test_store, test_doctor, test_department):
        """测试批量解绑医生"""
        from datetime import datetime
        # 创建临时科室用于转移医生
        temp_dept = Department(
            id=str(uuid4()),
            name="临时科室",
            tenant_id=test_tenant.id,
            store_id=test_store.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(temp_dept)
        await db_session.flush()

        # 将test_doctor转移到临时科室
        test_doctor.department_id = temp_dept.id
        await db_session.commit()

        service = DepartmentService(db_session)
        # 将test_doctor绑定回test_department
        count = await service.batch_bind_doctors(test_department.id, [test_doctor.id])

        assert count == 1

        # 验证绑定成功
        doctor_updated = await db_session.get(Doctor, test_doctor.id)
        assert doctor_updated.department_id == test_department.id

    async def test_batch_update_sort_order(self, db_session, test_tenant, test_department):
        """测试批量更新排序"""
        # 创建多个科室
        dept1 = Department(
            id=str(uuid4()),
            name="科室1",
            tenant_id=test_tenant.id,
            sort_order=1,
            status=1,
            created_at=test_department.created_at,
        )
        dept2 = Department(
            id=str(uuid4()),
            name="科室2",
            tenant_id=test_tenant.id,
            sort_order=2,
            status=1,
            created_at=test_department.created_at,
        )
        db_session.add_all([dept1, dept2])
        await db_session.commit()

        service = DepartmentService(db_session)
        items = [
            {"id": dept1.id, "sort_order": 10},
            {"id": dept2.id, "sort_order": 20},
        ]
        count = await service.batch_update_sort_order(items)

        assert count == 2

        # 验证排序已更新
        dept1_updated = await db_session.get(Department, dept1.id)
        dept2_updated = await db_session.get(Department, dept2.id)
        assert dept1_updated.sort_order == 10
        assert dept2_updated.sort_order == 20
