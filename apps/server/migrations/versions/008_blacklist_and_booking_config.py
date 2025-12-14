"""add blacklist table and booking config settings

Revision ID: 008
Revises: 007_schedule_management
Create Date: 2024-12-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = '008_blacklist_and_booking_config'
down_revision = '007_schedule_management'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建黑名单表
    op.create_table(
        'blacklists',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True, comment='用户ID，可选'),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=True, comment='门店ID，可选'),
        sa.Column('keyword', sa.String(50), nullable=True, comment='手机号或身份证关键词'),
        sa.Column('reason', sa.String(500), nullable=True, comment='黑名单原因/备注'),
        sa.Column('no_show_count', sa.Integer, server_default='0', comment='爽约次数（自动触发时记录）'),
        sa.Column('source', sa.Integer, server_default='1', comment='来源: 1手动添加 2自动触发'),
        sa.Column('expire_at', sa.DateTime, nullable=True, comment='解禁时间'),
        sa.Column('released_at', sa.DateTime, nullable=True, comment='实际解禁时间'),
        sa.Column('status', sa.Integer, server_default='1', comment='状态: 1生效 0已解禁'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_blacklists_user_id', 'blacklists', ['user_id'])
    op.create_index('ix_blacklists_store_id', 'blacklists', ['store_id'])
    op.create_index('ix_blacklists_keyword', 'blacklists', ['keyword'])
    op.create_index('ix_blacklists_status', 'blacklists', ['status'])
    
    # 初始化预约选项配置数据
    settings_table = sa.table(
        'system_settings',
        sa.column('id', sa.String),
        sa.column('category', sa.String),
        sa.column('key', sa.String),
        sa.column('value', sa.Text),
        sa.column('description', sa.String),
    )
    
    # 预约选项配置
    booking_fields = [
        ('name', '{"enabled": true, "required": true}', '姓名'),
        ('phone', '{"enabled": true, "required": true}', '联系电话'),
        ('gender', '{"enabled": true, "required": true}', '性别'),
        ('province_city_district', '{"enabled": false, "required": false}', '省/市/区'),
        ('street', '{"enabled": false, "required": false}', '街道/社区'),
        ('card_no', '{"enabled": false, "required": false}', '就诊卡编号'),
        ('id_card_type', '{"enabled": false, "required": false}', '证件类型'),
        ('id_card', '{"enabled": false, "required": false}', '证件号'),
        ('ethnicity', '{"enabled": false, "required": false}', '民族'),
        ('birthday', '{"enabled": false, "required": false}', '出生日期'),
        ('age', '{"enabled": true, "required": true}', '年龄'),
        ('relationship', '{"enabled": false, "required": false}', '关系'),
        ('address', '{"enabled": false, "required": false}', '详细地址'),
    ]
    
    for key, value, description in booking_fields:
        op.execute(
            settings_table.insert().values(
                id=str(uuid.uuid4()),
                category='booking_fields',
                key=key,
                value=value,
                description=description,
            )
        )
    
    # 就诊卡配置
    patient_card_settings = [
        ('card_name', '就诊卡', '就诊卡名称'),
        ('card_description', '', '就诊卡描述文字（限16字以内）'),
        ('max_cards_per_user', '5', '每用户可建卡数量'),
        ('show_on_homepage', 'false', '首页是否展示'),
    ]
    
    for key, value, description in patient_card_settings:
        op.execute(
            settings_table.insert().values(
                id=str(uuid.uuid4()),
                category='patient_card',
                key=key,
                value=value,
                description=description,
            )
        )


def downgrade() -> None:
    # 删除黑名单表
    op.drop_index('ix_blacklists_status', 'blacklists')
    op.drop_index('ix_blacklists_keyword', 'blacklists')
    op.drop_index('ix_blacklists_store_id', 'blacklists')
    op.drop_index('ix_blacklists_user_id', 'blacklists')
    op.drop_table('blacklists')
    
    # 删除预约选项配置
    op.execute("DELETE FROM system_settings WHERE category = 'booking_fields'")
    
    # 删除就诊卡配置
    op.execute("DELETE FROM system_settings WHERE category = 'patient_card'")
