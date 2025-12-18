"""add user behavior logs table

Revision ID: 015_add_user_behavior_logs
Revises: 014_add_operation_logs
Create Date: 2024-12-17 15:00:00.000000

Add user_behavior_logs table for user behavior analytics.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '015_add_user_behavior_logs'
down_revision = '014_add_operation_logs'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # 创建用户行为日志表
    if not table_exists('user_behavior_logs'):
        op.create_table(
            'user_behavior_logs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('platform', sa.String(20), nullable=False, comment='平台: admin/h5/miniapp'),
            sa.Column('user_id', sa.String(36), nullable=True, comment='用户ID'),
            sa.Column('session_id', sa.String(64), nullable=True, comment='会话ID'),
            sa.Column('event_type', sa.String(30), nullable=False, comment='事件类型: page_view/page_leave/click/search/custom'),
            sa.Column('page_path', sa.String(255), nullable=True, comment='页面路径'),
            sa.Column('page_title', sa.String(100), nullable=True, comment='页面标题'),
            sa.Column('element_id', sa.String(100), nullable=True, comment='元素ID'),
            sa.Column('element_text', sa.String(200), nullable=True, comment='元素文本'),
            sa.Column('search_keyword', sa.String(200), nullable=True, comment='搜索关键词'),
            sa.Column('event_name', sa.String(100), nullable=True, comment='自定义事件名称'),
            sa.Column('duration', sa.Integer, nullable=True, comment='停留时长(毫秒)'),
            sa.Column('referrer', sa.String(255), nullable=True, comment='来源页面'),
            sa.Column('extra_data', sa.Text, nullable=True, comment='额外数据(JSON)'),
            sa.Column('ip', sa.String(50), nullable=True, comment='IP地址'),
            sa.Column('user_agent', sa.String(500), nullable=True, comment='User-Agent'),
            sa.Column('device_type', sa.String(20), nullable=True, comment='设备类型: desktop/mobile/tablet'),
            sa.Column('browser', sa.String(50), nullable=True, comment='浏览器'),
            sa.Column('os', sa.String(50), nullable=True, comment='操作系统'),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), comment='创建时间'),
        )
        
        # 创建索引
        op.create_index('idx_behavior_logs_platform', 'user_behavior_logs', ['platform'])
        op.create_index('idx_behavior_logs_user_id', 'user_behavior_logs', ['user_id'])
        op.create_index('idx_behavior_logs_session_id', 'user_behavior_logs', ['session_id'])
        op.create_index('idx_behavior_logs_event_type', 'user_behavior_logs', ['event_type'])
        op.create_index('idx_behavior_logs_page_path', 'user_behavior_logs', ['page_path'])
        op.create_index('idx_behavior_logs_created_at', 'user_behavior_logs', ['created_at'])
        # 复合索引：用于统计查询
        op.create_index('idx_behavior_logs_platform_event', 'user_behavior_logs', ['platform', 'event_type'])
        op.create_index('idx_behavior_logs_platform_created', 'user_behavior_logs', ['platform', 'created_at'])


def downgrade() -> None:
    # 删除索引
    try:
        op.drop_index('idx_behavior_logs_platform_created', 'user_behavior_logs')
        op.drop_index('idx_behavior_logs_platform_event', 'user_behavior_logs')
        op.drop_index('idx_behavior_logs_created_at', 'user_behavior_logs')
        op.drop_index('idx_behavior_logs_page_path', 'user_behavior_logs')
        op.drop_index('idx_behavior_logs_event_type', 'user_behavior_logs')
        op.drop_index('idx_behavior_logs_session_id', 'user_behavior_logs')
        op.drop_index('idx_behavior_logs_user_id', 'user_behavior_logs')
        op.drop_index('idx_behavior_logs_platform', 'user_behavior_logs')
    except:
        pass
    
    # 删除表
    if table_exists('user_behavior_logs'):
        op.drop_table('user_behavior_logs')

