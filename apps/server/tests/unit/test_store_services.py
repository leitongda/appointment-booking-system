"""门店服务补充单元测试

覆盖 test_store_service.py 未涉及的场景：
- 租户隔离（查询和变更操作）
- 批量操作边界条件
- 门店 email 字段 CRUD
- 删除不存在的门店
- wechat 配置查询不存在的门店
- get_department_counts_batch 空输入
- get_list 城市筛选
- get_admins 查询
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.modules.stores.service import StoreService
from app.schemas.store import StoreCreate, StoreUpdate, StoreQuery
from app.models.store import Store
from app.models.department import Department


@pytest.mark.unit
class TestStoreServiceMutation:
    """门店变更操作补充测试"""

    async def test_create_store_sets_tenant_id(self, db_session, test_tenant):
        """创建门店时应正确设置 tenant_id"""
        from app.middleware.tenant_context import set_tenant_context

        service = StoreService(db_session)
        data = StoreCreate(name="租户门店", code="T001")

        token = set_tenant_context(test_tenant.id)
        with patch("app.common.quota.check_quota", new_callable=AsyncMock):
            store = await service.create(data)
        set_tenant_context(None)

        assert store.tenant_id == test_tenant.id
        assert store.name == "租户门店"

    async def test_create_store_with_email(self, db_session, test_tenant):
        """创建门店时设置 email 字段"""
        from app.middleware.tenant_context import set_tenant_context

        service = StoreService(db_session)
        data = StoreCreate(name="邮件门店", email="store@example.com")

        token = set_tenant_context(test_tenant.id)
        with patch("app.common.quota.check_quota", new_callable=AsyncMock):
            store = await service.create(data)
        set_tenant_context(None)

        assert store.email == "store@example.com"

    async def test_create_store_no_code_skips_duplicate_check(self, db_session, test_tenant):
        """创建门店时不传 code 应跳过编码重复检查"""
        from app.middleware.tenant_context import set_tenant_context

        service = StoreService(db_session)
        data = StoreCreate(name="无编码门店")

        token = set_tenant_context(test_tenant.id)
        with patch("app.common.quota.check_quota", new_callable=AsyncMock):
            store = await service.create(data)
        set_tenant_context(None)

        assert store.code is None
        assert store.name == "无编码门店"

    async def test_update_store_email(self, db_session, test_store):
        """更新门店 email 字段"""
        service = StoreService(db_session)
        data = StoreUpdate(email="updated@example.com")

        store = await service.update(test_store.id, data)
        assert store is not None
        assert store.email == "updated@example.com"

    async def test_update_store_not_found_returns_none(self, db_session):
        """更新不存在的门店应返回 None"""
        service = StoreService(db_session)
        data = StoreUpdate(name="ghost")
        result = await service.update(str(uuid4()), data)
        assert result is None

    async def test_delete_store_not_found_returns_false(self, db_session):
        """删除不存在的门店应返回 False"""
        service = StoreService(db_session)
        result = await service.delete(str(uuid4()))
        assert result is False

    async def test_update_status_not_found(self, db_session):
        """更新不存在门店的状态应返回 None"""
        service = StoreService(db_session)
        result = await service.update_status(str(uuid4()), 1)
        assert result is None

    async def test_update_status_set_disabled(self, db_session, test_store):
        """门店状态设置为禁用(2)"""
        service = StoreService(db_session)
        store = await service.update_status(test_store.id, 2)
        assert store is not None
        assert store.status == 2

    async def test_update_store_multiple_fields(self, db_session, test_store):
        """同时更新多个字段"""
        service = StoreService(db_session)
        data = StoreUpdate(
            name="多字段更新",
            phone="13900139000",
            city="深圳",
            email="multi@example.com",
            sort_order=99,
        )

        store = await service.update(test_store.id, data)
        assert store is not None
        assert store.name == "多字段更新"
        assert store.phone == "13900139000"
        assert store.city == "深圳"
        assert store.email == "multi@example.com"
        assert store.sort_order == 99

    async def test_update_wechat_config_not_found(self, db_session):
        """更新不存在门店的微信配置应返回 None"""
        service = StoreService(db_session)
        result = await service.update_wechat_config(str(uuid4()), {"wechat_app_id": "wx123"})
        assert result is None

    async def test_update_wechat_config(self, db_session, test_store):
        """更新门店微信配置"""
        service = StoreService(db_session)
        config = {
            "wechat_app_id": "wx_new_app",
            "wechat_mch_id": "mch_new",
        }
        store = await service.update_wechat_config(test_store.id, config)
        assert store is not None
        assert store.wechat_app_id == "wx_new_app"
        assert store.wechat_mch_id == "mch_new"

    async def test_update_wechat_config_ignores_unknown_fields(self, db_session, test_store):
        """更新微信配置时忽略不存在的字段"""
        service = StoreService(db_session)
        original_app_id = test_store.wechat_app_id
        config = {"nonexistent_field": "value", "wechat_app_id": "wx_ok"}
        store = await service.update_wechat_config(test_store.id, config)
        assert store is not None
        assert store.wechat_app_id == "wx_ok"


@pytest.mark.unit
class TestStoreTenantIsolation:
    """门店租户隔离测试"""

    async def test_get_by_id_cross_tenant_returns_none(self, db_session, test_tenant):
        """跨租户查询门店应返回 None"""
        from app.middleware.tenant_context import set_tenant_context

        # 创建属于 test_tenant 的门店
        store = Store(
            id=str(uuid4()),
            name="租户A门店",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(store)
        await db_session.commit()

        # 用另一个租户 ID 查询
        other_tenant_id = str(uuid4())
        service = StoreService(db_session)
        set_tenant_context(other_tenant_id)
        result = await service.get_by_id(store.id)
        set_tenant_context(None)

        assert result is None

    async def test_get_by_code_cross_tenant_returns_none(self, db_session, test_tenant):
        """跨租户按编码查询门店应返回 None"""
        from app.middleware.tenant_context import set_tenant_context

        store = Store(
            id=str(uuid4()),
            name="编码门店",
            code="CROSS001",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(store)
        await db_session.commit()

        other_tenant_id = str(uuid4())
        service = StoreService(db_session)
        set_tenant_context(other_tenant_id)
        result = await service.get_by_code("CROSS001")
        set_tenant_context(None)

        assert result is None

    async def test_get_by_name_cross_tenant_returns_none(self, db_session, test_tenant):
        """跨租户按名称查询门店应返回 None"""
        from app.middleware.tenant_context import set_tenant_context

        store = Store(
            id=str(uuid4()),
            name="隔离门店",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(store)
        await db_session.commit()

        other_tenant_id = str(uuid4())
        service = StoreService(db_session)
        set_tenant_context(other_tenant_id)
        result = await service.get_by_name("隔离门店")
        set_tenant_context(None)

        assert result is None

    async def test_check_name_exists_cross_tenant(self, db_session, test_tenant):
        """跨租户检查名称是否存在应返回 False"""
        from app.middleware.tenant_context import set_tenant_context

        store = Store(
            id=str(uuid4()),
            name="隔离检查门店",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(store)
        await db_session.commit()

        other_tenant_id = str(uuid4())
        service = StoreService(db_session)
        set_tenant_context(other_tenant_id)
        result = await service.check_name_exists("隔离检查门店")
        set_tenant_context(None)

        assert result is False

    async def test_get_all_active_cross_tenant(self, db_session, test_tenant):
        """跨租户获取所有启用门店应返回空列表"""
        from app.middleware.tenant_context import set_tenant_context

        store = Store(
            id=str(uuid4()),
            name="活跃门店",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(store)
        await db_session.commit()

        other_tenant_id = str(uuid4())
        service = StoreService(db_session)
        set_tenant_context(other_tenant_id)
        result = await service.get_all_active()
        set_tenant_context(None)

        assert len(result) == 0

    async def test_get_list_cross_tenant(self, db_session, test_tenant):
        """跨租户查询门店列表应返回空"""
        from app.middleware.tenant_context import set_tenant_context

        store = Store(
            id=str(uuid4()),
            name="列表门店",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(store)
        await db_session.commit()

        other_tenant_id = str(uuid4())
        service = StoreService(db_session)
        set_tenant_context(other_tenant_id)
        stores, total = await service.get_list(StoreQuery())
        set_tenant_context(None)

        assert total == 0
        assert len(stores) == 0


@pytest.mark.unit
class TestStoreQueryEdgeCases:
    """门店查询边界条件测试"""

    async def test_get_list_with_city_filter(self, db_session, test_tenant, test_store):
        """按城市筛选门店列表"""
        service = StoreService(db_session)
        query = StoreQuery(city="北京")
        stores, total = await service.get_list(query)

        # test_store 没有设置 city，不应出现在结果中
        assert total == 0 or all(s.city == "北京" for s in stores)

    async def test_get_department_counts_batch_empty_input(self, db_session):
        """批量查询科室数量时传入空列表"""
        service = StoreService(db_session)
        counts = await service.get_department_counts_batch([])
        assert counts == {}

    async def test_get_department_counts_batch_no_departments(self, db_session, test_store):
        """批量查询门店科室数量 — 门店无科室时返回 0"""
        service = StoreService(db_session)
        counts = await service.get_department_counts_batch([test_store.id])
        assert counts[test_store.id] == 0

    async def test_get_wechat_config_returns_none_for_missing_store(self, db_session):
        """查询不存在门店的微信配置应返回 None"""
        service = StoreService(db_session)
        result = await service.get_wechat_config(str(uuid4()))
        assert result is None

    async def test_get_wechat_config_no_fields_set(self, db_session, test_store):
        """门店未设置微信配置字段时返回 None 值"""
        service = StoreService(db_session)
        config = await service.get_wechat_config(test_store.id)
        assert config is not None
        assert config["app_id"] is None
        assert config["app_secret"] is None
        assert config["mch_id"] is None

    async def test_get_list_default_pagination(self, db_session, test_store):
        """默认分页参数应正常工作"""
        service = StoreService(db_session)
        query = StoreQuery()  # page=1, page_size=10
        stores, total = await service.get_list(query)
        assert total >= 1
        assert len(stores) >= 1


@pytest.mark.unit
class TestStoreBatchOperationsEdgeCases:
    """门店批量操作边界条件测试"""

    async def test_batch_bind_departments_empty_list(self, db_session, test_store, test_department):
        """绑定空列表应解绑所有科室"""
        service = StoreService(db_session)
        count = await service.batch_bind_departments(test_store.id, [])
        assert count == 0

        dept = await db_session.get(Department, test_department.id)
        assert dept.store_id is None

    async def test_batch_bind_departments_store_not_found(self, db_session):
        """绑定科室到不存在的门店应抛出异常"""
        service = StoreService(db_session)
        with pytest.raises(ValueError, match="门店不存在"):
            await service.batch_bind_departments(str(uuid4()), [])

    async def test_batch_bind_admins_store_not_found(self, db_session):
        """绑定管理员到不存在的门店应抛出异常"""
        service = StoreService(db_session)
        with pytest.raises(ValueError, match="门店不存在"):
            await service.batch_bind_admins(str(uuid4()), [])

    async def test_batch_bind_admins_empty_list(self, db_session, test_store):
        """绑定管理员空列表不应报错"""
        service = StoreService(db_session)
        count = await service.batch_bind_admins(test_store.id, [])
        assert count == 0

    async def test_batch_bind_departments_cross_tenant_not_found(self, db_session, test_tenant):
        """跨租户批量绑定科室 — get_by_id 因租户过滤返回 None，报门店不存在

        注意：batch_bind_departments 内部的租户隔离校验（"无权操作此门店"）
        在 get_by_id 已按租户过滤的前提下是不可达的死代码。
        """
        from app.middleware.tenant_context import set_tenant_context

        store = Store(
            id=str(uuid4()),
            name="隔离绑定门店",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(store)
        await db_session.commit()

        other_tenant_id = str(uuid4())
        service = StoreService(db_session)
        set_tenant_context(other_tenant_id)
        with pytest.raises(ValueError, match="门店不存在"):
            await service.batch_bind_departments(store.id, [])
        set_tenant_context(None)

    async def test_batch_bind_admins_cross_tenant_not_found(self, db_session, test_tenant):
        """跨租户批量绑定管理员 — get_by_id 因租户过滤返回 None"""
        from app.middleware.tenant_context import set_tenant_context

        store = Store(
            id=str(uuid4()),
            name="隔离绑定管理员门店",
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
        )
        db_session.add(store)
        await db_session.commit()

        other_tenant_id = str(uuid4())
        service = StoreService(db_session)
        set_tenant_context(other_tenant_id)
        with pytest.raises(ValueError, match="门店不存在"):
            await service.batch_bind_admins(store.id, [])
        set_tenant_context(None)
