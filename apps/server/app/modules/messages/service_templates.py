"""Message template service."""

import uuid
import logging
from typing import List, Optional

from sqlalchemy import select, or_
from jinja2 import Environment, BaseLoader, TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment

from app.models.message import MessageTemplate
from app.middleware.tenant_context import get_current_tenant_id
from app.schemas.message import MessageTemplateCreate, MessageTemplateUpdate
from app.utils.audit import set_create_audit, set_update_audit

logger = logging.getLogger(__name__)


class MessageTemplateService:
    def __init__(self, db):
        self.db = db
        self.env = SandboxedEnvironment(loader=BaseLoader())

    def _tenant_filter(self, stmt):
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(or_(MessageTemplate.tenant_id == tenant_id, MessageTemplate.tenant_id.is_(None)))
        return stmt

    async def get_by_id(self, template_id: str) -> Optional[MessageTemplate]:
        stmt = select(MessageTemplate).where(MessageTemplate.id == template_id)
        stmt = self._tenant_filter(stmt)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[MessageTemplate]:
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = select(MessageTemplate).where(
                MessageTemplate.code == code,
                MessageTemplate.tenant_id == tenant_id,
            )
            result = await self.db.execute(stmt)
            template = result.scalar_one_or_none()
            if template:
                return template
            stmt = select(MessageTemplate).where(
                MessageTemplate.code == code,
                MessageTemplate.tenant_id.is_(None),
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        result = await self.db.execute(
            select(MessageTemplate).where(MessageTemplate.code == code)
        )
        return result.scalar_one_or_none()

    async def get_list(self, status: Optional[int] = None) -> List[MessageTemplate]:
        stmt = select(MessageTemplate)
        stmt = self._tenant_filter(stmt)
        if status is not None:
            stmt = stmt.where(MessageTemplate.status == status)
        stmt = stmt.order_by(MessageTemplate.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self, data: MessageTemplateCreate, operator_id: Optional[str] = None
    ) -> MessageTemplate:
        tenant_id = get_current_tenant_id()

        if tenant_id:
            existing_stmt = select(MessageTemplate).where(
                MessageTemplate.code == data.code,
                MessageTemplate.tenant_id == tenant_id,
            )
        else:
            existing_stmt = select(MessageTemplate).where(
                MessageTemplate.code == data.code,
                MessageTemplate.tenant_id.is_(None),
            )
        result = await self.db.execute(existing_stmt)
        if result.scalar_one_or_none():
            raise ValueError(f"模板编码 {data.code} 已存在")

        template = MessageTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            **data.model_dump(),
        )
        set_create_audit(template, operator_id)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update(
        self, template_id: str, data: MessageTemplateUpdate, operator_id: Optional[str] = None
    ) -> Optional[MessageTemplate]:
        template = await self.get_by_id(template_id)
        if not template:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(template, key):
                setattr(template, key, value)

        set_update_audit(template, operator_id)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete(self, template_id: str) -> bool:
        template = await self.get_by_id(template_id)
        if not template:
            return False
        await self.db.delete(template)
        await self.db.commit()
        return True

    def render_template(self, template: MessageTemplate, variables: dict) -> tuple[str, str]:
        title = template.title_template
        content = template.content_template

        try:
            title_tmpl = self.env.from_string(title)
            content_tmpl = self.env.from_string(content)
            rendered_title = title_tmpl.render(**variables)
            rendered_content = content_tmpl.render(**variables)

            # 如果渲染后仍包含单花括号占位符，执行简单替换（向后兼容）
            if "{" in rendered_title or "{" in rendered_content:
                for key, value in variables.items():
                    placeholder = f"{{{key}}}"
                    rendered_title = rendered_title.replace(placeholder, str(value))
                    rendered_content = rendered_content.replace(placeholder, str(value))

            return rendered_title, rendered_content
        except TemplateSyntaxError as e:
            logger.debug(f"模板语法错误，回退到简单替换: {e}")
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                title = title.replace(placeholder, str(value))
                content = content.replace(placeholder, str(value))
            return title, content
        except Exception as e:
            logger.warning(f"模板渲染失败: {e}")
            return title, content
