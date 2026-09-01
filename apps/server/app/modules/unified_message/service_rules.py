"""统一消息服务 - 规则与模板 CRUD Mixin

包含 4 个 rule CRUD + 4 个 template CRUD 方法。
方法体逐字从原 service.py 搬迁，逻辑/签名不变。
"""
import uuid
from typing import Any

from sqlalchemy import and_, select

from app.modules.unified_message.models import (
    RecipientRule,
    UnifiedTemplate,
)


class UnifiedMessageRulesMixin:
    """统一消息服务 - 规则与模板 CRUD Mixin"""

    async def get_rules(
        self, tenant_id: str, event_type: str | None = None
    ) -> list[RecipientRule]:
        """获取接收人规则列表"""
        stmt = select(RecipientRule).where(RecipientRule.tenant_id == tenant_id)
        if event_type:
            stmt = stmt.where(
                (RecipientRule.event_type == event_type) | (RecipientRule.event_type.is_(None))
            )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_rule(self, tenant_id: str, rule_data: dict[str, Any]) -> RecipientRule:
        """创建接收人规则"""
        rule = RecipientRule(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            **rule_data,
        )
        self.db.add(rule)
        await self.db.commit()
        return rule

    async def update_rule(
        self, rule_id: str, tenant_id: str, rule_data: dict[str, Any]
    ) -> RecipientRule | None:
        """更新接收人规则"""
        rule = await self.db.get(RecipientRule, rule_id)
        if not rule or rule.tenant_id != tenant_id:
            return None

        for key, value in rule_data.items():
            setattr(rule, key, value)

        await self.db.commit()
        return rule

    async def delete_rule(self, rule_id: str, tenant_id: str) -> bool:
        """删除接收人规则"""
        rule = await self.db.get(RecipientRule, rule_id)
        if not rule or rule.tenant_id != tenant_id:
            return False

        await self.db.delete(rule)
        await self.db.commit()
        return True

    # -----------------------------------------------------------------------
    # 模板管理
    # -----------------------------------------------------------------------

    async def get_templates(
        self,
        tenant_id: str,
        message_type: str | None = None,
        status: int | None = None,
    ) -> list[UnifiedTemplate]:
        """获取统一模板列表"""
        stmt = select(UnifiedTemplate).where(UnifiedTemplate.tenant_id == tenant_id)
        if message_type:
            stmt = stmt.where(UnifiedTemplate.message_type == message_type)
        if status is not None:
            stmt = stmt.where(UnifiedTemplate.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_template(
        self, tenant_id: str, template_data: dict[str, Any]
    ) -> UnifiedTemplate:
        """创建统一模板"""
        # 检查 code 唯一性
        existing = await self.db.execute(
            select(UnifiedTemplate.id).where(
                and_(
                    UnifiedTemplate.tenant_id == tenant_id,
                    UnifiedTemplate.code == template_data.get("code"),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"模板编码已存在: {template_data.get('code')}")

        template = UnifiedTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            **template_data,
        )
        self.db.add(template)
        await self.db.commit()
        return template

    async def update_template(
        self, template_id: str, tenant_id: str, template_data: dict[str, Any]
    ) -> UnifiedTemplate | None:
        """更新统一模板"""
        template = await self.db.get(UnifiedTemplate, template_id)
        if not template or template.tenant_id != tenant_id:
            return None

        # 如果更新了 code，检查唯一性
        new_code = template_data.get("code")
        if new_code and new_code != template.code:
            existing = await self.db.execute(
                select(UnifiedTemplate.id).where(
                    and_(
                        UnifiedTemplate.tenant_id == tenant_id,
                        UnifiedTemplate.code == new_code,
                        UnifiedTemplate.id != template_id,
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"模板编码已存在: {new_code}")

        for key, value in template_data.items():
            setattr(template, key, value)

        await self.db.commit()
        return template

    async def delete_template(self, template_id: str, tenant_id: str) -> bool:
        """删除统一模板"""
        template = await self.db.get(UnifiedTemplate, template_id)
        if not template or template.tenant_id != tenant_id:
            return False

        await self.db.delete(template)
        await self.db.commit()
        return True
