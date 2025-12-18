"""add email templates table

Revision ID: 013_add_email_templates
Revises: 012_appt_reminder
Create Date: 2024-12-17 10:00:00.000000

Add email_templates table for email template management.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '013_add_email_templates'
down_revision = '012_appt_reminder'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # 创建邮件模板表
    if not table_exists('email_templates'):
        op.create_table(
            'email_templates',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('code', sa.String(50), unique=True, nullable=False, comment='模板编码'),
            sa.Column('name', sa.String(100), nullable=False, comment='模板名称'),
            sa.Column('template_type', sa.String(30), server_default='custom', comment='模板类型'),
            sa.Column('subject_template', sa.String(200), nullable=False, comment='邮件主题模板'),
            sa.Column('content_template', sa.Text, nullable=False, comment='邮件内容模板(HTML)'),
            sa.Column('description', sa.String(255), nullable=True, comment='模板说明'),
            sa.Column('status', sa.Integer, server_default='1', comment='状态: 0-禁用 1-启用'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        
        # 创建索引
        op.create_index('idx_email_templates_code', 'email_templates', ['code'])
        op.create_index('idx_email_templates_type', 'email_templates', ['template_type'])
        op.create_index('idx_email_templates_status', 'email_templates', ['status'])


def downgrade() -> None:
    # 删除索引
    try:
        op.drop_index('idx_email_templates_status', 'email_templates')
        op.drop_index('idx_email_templates_type', 'email_templates')
        op.drop_index('idx_email_templates_code', 'email_templates')
    except:
        pass
    
    # 删除表
    if table_exists('email_templates'):
        op.drop_table('email_templates')

