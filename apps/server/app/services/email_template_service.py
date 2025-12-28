from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
import uuid

from app.models.email_template import EmailTemplate
from app.schemas.email_template import (
    EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateQuery
)
from app.utils.audit import set_create_audit, set_update_audit


class EmailTemplateService:
    """邮件模板服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, template_id: str) -> Optional[EmailTemplate]:
        """根据ID获取邮件模板"""
        result = await self.db.execute(
            select(EmailTemplate).where(EmailTemplate.id == template_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_code(self, code: str) -> Optional[EmailTemplate]:
        """根据编码获取邮件模板"""
        result = await self.db.execute(
            select(EmailTemplate).where(EmailTemplate.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self, 
        query: EmailTemplateQuery
    ) -> tuple[List[EmailTemplate], int]:
        """获取邮件模板列表"""
        stmt = select(EmailTemplate)
        count_stmt = select(func.count(EmailTemplate.id))
        
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
        """获取所有邮件模板"""
        stmt = select(EmailTemplate)
        if status is not None:
            stmt = stmt.where(EmailTemplate.status == status)
        stmt = stmt.order_by(EmailTemplate.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def create(self, data: EmailTemplateCreate, operator_id: Optional[str] = None) -> EmailTemplate:
        """创建邮件模板"""
        existing = await self.get_by_code(data.code)
        if existing:
            raise ValueError(f"模板编码 {data.code} 已存在")
        
        template = EmailTemplate(
            id=str(uuid.uuid4()),
            code=data.code,
            name=data.name,
            template_type=data.template_type.value,
            subject_template=data.subject_template,
            content_template=data.content_template,
            description=data.description,
            status=data.status
        )
        set_create_audit(template, operator_id)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def update(self, template_id: str, data: EmailTemplateUpdate, operator_id: Optional[str] = None) -> Optional[EmailTemplate]:
        """更新邮件模板"""
        template = await self.get_by_id(template_id)
        if not template:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        # 处理枚举类型
        if 'template_type' in update_data and update_data['template_type']:
            update_data['template_type'] = update_data['template_type'].value
        
        for field, value in update_data.items():
            setattr(template, field, value)
        
        set_update_audit(template, operator_id)
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def delete(self, template_id: str) -> bool:
        """删除邮件模板"""
        template = await self.get_by_id(template_id)
        if not template:
            return False
        
        await self.db.delete(template)
        await self.db.commit()
        return True
    
    def render_template(self, template: EmailTemplate, variables: dict) -> tuple[str, str]:
        """渲染邮件模板"""
        subject = template.subject_template
        content = template.content_template
        
        # 使用双花括号替换变量 {{variable}}
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            subject = subject.replace(placeholder, str(value))
            content = content.replace(placeholder, str(value))
        
        return subject, content

