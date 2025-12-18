"""add operation logs table

Revision ID: 014_add_operation_logs
Revises: 013_add_email_templates
Create Date: 2024-12-17 14:00:00.000000

Add operation_logs table for admin operation audit logging.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '014_add_operation_logs'
down_revision = '013_add_email_templates'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # 创建操作日志表
    if not table_exists('operation_logs'):
        op.create_table(
            'operation_logs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('admin_id', sa.String(36), sa.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True, comment='操作人ID'),
            sa.Column('admin_name', sa.String(50), nullable=True, comment='操作人姓名'),
            sa.Column('module', sa.String(50), nullable=True, comment='模块'),
            sa.Column('action', sa.String(100), nullable=True, comment='操作'),
            sa.Column('method', sa.String(10), nullable=True, comment='请求方法'),
            sa.Column('path', sa.String(255), nullable=True, comment='请求路径'),
            sa.Column('params', sa.Text, nullable=True, comment='请求参数'),
            sa.Column('result', sa.String(20), nullable=True, comment='结果'),
            sa.Column('ip', sa.String(50), nullable=True, comment='IP地址'),
            sa.Column('user_agent', sa.String(500), nullable=True, comment='User-Agent'),
            sa.Column('duration', sa.Integer, nullable=True, comment='耗时(毫秒)'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), comment='创建时间'),
        )
        
        # 创建索引
        op.create_index('idx_operation_logs_admin_id', 'operation_logs', ['admin_id'])
        op.create_index('idx_operation_logs_module', 'operation_logs', ['module'])
        op.create_index('idx_operation_logs_created_at', 'operation_logs', ['created_at'])


def downgrade() -> None:
    # 删除索引
    try:
        op.drop_index('idx_operation_logs_created_at', 'operation_logs')
        op.drop_index('idx_operation_logs_module', 'operation_logs')
        op.drop_index('idx_operation_logs_admin_id', 'operation_logs')
    except:
        pass
    
    # 删除表
    if table_exists('operation_logs'):
        op.drop_table('operation_logs')

