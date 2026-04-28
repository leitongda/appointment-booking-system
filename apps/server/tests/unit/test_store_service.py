"""门店服务单元测试

测试门店 CRUD、批量绑定科室/管理员等功能。
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.modules.stores.service import StoreService
from app.schemas.store import StoreCreate, StoreUpdate, StoreQuery
from app.models.store import Store
from app.models.department import Department
from app.models.admin import Admin


@pytest.mark.unit
class TestStoreQueryMixin:
    """门店查询服务测试"""

    async def test_get_by_id(self, db_session, test_store):
        """测试通过ID获取门店"""
        service = StoreService(db_session)
        store = await service.get_by_id(test_store.id)
        assert store is not None
        assert store.id == test_store.id
        assert store.name == "测试门店"

    async def test_get_by_id_not_found(self, db_session):
        """测试获取不存在的门店"""
        service = StoreService(db_session)
        store = await service.get_by_id(str(uuid4()))
        assert store is None

    async def test_get_by_code(self, db_session, test_store):
        """测试通过编码获取门店"""
        # 先给门店设置编码
        test_store.code = "STORE001"
        await db_session.commit()

        service = StoreService(db_session)
        store = await service.get_by_code("STORE001")
        assert store is not None
        assert store.code == "STORE001"

    async def test_get_by_name(self, db_session, test_store):
        """测试通过名称获取门店"""
        service = StoreService(db_session)
        store = await service.get_by_name("测试门店")
        assert store is not None
        assert store.name == "测试门店"

    async def test_check_name_exists(self, db_session, test_store):
        """测试检查名称是否存在"""
        service = StoreService(db_session)
        assert await service.check_name_exists("测试门店") is True
        assert await service.check_name_exists("不存在的门店") is False

    async def test_check_name_exists_exclude_id(self, db_session, test_store):
        """测试检查名称是否存在（排除自身）"""
        service = StoreService(db_session)
        # 排除自身应该返回 False
        assert await service.check_name_exists("测试门店", exclude_id=test_store.id) is False

    async def test_check_code_exists(self, db_session, test_store):
        """测试检查编码是否存在"""
        test_store.code = "STORE001"
        await db_session.commit()

        service = StoreService(db_session)
        assert await service.check_code_exists("STORE001") is True
        assert await service.check_code_exists("STORE999") is False

    async def test_get_list(self, db_session, test_tenant, test_store):
        """测试获取门店列表"""
        # 创建多个门店
        for i in range(3):
            store = Store(
                id=str(uuid4()),
                name=f"门店{i}",
                tenant_id=test_tenant.id,
                status=1,
                created_at=test_store.created_at,
            )
            db_session.add(store)
        await db_session.commit()

        service = StoreService(db_session)
        query = StoreQuery(page=1, page_size=10)
        stores, total = await service.get_list(query)

        assert total >= 4  # 至少有4个门店
        assert len(stores) <= 10

    async def test_get_list_with_keyword(self, db_session, test_store):
        """测试关键字搜索"""
        service = StoreService(db_session)
        query = StoreQuery(keyword="测试")
        stores, total = await service.get_list(query)

        assert total >= 1
        assert any(s.name == "测试门店" for s in stores)

    async def test_get_list_with_status(self, db_session, test_tenant, test_store):
        """测试状态过滤"""
        from datetime import datetime
        # 创建不同状态的门店
        active_store = Store(
            id=str(uuid4()),
            name="活跃门店",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        inactive_store = Store(
            id=str(uuid4()),
            name="停业门店",
            tenant_id=test_tenant.id,
            status=0,
            created_at=datetime.now(),
        )
        db_session.add(active_store)
        db_session.add(inactive_store)
        await db_session.commit()

        service = StoreService(db_session)
        query = StoreQuery(status=1)
        stores, total = await service.get_list(query)

        assert all(s.status == 1 for s in stores)

    async def test_get_all_active(self, db_session, test_store):
        """测试获取所有启用的门店"""
        service = StoreService(db_session)
        stores = await service.get_all_active()

        assert all(s.status == 1 for s in stores)

    async def test_get_department_count(self, db_session, test_tenant, test_store, test_department):
        """测试获取门店的科室数量"""
        service = StoreService(db_session)
        count = await service.get_department_count(test_store.id)
        assert count == 1

    async def test_get_department_counts_batch(self, db_session, test_tenant, test_store, test_department):
        """测试批量获取门店科室数量"""
        # 创建第二个门店
        store2 = Store(
            id=str(uuid4()),
            name="门店2",
            tenant_id=test_tenant.id,
            status=1,
            created_at=test_store.created_at,
        )
        db_session.add(store2)
        await db_session.commit()

        service = StoreService(db_session)
        counts = await service.get_department_counts_batch([test_store.id, store2.id])

        assert counts[test_store.id] == 1
        assert counts[store2.id] == 0

    async def test_get_departments(self, db_session, test_department):
        """测试获取门店的科室列表"""
        service = StoreService(db_session)
        departments = await service.get_departments(test_department.store_id)

        assert len(departments) == 1
        assert departments[0].id == test_department.id

    async def test_get_wechat_config(self, db_session, test_store):
        """测试获取微信配置"""
        test_store.wechat_app_id = "wx123456"
        test_store.wechat_app_secret = "secret123"
        await db_session.commit()

        service = StoreService(db_session)
        config = await service.get_wechat_config(test_store.id)

        assert config is not None
        assert config["app_id"] == "wx123456"
        assert config["app_secret"] == "secret123"


@pytest.mark.unit
class TestStoreMutationMixin:
    """门店变更服务测试"""

    async def test_create_store(self, db_session, test_tenant):
        """测试创建门店"""
        from app.middleware.tenant_context import set_tenant_context
        service = StoreService(db_session)
        data = StoreCreate(
            name="新门店",
            code="NEW001",
            address="新地址",
            phone="13900139000",
        )

        # 设置租户上下文并 Mock quota check
        token = set_tenant_context(test_tenant.id)
        with patch("app.common.quota.check_quota", new_callable=AsyncMock):
            store = await service.create(data)
        set_tenant_context(None)  # 清理上下文

        assert store.name == "新门店"
        assert store.code == "NEW001"
        assert store.status == 1

    async def test_create_store_duplicate_code(self, db_session, test_store, test_tenant):
        """测试创建门店时编码重复"""
        from app.middleware.tenant_context import set_tenant_context
        test_store.code = "DUP001"
        await db_session.commit()

        service = StoreService(db_session)
        data = StoreCreate(
            name="新门店",
            code="DUP001",
        )

        # 设置租户上下文并 Mock quota check
        token = set_tenant_context(test_tenant.id)
        with patch("app.common.quota.check_quota", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="门店编码 DUP001 已存在"):
                await service.create(data)
        set_tenant_context(None)  # 清理上下文

    async def test_update_store(self, db_session, test_store):
        """测试更新门店"""
        service = StoreService(db_session)
        data = StoreUpdate(name="更新后的门店")

        store = await service.update(test_store.id, data)
        assert store is not None
        assert store.name == "更新后的门店"

    async def test_update_store_not_found(self, db_session):
        """测试更新不存在的门店"""
        service = StoreService(db_session)
        data = StoreUpdate(name="新名称")

        store = await service.update(str(uuid4()), data)
        assert store is None

    async def test_update_store_duplicate_code(self, db_session, test_tenant, test_store):
        """测试更新门店时编码重复"""
        # 创建第二个门店
        store2 = Store(
            id=str(uuid4()),
            name="门店2",
            code="STORE002",
            tenant_id=test_tenant.id,
            status=1,
            created_at=test_store.created_at,
        )
        db_session.add(store2)
        await db_session.commit()

        service = StoreService(db_session)
        data = StoreUpdate(code="STORE002")

        with pytest.raises(ValueError, match="门店编码 STORE002 已存在"):
            await service.update(test_store.id, data)

    async def test_delete_store(self, db_session, test_store):
        """测试删除门店"""
        service = StoreService(db_session)
        result = await service.delete(test_store.id)

        assert result is True

        # 验证已删除
        deleted_store = await service.get_by_id(test_store.id)
        assert deleted_store is None

    async def test_delete_store_with_departments(self, db_session, test_store, test_department):
        """测试删除有关联科室的门店"""
        service = StoreService(db_session)

        with pytest.raises(ValueError, match="该门店下有关联科室"):
            await service.delete(test_store.id)

    async def test_update_status(self, db_session, test_store):
        """测试更新门店状态"""
        service = StoreService(db_session)
        store = await service.update_status(test_store.id, 0)

        assert store is not None
        assert store.status == 0

    async def test_batch_bind_departments(self, db_session, test_tenant, test_store):
        """测试批量绑定科室"""
        # 创建两个未绑定门店的科室
        dept1 = Department(
            id=str(uuid4()),
            name="科室1",
            tenant_id=test_tenant.id,
            status=1,
            created_at=test_store.created_at,
        )
        dept2 = Department(
            id=str(uuid4()),
            name="科室2",
            tenant_id=test_tenant.id,
            status=1,
            created_at=test_store.created_at,
        )
        db_session.add_all([dept1, dept2])
        await db_session.commit()

        service = StoreService(db_session)
        count = await service.batch_bind_departments(test_store.id, [dept1.id, dept2.id])

        assert count == 2

        # 验证绑定成功
        dept1_updated = await db_session.get(Department, dept1.id)
        dept2_updated = await db_session.get(Department, dept2.id)
        assert dept1_updated.store_id == test_store.id
        assert dept2_updated.store_id == test_store.id

    async def test_batch_bind_departments_unbind(self, db_session, test_store, test_department):
        """测试批量解绑科室"""
        service = StoreService(db_session)
        # 解绑所有科室
        count = await service.batch_bind_departments(test_store.id, [])

        assert count == 0

        # 验证解绑成功
        dept_updated = await db_session.get(Department, test_department.id)
        assert dept_updated.store_id is None
