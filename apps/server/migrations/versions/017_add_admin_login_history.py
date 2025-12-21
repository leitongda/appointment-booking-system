"""添加管理员登录历史表

Revision ID: 017_add_admin_login_history
Revises: 016_multi_tenant
Create Date: 2024-12-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '017_add_admin_login_history'
down_revision = '016_multi_tenant'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建管理员登录历史表
    op.create_table(
        'admin_login_history',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('admin_id', sa.String(36), sa.ForeignKey('admins.id'), nullable=False, comment='管理员ID'),
        sa.Column('login_time', sa.DateTime, nullable=False, comment='登录时间'),
        sa.Column('logout_time', sa.DateTime, nullable=True, comment='退出时间'),
        sa.Column('logout_type', sa.String(20), nullable=True, comment='退出类型: manual/timeout/kicked'),
        sa.Column('login_ip', sa.String(50), comment='登录IP'),
        sa.Column('user_agent', sa.String(500), comment='User-Agent字符串'),
        sa.Column('browser', sa.String(50), comment='浏览器'),
        sa.Column('os', sa.String(50), comment='操作系统'),
        sa.Column('device_type', sa.String(20), comment='设备类型: desktop/mobile/tablet'),
        sa.Column('duration', sa.Integer, nullable=True, comment='在线时长（秒）'),
    )
    
    # 创建索引
    op.create_index('ix_admin_login_history_admin_id', 'admin_login_history', ['admin_id'])
    op.create_index('ix_admin_login_history_login_time', 'admin_login_history', ['login_time'])


def downgrade() -> None:
    op.drop_index('ix_admin_login_history_login_time', 'admin_login_history')
    op.drop_index('ix_admin_login_history_admin_id', 'admin_login_history')
    op.drop_table('admin_login_history')

