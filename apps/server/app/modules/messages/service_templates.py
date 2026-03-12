"""Message template service."""

import uuid
from typing import List, Optional

from sqlalchemy import select

from app.models.message import MessageTemplate
from app.schemas.message import MessageTemplateCreate, MessageTemplateUpdate
from app.utils.audit import set_create_audit, set_update_audit


class MessageTemplateService:
    def __init__(self, db):
        self.db = db

    async def get_by_id(self, template_id: str) -> Optional[MessageTemplate]:
        result = await self.db.execute(select(MessageTemplate).where(MessageTemplate.id == template_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[MessageTemplate]:
        result = await self.db.execute(select(MessageTemplate).where(MessageTemplate.code == code))
        return result.scalar_one_or_none()

    async def get_list(self, status: Optional[int] = None) -> List[MessageTemplate]:
        stmt = select(MessageTemplate)
        if status is not None:
            stmt = stmt.where(MessageTemplate.status == status)
        stmt = stmt.order_by(MessageTemplate.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self, data: MessageTemplateCreate, operator_id: Optional[str] = None
    ) -> MessageTemplate:
        existing = await self.get_by_code(data.code)
        if existing:
            raise ValueError(f"模板编码 {data.code} 已存在")

        template = MessageTemplate(id=str(uuid.uuid4()), **data.model_dump())
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
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            title = title.replace(placeholder, str(value))
            content = content.replace(placeholder, str(value))
        return title, content
