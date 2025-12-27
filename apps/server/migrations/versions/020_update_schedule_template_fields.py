"""update schedule_template fields: weekday to weekdays, add slot_count, rename total_slots to slot_capacity

Revision ID: 020
Revises: 019_add_store_fee_templates
Create Date: 2025-01-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import json


# revision identifiers, used by Alembic.
revision = '020_schedule_template_fields'
down_revision = '019_add_store_fee_templates'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # ========== schedule_templates 表字段更新 ==========
    
    # 1. 添加 weekdays 字段（Text类型，存储JSON数组）
    if not column_exists('schedule_templates', 'weekdays'):
        op.add_column('schedule_templates', sa.Column('weekdays', sa.Text, nullable=True, comment='星期数组 JSON格式 [1,2,3,4,5]'))
    
    # 2. 添加 slot_count 字段
    if not column_exists('schedule_templates', 'slot_count'):
        op.add_column('schedule_templates', sa.Column('slot_count', sa.Integer, nullable=True, server_default='1', comment='班次数量'))
    
    # 3. 添加 slot_capacity 字段
    if not column_exists('schedule_templates', 'slot_capacity'):
        op.add_column('schedule_templates', sa.Column('slot_capacity', sa.Integer, nullable=True, server_default='10', comment='每班次人数'))
    
    # 4. 迁移旧数据：将 weekday 转换为 weekdays JSON数组
    connection = op.get_bind()
    try:
        # 检查是否有 weekday 字段
        if column_exists('schedule_templates', 'weekday'):
            # 将 weekday 转换为 weekdays JSON数组
            result = connection.execute(sa.text("SELECT id, weekday FROM schedule_templates WHERE weekdays IS NULL OR weekdays = ''"))
            rows = result.fetchall()
            for row in rows:
                template_id, weekday = row
                if weekday:
                    weekdays_json = json.dumps([weekday])
                    connection.execute(sa.text("UPDATE schedule_templates SET weekdays = :weekdays WHERE id = :id"), 
                               {"weekdays": weekdays_json, "id": template_id})
        
        # 迁移 total_slots 到 slot_capacity
        if column_exists('schedule_templates', 'total_slots'):
            connection.execute(sa.text("UPDATE schedule_templates SET slot_capacity = total_slots WHERE slot_capacity IS NULL"))
        
        # 设置默认值
        connection.execute(sa.text("UPDATE schedule_templates SET slot_count = 1 WHERE slot_count IS NULL"))
        connection.execute(sa.text("UPDATE schedule_templates SET slot_capacity = 10 WHERE slot_capacity IS NULL"))
    except Exception as e:
        print(f"数据迁移错误: {e}")
    
    # 5. 设置字段为 NOT NULL（在数据迁移后）
    try:
        op.alter_column('schedule_templates', 'weekdays', nullable=False)
        op.alter_column('schedule_templates', 'slot_count', nullable=False)
        op.alter_column('schedule_templates', 'slot_capacity', nullable=False)
    except Exception as e:
        print(f"设置NOT NULL约束时出错（可能已有约束）: {e}")


def downgrade() -> None:
    # 回滚：删除新字段，保留旧字段
    if column_exists('schedule_templates', 'slot_capacity'):
        op.drop_column('schedule_templates', 'slot_capacity')
    
    if column_exists('schedule_templates', 'slot_count'):
        op.drop_column('schedule_templates', 'slot_count')
    
    if column_exists('schedule_templates', 'weekdays'):
        op.drop_column('schedule_templates', 'weekdays')

