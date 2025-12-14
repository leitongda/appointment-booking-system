"""add patient management fields and point logs

Revision ID: 006
Revises: 005_add_doctor_booking_settings
Create Date: 2024-12-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_patient_management'
down_revision = '005_add_doctor_booking_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 扩展 patients 表 - 添加新字段
    op.add_column('patients', sa.Column('card_no', sa.String(50), nullable=True, comment='就诊卡编号'))
    op.add_column('patients', sa.Column('province', sa.String(50), nullable=True, comment='省'))
    op.add_column('patients', sa.Column('city', sa.String(50), nullable=True, comment='市'))
    op.add_column('patients', sa.Column('district', sa.String(50), nullable=True, comment='区'))
    op.add_column('patients', sa.Column('street', sa.String(100), nullable=True, comment='街道/社区'))
    op.add_column('patients', sa.Column('id_card_type', sa.Integer, server_default='1', comment='证件类型: 1身份证 2户口簿 3护照'))
    op.add_column('patients', sa.Column('ethnicity', sa.String(20), server_default='汉族', comment='民族'))
    op.add_column('patients', sa.Column('address', sa.String(255), nullable=True, comment='详细地址'))
    op.add_column('patients', sa.Column('source', sa.Integer, server_default='1', comment='来源: 1用户添加 2管理员添加'))
    op.add_column('patients', sa.Column('total_consumption', sa.Numeric(10, 2), server_default='0', comment='累计消费'))
    
    # 创建就诊卡编号唯一索引
    op.create_index('ix_patients_card_no', 'patients', ['card_no'], unique=True)
    
    # 扩展 users 表 - 添加积分字段
    op.add_column('users', sa.Column('points', sa.Integer, server_default='0', comment='当前积分'))
    
    # 创建积分流水表
    op.create_table(
        'point_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False, comment='用户ID'),
        sa.Column('change_amount', sa.Integer, nullable=False, comment='变更积分（正增负减）'),
        sa.Column('balance', sa.Integer, nullable=False, comment='变更后余额'),
        sa.Column('type', sa.Integer, server_default='4', comment='类型: 1消费 2充值 3赠送 4手动调整'),
        sa.Column('remark', sa.String(255), nullable=True, comment='备注'),
        sa.Column('operator_id', sa.String(36), nullable=True, comment='操作人ID'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_point_logs_user_id', 'point_logs', ['user_id'])


def downgrade() -> None:
    # 删除积分流水表
    op.drop_index('ix_point_logs_user_id', 'point_logs')
    op.drop_table('point_logs')
    
    # 删除 users 表的积分字段
    op.drop_column('users', 'points')
    
    # 删除 patients 表的索引
    op.drop_index('ix_patients_card_no', 'patients')
    
    # 删除 patients 表的新字段
    op.drop_column('patients', 'total_consumption')
    op.drop_column('patients', 'source')
    op.drop_column('patients', 'address')
    op.drop_column('patients', 'ethnicity')
    op.drop_column('patients', 'id_card_type')
    op.drop_column('patients', 'street')
    op.drop_column('patients', 'district')
    op.drop_column('patients', 'city')
    op.drop_column('patients', 'province')
    op.drop_column('patients', 'card_no')
