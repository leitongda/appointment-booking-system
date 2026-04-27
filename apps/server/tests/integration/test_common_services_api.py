"""常见服务和健康提醒 API 集成测试

覆盖:
- GET /api/v1/content/common-services — 返回空列表或种子数据
- GET /api/v1/content/health-reminders/config — 返回健康提醒配置
- GET /api/v1/content/health-reminders/my 未登录 — 返回 401
- GET /api/v1/content/health-reminders/my 已登录 — 返回用户提醒
- 租户隔离：不同 tenant_id 看到不同数据
"""
import json
import pytest
from datetime import datetime
from uuid import uuid4

from app.models.common_service import CommonService, HealthReminder
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context


@pytest.mark.asyncio
async def test_get_common_services_empty(async_client, db_session, test_tenant):
    """获取常见服务列表 - 空列表"""
    # 设置租户上下文
    set_tenant_context(test_tenant.id, test_tenant.tenant_code)

    response = await async_client.get(
        "/api/v1/content/common-services",
        headers={"X-Tenant-ID": test_tenant.id}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["items"] == []

    # 清理
    clear_tenant_context()


@pytest.mark.asyncio
async def test_get_common_services_with_data(async_client, db_session, test_tenant):
    """获取常见服务列表 - 有数据"""
    set_tenant_context(test_tenant.id, test_tenant.tenant_code)

    # 创建测试数据
    service1 = CommonService(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="预约挂号",
        code="appointment_booking",
        icon="calendar",
        variant="blue",
        link_type=1,
        link_url="/pages/appointment/index",
        sort_order=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    service2 = CommonService(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="在线咨询",
        code="online_consult",
        icon="message",
        variant="green",
        link_type=1,
        link_url="/pages/consult/index",
        sort_order=2,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([service1, service2])
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/content/common-services",
        headers={"X-Tenant-ID": test_tenant.id}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    items = data["data"]["items"]
    assert len(items) == 2
    assert items[0]["name"] == "预约挂号"
    assert items[1]["name"] == "在线咨询"

    clear_tenant_context()


@pytest.mark.asyncio
async def test_get_common_services_filter_by_status(async_client, db_session, test_tenant):
    """获取常见服务列表 - 状态过滤"""
    set_tenant_context(test_tenant.id, test_tenant.tenant_code)

    # 创建测试数据（一个启用，一个禁用）
    service1 = CommonService(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="启用服务",
        code="enabled_service",
        icon="check",
        variant="green",
        link_type=1,
        link_url="/pages/enabled",
        sort_order=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    service2 = CommonService(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="禁用服务",
        code="disabled_service",
        icon="close",
        variant="red",
        link_type=1,
        link_url="/pages/disabled",
        sort_order=2,
        status=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([service1, service2])
    await db_session.commit()

    # 只获取启用的服务
    response = await async_client.get(
        "/api/v1/content/common-services?status=1",
        headers={"X-Tenant-ID": test_tenant.id}
    )

    assert response.status_code == 200
    data = response.json()
    items = data["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "启用服务"

    clear_tenant_context()


@pytest.mark.asyncio
async def test_get_health_reminder_config_empty(async_client, db_session, test_tenant):
    """获取健康提醒配置 - 空列表"""
    set_tenant_context(test_tenant.id, test_tenant.tenant_code)

    response = await async_client.get(
        "/api/v1/content/health-reminders/config",
        headers={"X-Tenant-ID": test_tenant.id}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"] == []

    clear_tenant_context()


@pytest.mark.asyncio
async def test_get_health_reminder_config_with_data(async_client, db_session, test_tenant):
    """获取健康提醒配置 - 有数据"""
    set_tenant_context(test_tenant.id, test_tenant.tenant_code)

    # 创建测试数据
    reminder1 = HealthReminder(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        reminder_type="checkup",
        name="常规体检",
        title="年度体检提醒",
        content="定期体检可以及早发现健康问题",
        tips='["体检前一天晚上10点后避免进食", "体检前三天保持清淡饮食"]',
        recommended_interval=365,
        sort_order=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    reminder2 = HealthReminder(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        reminder_type="gynecological",
        name="妇科检查",
        title="女性健康检查",
        content="建议成年女性每年进行一次妇科检查",
        tips='["检查时间应避开月经期"]',
        recommended_interval=365,
        sort_order=2,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([reminder1, reminder2])
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/content/health-reminders/config",
        headers={"X-Tenant-ID": test_tenant.id}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    items = data["data"]
    assert len(items) == 2
    assert items[0]["reminderType"] == "checkup"
    assert items[0]["name"] == "常规体检"
    assert items[0]["tips"] == ["体检前一天晚上10点后避免进食", "体检前三天保持清淡饮食"]

    clear_tenant_context()


@pytest.mark.asyncio
async def test_get_health_reminder_config_filter_by_type(async_client, db_session, test_tenant):
    """获取健康提醒配置 - 按类型过滤"""
    set_tenant_context(test_tenant.id, test_tenant.tenant_code)

    # 创建不同类型的提醒
    reminder1 = HealthReminder(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        reminder_type="checkup",
        name="常规体检",
        content="定期体检",
        recommended_interval=365,
        sort_order=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    reminder2 = HealthReminder(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        reminder_type="dental",
        name="口腔检查",
        content="口腔健康",
        recommended_interval=180,
        sort_order=2,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([reminder1, reminder2])
    await db_session.commit()

    # 只获取体检类型的提醒
    response = await async_client.get(
        "/api/v1/content/health-reminders/config?reminder_type=checkup",
        headers={"X-Tenant-ID": test_tenant.id}
    )

    assert response.status_code == 200
    data = response.json()
    items = data["data"]
    assert len(items) == 1
    assert items[0]["reminderType"] == "checkup"

    clear_tenant_context()


@pytest.mark.asyncio
async def test_get_my_health_reminder_unauthorized(async_client, test_tenant):
    """获取我的健康提醒 - 未登录返回401"""
    response = await async_client.get(
        "/api/v1/content/health-reminders/my",
        headers={"X-Tenant-ID": test_tenant.id}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_my_health_reminder_authorized(async_client, db_session, test_tenant, test_user, test_patient):
    """获取我的健康提醒 - 已登录用户"""
    from app.core.security import create_access_token

    set_tenant_context(test_tenant.id, test_tenant.tenant_code)

    # 创建健康提醒配置
    reminder = HealthReminder(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        reminder_type="checkup",
        name="常规体检",
        content="定期体检可以及早发现健康问题",
        recommended_interval=365,
        sort_order=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(reminder)
    await db_session.commit()

    # 创建用户 token
    token = create_access_token({"sub": test_user.id, "type": "access"})

    response = await async_client.get(
        "/api/v1/content/health-reminders/my",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": test_tenant.id
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["hasData"] is True
    assert data["data"]["checkType"] == "checkup"
    assert data["data"]["reminderContent"] is not None

    clear_tenant_context()


@pytest.mark.asyncio
async def test_tenant_isolation(async_client, db_session):
    """租户隔离测试 - 不同租户看到不同数据"""
    # 创建两个租户
    from app.models.tenant import Tenant, SubscriptionPlan

    plan = SubscriptionPlan(
        id=str(uuid4()),
        plan_code="isolation_test_plan",
        name="隔离测试计划",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(plan)
    await db_session.flush()

    tenant1 = Tenant(
        id=str(uuid4()),
        tenant_code="tenant1",
        name="租户1",
        status=1,
        subscription_plan_id=plan.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    tenant2 = Tenant(
        id=str(uuid4()),
        tenant_code="tenant2",
        name="租户2",
        status=1,
        subscription_plan_id=plan.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([tenant1, tenant2])
    await db_session.commit()

    # 为租户1创建服务
    service1 = CommonService(
        id=str(uuid4()),
        tenant_id=tenant1.id,
        name="租户1服务",
        code="tenant1_service",
        icon="star",
        variant="blue",
        link_type=1,
        link_url="/pages/tenant1",
        sort_order=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # 为租户2创建服务
    service2 = CommonService(
        id=str(uuid4()),
        tenant_id=tenant2.id,
        name="租户2服务",
        code="tenant2_service",
        icon="heart",
        variant="red",
        link_type=1,
        link_url="/pages/tenant2",
        sort_order=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([service1, service2])
    await db_session.commit()

    # 租户1 只能看到自己的服务
    set_tenant_context(tenant1.id, tenant1.tenant_code)
    response1 = await async_client.get(
        "/api/v1/content/common-services",
        headers={"X-Tenant-ID": tenant1.id}
    )

    assert response1.status_code == 200
    data1 = response1.json()
    items1 = data1["data"]["items"]
    assert len(items1) == 1
    assert items1[0]["name"] == "租户1服务"

    clear_tenant_context()

    # 租户2 只能看到自己的服务
    set_tenant_context(tenant2.id, tenant2.tenant_code)
    response2 = await async_client.get(
        "/api/v1/content/common-services",
        headers={"X-Tenant-ID": tenant2.id}
    )

    assert response2.status_code == 200
    data2 = response2.json()
    items2 = data2["data"]["items"]
    assert len(items2) == 1
    assert items2[0]["name"] == "租户2服务"

    clear_tenant_context()


@pytest.mark.asyncio
async def test_common_services_with_department(async_client, db_session, test_tenant, test_department):
    """常见服务关联科室"""
    from app.models.department import Department

    set_tenant_context(test_tenant.id, test_tenant.tenant_code)

    # 创建关联科室的服务
    service = CommonService(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        name="内科挂号",
        code="internal_medicine_booking",
        icon="stethoscope",
        variant="blue",
        link_type=3,
        department_id=test_department.id,
        sort_order=1,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(service)
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/content/common-services",
        headers={"X-Tenant-ID": test_tenant.id}
    )

    assert response.status_code == 200
    data = response.json()
    items = data["data"]["items"]
    assert len(items) == 1
    assert items[0]["departmentId"] == test_department.id
    assert items[0]["departmentName"] == test_department.name

    clear_tenant_context()
