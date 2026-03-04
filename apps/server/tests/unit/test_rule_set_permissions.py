"""
规则组权限测试

测试规则组 API 的权限控制：
- 超级管理员可以执行所有操作
- 普通管理员只能查看，不能修改
"""
import pytest
from fastapi import status
from httpx import AsyncClient

from app.models.rule_set import RuleSet, ShiftType


@pytest.mark.asyncio
class TestRuleSetPermissions:
    """规则组权限测试"""

    async def test_list_rule_sets_as_store_admin(
        self, async_client: AsyncClient, store_admin_token: str
    ):
        """门店管理员查看规则组列表 - 应该成功"""
        response = await async_client.get(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {store_admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_list_rule_sets_as_super_admin(
        self, async_client: AsyncClient, super_admin_token: str
    ):
        """超级管理员查看规则组列表 - 应该成功"""
        response = await async_client.get(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_get_rule_set_detail_as_store_admin(
        self, async_client: AsyncClient, store_admin_token: str
    ):
        """门店管理员查看规则组详情 - 应该成功"""
        # 使用列表查询中的第一个规则组
        list_response = await async_client.get(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {store_admin_token}"}
        )
        assert list_response.status_code == status.HTTP_200_OK
        rule_sets = list_response.json()["data"]["items"]
        if rule_sets:
            rule_set_id = rule_sets[0]["id"]
            response = await async_client.get(
                f"/api/v1/rule-sets/{rule_set_id}",
                headers={"Authorization": f"Bearer {store_admin_token}"}
            )
            assert response.status_code == status.HTTP_200_OK

    async def test_update_rule_set_as_store_admin_forbidden(
        self, async_client: AsyncClient, store_admin_token: str, test_shift_type: ShiftType
    ):
        """门店管理员更新规则组 - 应该被禁止"""
        # 先创建一个规则组
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {store_admin_token}"},
            json={
                "name": "待更新的规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": True,
            }
        )
        # 应该被禁止
        assert create_response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_rule_set_as_super_admin(
        self, async_client: AsyncClient, super_admin_token: str, test_shift_type: ShiftType
    ):
        """超级管理员更新规则组 - 应该成功"""
        # 先创建一个规则组
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "name": "待更新的规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": True,
            }
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        rule_set_id = create_response.json()["data"]["id"]

        # 更新规则组
        response = await async_client.put(
            f"/api/v1/rule-sets/{rule_set_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "name": "更新的规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": True,
            }
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_delete_rule_set_as_store_admin_forbidden(
        self, async_client: AsyncClient, store_admin_token: str, test_shift_type: ShiftType
    ):
        """门店管理员删除规则组 - 应该被禁止"""
        # 先创建一个规则组
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {store_admin_token}"},
            json={
                "name": "待删除的规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": False,
            }
        )
        # 应该被禁止
        assert create_response.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_rule_set_as_super_admin(
        self, async_client: AsyncClient, super_admin_token: str, test_shift_type: ShiftType
    ):
        """超级管理员删除规则组 - 应该成功"""
        # 先创建一个测试规则组用于删除
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "name": "待删除的规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": False,
            }
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        rule_set_id = create_response.json()["data"]["id"]

        # 删除规则组 - 返回 204 No Content
        response = await async_client.delete(
            f"/api/v1/rule-sets/{rule_set_id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_enable_rule_set_as_store_admin_forbidden(
        self, async_client: AsyncClient, store_admin_token: str, test_shift_type: ShiftType
    ):
        """门店管理员启用规则组 - 应该被禁止"""
        # 先创建一个规则组
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {store_admin_token}"},
            json={
                "name": "待启用的规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": False,
            }
        )
        # 应该被禁止
        assert create_response.status_code == status.HTTP_403_FORBIDDEN

    async def test_enable_rule_set_as_super_admin(
        self, async_client: AsyncClient, super_admin_token: str, test_shift_type: ShiftType
    ):
        """超级管理员启用规则组 - 应该成功"""
        # 先创建一个规则组
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "name": "待启用的规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": False,
            }
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        rule_set_id = create_response.json()["data"]["id"]

        # 启用规则组
        response = await async_client.post(
            f"/api/v1/rule-sets/{rule_set_id}/enable",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_disable_rule_set_as_store_admin_forbidden(
        self, async_client: AsyncClient, store_admin_token: str, test_shift_type: ShiftType
    ):
        """门店管理员禁用规则组 - 应该被禁止"""
        # 先创建一个规则组
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {store_admin_token}"},
            json={
                "name": "待禁用的规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": True,
            }
        )
        # 应该被禁止
        assert create_response.status_code == status.HTTP_403_FORBIDDEN

    async def test_disable_rule_set_as_super_admin(
        self, async_client: AsyncClient, super_admin_token: str, test_shift_type: ShiftType
    ):
        """超级管理员禁用规则组 - 应该成功"""
        # 先创建一个规则组
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "name": "待禁用的规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": True,
            }
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        rule_set_id = create_response.json()["data"]["id"]

        # 禁用规则组
        response = await async_client.post(
            f"/api/v1/rule-sets/{rule_set_id}/disable",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_create_window_as_store_admin_forbidden(
        self, async_client: AsyncClient, store_admin_token: str, test_shift_type: ShiftType
    ):
        """门店管理员创建时间窗 - 应该被禁止"""
        # 先创建一个规则组
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {store_admin_token}"},
            json={
                "name": "测试规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": True,
            }
        )
        # 应该被禁止
        assert create_response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_booking_policy_as_store_admin_forbidden(
        self, async_client: AsyncClient, store_admin_token: str, test_shift_type: ShiftType
    ):
        """门店管理员更新预约策略 - 应该被禁止"""
        # 先创建一个规则组
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {store_admin_token}"},
            json={
                "name": "测试规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": True,
            }
        )
        # 应该被禁止
        assert create_response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_checkin_policy_as_store_admin_forbidden(
        self, async_client: AsyncClient, store_admin_token: str, test_shift_type: ShiftType
    ):
        """门店管理员更新签到策略 - 应该被禁止"""
        # 先创建一个规则组
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {store_admin_token}"},
            json={
                "name": "测试规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": True,
            }
        )
        # 应该被禁止
        assert create_response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_capacity_policy_as_store_admin_forbidden(
        self, async_client: AsyncClient, store_admin_token: str, test_shift_type: ShiftType
    ):
        """门店管理员更新容量策略 - 应该被禁止"""
        # 先创建一个规则组
        create_response = await async_client.post(
            "/api/v1/rule-sets",
            headers={"Authorization": f"Bearer {store_admin_token}"},
            json={
                "name": "测试规则组",
                "priority": 100,
                "shiftTypeIds": [test_shift_type.id],
                "enabled": True,
            }
        )
        # 应该被禁止
        assert create_response.status_code == status.HTTP_403_FORBIDDEN

    async def test_unauthorized_access_without_token(
        self, async_client: AsyncClient
    ):
        """未授权访问 - 没有提供 token"""
        response = await async_client.get("/api/v1/rule-sets")
        # 应该返回 401 Unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_invalid_token(
        self, async_client: AsyncClient
    ):
        """无效的 token"""
        response = await async_client.get(
            "/api/v1/rule-sets",
            headers={"Authorization": "Bearer invalid_token"}
        )
        # 应该返回 401 Unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
