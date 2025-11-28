"""add new tables for store, message, leave_request, feedback

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_add_new_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 门店表
    op.create_table(
        'stores',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, comment='门店名称'),
        sa.Column('code', sa.String(50), unique=True, comment='门店编码'),
        sa.Column('address', sa.String(255), comment='地址'),
        sa.Column('phone', sa.String(20), comment='联系电话'),
        sa.Column('business_hours', sa.String(100), comment='营业时间'),
        sa.Column('description', sa.Text, comment='门店介绍'),
        sa.Column('status', sa.Integer, default=1, comment='状态: 0-停业 1-营业'),
        sa.Column('sort_order', sa.Integer, default=0, comment='排序'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # 门店-科室关联表
    op.create_table(
        'store_departments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('store_id', sa.String(36), nullable=False, comment='门店ID'),
        sa.Column('department_id', sa.String(36), nullable=False, comment='科室ID'),
        sa.Column('floor', sa.String(20), comment='楼层'),
        sa.Column('room', sa.String(50), comment='诊室'),
        sa.Column('status', sa.Integer, default=1, comment='状态'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_store_departments_store_id', 'store_departments', ['store_id'])
    op.create_index('ix_store_departments_department_id', 'store_departments', ['department_id'])
    
    # 消息表
    op.create_table(
        'messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False, comment='接收用户ID'),
        sa.Column('user_type', sa.String(20), nullable=False, comment='用户类型'),
        sa.Column('title', sa.String(200), nullable=False, comment='消息标题'),
        sa.Column('content', sa.Text, comment='消息内容'),
        sa.Column('message_type', sa.String(20), default='system', comment='消息类型'),
        sa.Column('related_id', sa.String(36), comment='关联业务ID'),
        sa.Column('is_read', sa.Integer, default=0, comment='是否已读'),
        sa.Column('read_at', sa.DateTime, comment='阅读时间'),
        sa.Column('extra_data', sa.Text, comment='额外数据'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_messages_user_id', 'messages', ['user_id'])
    
    # 消息模板表
    op.create_table(
        'message_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False, comment='模板编码'),
        sa.Column('name', sa.String(100), nullable=False, comment='模板名称'),
        sa.Column('message_type', sa.String(20), nullable=False, comment='消息类型'),
        sa.Column('title_template', sa.String(200), nullable=False, comment='标题模板'),
        sa.Column('content_template', sa.Text, nullable=False, comment='内容模板'),
        sa.Column('description', sa.String(255), comment='模板说明'),
        sa.Column('status', sa.Integer, default=1, comment='状态'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # 停诊/调班申请表
    op.create_table(
        'leave_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('doctor_id', sa.String(36), nullable=False, comment='医生ID'),
        sa.Column('request_type', sa.String(20), nullable=False, comment='申请类型'),
        sa.Column('schedule_id', sa.String(36), comment='排班ID'),
        sa.Column('stop_date', sa.Date, comment='停诊日期'),
        sa.Column('stop_period', sa.String(20), comment='停诊时段'),
        sa.Column('original_date', sa.Date, comment='原日期'),
        sa.Column('original_period', sa.String(20), comment='原时段'),
        sa.Column('target_date', sa.Date, comment='目标日期'),
        sa.Column('target_period', sa.String(20), comment='目标时段'),
        sa.Column('reason', sa.Text, nullable=False, comment='申请原因'),
        sa.Column('status', sa.String(20), default='pending', comment='状态'),
        sa.Column('reviewer_id', sa.String(36), comment='审核人ID'),
        sa.Column('review_comment', sa.Text, comment='审核意见'),
        sa.Column('reviewed_at', sa.DateTime, comment='审核时间'),
        sa.Column('affected_appointments', sa.Integer, default=0, comment='受影响预约数'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_leave_requests_doctor_id', 'leave_requests', ['doctor_id'])
    
    # 用户反馈表
    op.create_table(
        'feedbacks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False, comment='用户ID'),
        sa.Column('user_type', sa.String(20), default='patient', comment='用户类型'),
        sa.Column('feedback_type', sa.String(20), default='suggestion', comment='反馈类型'),
        sa.Column('title', sa.String(200), nullable=False, comment='反馈标题'),
        sa.Column('content', sa.Text, nullable=False, comment='反馈内容'),
        sa.Column('images', sa.Text, comment='图片URL列表'),
        sa.Column('contact', sa.String(50), comment='联系方式'),
        sa.Column('status', sa.String(20), default='pending', comment='状态'),
        sa.Column('handler_id', sa.String(36), comment='处理人ID'),
        sa.Column('reply', sa.Text, comment='回复内容'),
        sa.Column('handled_at', sa.DateTime, comment='处理时间'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_feedbacks_user_id', 'feedbacks', ['user_id'])


def downgrade() -> None:
    op.drop_table('feedbacks')
    op.drop_table('leave_requests')
    op.drop_table('message_templates')
    op.drop_table('messages')
    op.drop_table('store_departments')
    op.drop_table('stores')
