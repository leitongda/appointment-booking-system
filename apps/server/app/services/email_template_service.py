from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List
import uuid

from app.models.email_template import EmailTemplate
from app.schemas.email_template import (
    EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateQuery
)
from app.middleware.tenant_context import get_current_tenant_id
from app.utils.audit import set_create_audit, set_update_audit


class EmailTemplateService:

    def __init__(self, db: AsyncSession):
        self.db = db

    def _tenant_filter(self, stmt, model_alias=None):
        tenant_id = get_current_tenant_id()
        target = model_alias or EmailTemplate
        if tenant_id:
            stmt = stmt.where(or_(target.tenant_id == tenant_id, target.tenant_id.is_(None)))
        return stmt

    async def get_by_id(self, template_id: str) -> Optional[EmailTemplate]:
        stmt = select(EmailTemplate).where(EmailTemplate.id == template_id)
        stmt = self._tenant_filter(stmt)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[EmailTemplate]:
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = select(EmailTemplate).where(
                EmailTemplate.code == code,
                EmailTemplate.tenant_id == tenant_id,
            )
            result = await self.db.execute(stmt)
            template = result.scalar_one_or_none()
            if template:
                return template
            stmt = select(EmailTemplate).where(
                EmailTemplate.code == code,
                EmailTemplate.tenant_id.is_(None),
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        result = await self.db.execute(
            select(EmailTemplate).where(EmailTemplate.code == code)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        query: EmailTemplateQuery
    ) -> tuple[List[EmailTemplate], int]:
        stmt = select(EmailTemplate)
        count_stmt = select(func.count(EmailTemplate.id))

        stmt = self._tenant_filter(stmt)
        count_stmt = self._tenant_filter(count_stmt)

        if query.template_type:
            stmt = stmt.where(EmailTemplate.template_type == query.template_type.value)
            count_stmt = count_stmt.where(EmailTemplate.template_type == query.template_type.value)

        if query.status is not None:
            stmt = stmt.where(EmailTemplate.status == query.status)
            count_stmt = count_stmt.where(EmailTemplate.status == query.status)

        if query.keyword:
            keyword_filter = (
                EmailTemplate.name.contains(query.keyword) |
                EmailTemplate.code.contains(query.keyword) |
                EmailTemplate.description.contains(query.keyword)
            )
            stmt = stmt.where(keyword_filter)
            count_stmt = count_stmt.where(keyword_filter)

        stmt = stmt.order_by(EmailTemplate.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def get_all(self, status: Optional[int] = None) -> List[EmailTemplate]:
        stmt = select(EmailTemplate)
        stmt = self._tenant_filter(stmt)
        if status is not None:
            stmt = stmt.where(EmailTemplate.status == status)
        stmt = stmt.order_by(EmailTemplate.created_at.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: EmailTemplateCreate, operator_id: Optional[str] = None) -> EmailTemplate:
        tenant_id = get_current_tenant_id()

        if tenant_id:
            existing = await self.db.execute(
                select(EmailTemplate).where(
                    EmailTemplate.code == data.code,
                    EmailTemplate.tenant_id == tenant_id,
                )
            )
        else:
            existing = await self.db.execute(
                select(EmailTemplate).where(
                    EmailTemplate.code == data.code,
                    EmailTemplate.tenant_id.is_(None),
                )
            )
        if existing.scalar_one_or_none():
            raise ValueError(f"模板编码 {data.code} 已存在")

        template = EmailTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            code=data.code,
            name=data.name,
            template_type=data.template_type.value,
            subject_template=data.subject_template,
            content_template=data.content_template,
            description=data.description,
            status=data.status,
        )
        set_create_audit(template, operator_id)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update(self, template_id: str, data: EmailTemplateUpdate, operator_id: Optional[str] = None) -> Optional[EmailTemplate]:
        template = await self.get_by_id(template_id)
        if not template:
            return None

        update_data = data.model_dump(exclude_unset=True)

        if 'template_type' in update_data and update_data['template_type']:
            update_data['template_type'] = update_data['template_type'].value

        for field, value in update_data.items():
            setattr(template, field, value)

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

    def render_template(self, template: EmailTemplate, variables: dict) -> tuple[str, str]:
        from app.utils.email_sync import render_email_template
        subject = render_email_template(template.subject_template, variables)
        content = render_email_template(template.content_template, variables)
        return subject, content
