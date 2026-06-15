"""接收人规则引擎

根据 RecipientRule 配置动态确定通知接收人。
支持的规则类型：
- role: 基于角色（如所有医生、所有护士）
- department: 基于科室/部门
- user_list: 固定用户列表
- dynamic: 动态查询（基于条件）
- event_driven: 事件驱动（从事件数据中提取接收人）
"""
import logging
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.unified_message.models import RecipientRule

logger = logging.getLogger(__name__)


class RecipientRuleEngine:
    """接收人规则引擎"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_recipients(
        self,
        tenant_id: str,
        event_type: str,
        event_data: dict[str, Any],
    ) -> list[dict[str, str]]:
        """解析接收人

        Args:
            tenant_id: 租户ID
            event_type: 事件类型
            event_data: 事件数据（用于动态规则和事件驱动规则）

        Returns:
            接收人列表，每个元素包含 user_id 和 user_type
        """
        # 查询匹配的规则
        rules = await self._get_matching_rules(tenant_id, event_type)

        if not rules:
            logger.debug(f"[接收人规则] 无匹配规则: tenant={tenant_id}, event={event_type}")
            return []

        # 解析所有规则并合并结果
        all_recipients = []
        for rule in rules:
            try:
                recipients = await self._resolve_rule(rule, event_data)
                all_recipients.extend(recipients)
            except Exception as e:
                logger.error(f"[接收人规则] 规则解析失败: rule={rule.id}, error={e}", exc_info=True)

        # 去重（基于 user_id + user_type）
        seen = set()
        unique_recipients = []
        for r in all_recipients:
            key = (r["user_id"], r["user_type"])
            if key not in seen:
                seen.add(key)
                unique_recipients.append(r)

        return unique_recipients

    async def _get_matching_rules(
        self, tenant_id: str, event_type: str
    ) -> list[RecipientRule]:
        """获取匹配的规则"""
        stmt = (
            select(RecipientRule)
            .where(
                and_(
                    RecipientRule.tenant_id == tenant_id,
                    RecipientRule.status == 1,
                    # 匹配绑定了该事件类型的规则，或者未绑定事件类型的通用规则
                    (RecipientRule.event_type == event_type) | (RecipientRule.event_type.is_(None)),
                )
            )
            .order_by(RecipientRule.event_type.desc())  # 具体规则优先
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _resolve_rule(
        self, rule: RecipientRule, event_data: dict[str, Any]
    ) -> list[dict[str, str]]:
        """解析单个规则"""
        rule_type = rule.rule_type
        config = rule.rule_config or {}

        if rule_type == "role":
            return await self._resolve_role_rule(config)
        elif rule_type == "department":
            return await self._resolve_department_rule(config)
        elif rule_type == "user_list":
            return self._resolve_user_list_rule(config)
        elif rule_type == "dynamic":
            return await self._resolve_dynamic_rule(config, event_data)
        elif rule_type == "event_driven":
            return self._resolve_event_driven_rule(config, event_data)
        else:
            logger.warning(f"[接收人规则] 未知规则类型: {rule_type}")
            return []

    async def _resolve_role_rule(self, config: dict[str, Any]) -> list[dict[str, str]]:
        """基于角色的规则

        config 格式:
        {
            "role": "doctor" | "nurse" | "admin",
            "store_id": "..." (可选，限定门店)
        }
        """
        role = config.get("role")
        store_id = config.get("store_id")

        if not role:
            return []

        # 查询用户表（根据角色）
        # 这里需要根据实际的用户表结构来实现
        # 示例：查询医生角色的用户
        if role == "doctor":
            from app.models.doctor import Doctor
            stmt = select(Doctor.id, Doctor.tenant_id)
            if store_id:
                stmt = stmt.where(Doctor.store_id == store_id)
            result = await self.db.execute(stmt)
            return [
                {"user_id": str(row[0]), "user_type": "doctor"}
                for row in result.fetchall()
            ]
        elif role == "patient":
            # 通常不向所有患者发送通知
            return []
        else:
            logger.warning(f"[接收人规则] 未实现的角色: {role}")
            return []

    async def _resolve_department_rule(self, config: dict[str, Any]) -> list[dict[str, str]]:
        """基于科室的规则

        config 格式:
        {
            "department_id": "...",
            "user_type": "doctor" | "nurse"
        }
        """
        department_id = config.get("department_id")
        user_type = config.get("user_type", "doctor")

        if not department_id:
            return []

        # 查询科室下的用户
        if user_type == "doctor":
            from app.models.doctor import Doctor
            stmt = select(Doctor.id).where(Doctor.department_id == department_id)
            result = await self.db.execute(stmt)
            return [
                {"user_id": str(row[0]), "user_type": "doctor"}
                for row in result.fetchall()
            ]
        else:
            logger.warning(f"[接收人规则] 未实现的用户类型: {user_type}")
            return []

    def _resolve_user_list_rule(self, config: dict[str, Any]) -> list[dict[str, str]]:
        """固定用户列表规则

        config 格式:
        {
            "users": [
                {"user_id": "...", "user_type": "doctor"},
                {"user_id": "...", "user_type": "patient"}
            ]
        }
        """
        users = config.get("users", [])
        return [
            {"user_id": u["user_id"], "user_type": u["user_type"]}
            for u in users
            if "user_id" in u and "user_type" in u
        ]

    async def _resolve_dynamic_rule(
        self, config: dict[str, Any], event_data: dict[str, Any]
    ) -> list[dict[str, str]]:
        """动态查询规则

        config 格式:
        {
            "query_type": "appointment_doctor" | "schedule_doctor" | ...,
            "params": {
                "field_mapping": {
                    "event_field": "query_param"
                }
            }
        }
        """
        query_type = config.get("query_type")
        params_config = config.get("params", {})
        field_mapping = params_config.get("field_mapping", {})

        if not query_type:
            return []

        # 从 event_data 中提取查询参数
        query_params = {}
        for event_field, query_param in field_mapping.items():
            if event_field in event_data:
                query_params[query_param] = event_data[event_field]

        # 根据查询类型执行不同的查询
        if query_type == "appointment_doctor":
            return await self._query_appointment_doctor(query_params)
        elif query_type == "schedule_doctor":
            return await self._query_schedule_doctor(query_params)
        else:
            logger.warning(f"[接收人规则] 未实现的查询类型: {query_type}")
            return []

    async def _query_appointment_doctor(self, params: dict[str, Any]) -> list[dict[str, str]]:
        """查询预约相关的医生"""
        appointment_id = params.get("appointment_id")
        if not appointment_id:
            return []

        from app.models.appointment import Appointment
        stmt = select(Appointment.doctor_id).where(Appointment.id == appointment_id)
        result = await self.db.execute(stmt)
        doctor_id = result.scalar_one_or_none()

        if doctor_id:
            return [{"user_id": str(doctor_id), "user_type": "doctor"}]
        return []

    async def _query_schedule_doctor(self, params: dict[str, Any]) -> list[dict[str, str]]:
        """查询排班相关的医生"""
        schedule_id = params.get("schedule_id")
        if not schedule_id:
            return []

        from app.models.schedule import Schedule
        stmt = select(Schedule.doctor_id).where(Schedule.id == schedule_id)
        result = await self.db.execute(stmt)
        doctor_id = result.scalar_one_or_none()

        if doctor_id:
            return [{"user_id": str(doctor_id), "user_type": "doctor"}]
        return []

    def _resolve_event_driven_rule(
        self, config: dict[str, Any], event_data: dict[str, Any]
    ) -> list[dict[str, str]]:
        """事件驱动规则

        config 格式:
        {
            "recipient_field": "doctor_id" | "patient_id" | ...,
            "user_type_field": "user_type" | "fixed_user_type",
            "fixed_user_type": "doctor" (可选，固定用户类型)
        }
        """
        recipient_field = config.get("recipient_field")
        if not recipient_field:
            return []

        user_id = event_data.get(recipient_field)
        if not user_id:
            return []

        # 获取用户类型
        if "fixed_user_type" in config:
            user_type = config["fixed_user_type"]
        elif "user_type_field" in config:
            user_type = event_data.get(config["user_type_field"], "patient")
        else:
            user_type = "patient"

        return [{"user_id": str(user_id), "user_type": user_type}]