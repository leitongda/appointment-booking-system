"""remove_weekday_column_from_schedule_templates

Revision ID: 2fc10ef02888
Revises: 021_merge_custom_schedules
Create Date: 2025-12-27 17:29:09.997759

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '2fc10ef02888'
down_revision = '021_merge_custom_schedules'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # 删除旧的 weekday 字段（如果存在）
    # 因为已经迁移到 weekdays 字段了
    if column_exists('schedule_templates', 'weekday'):
        # 先删除 NOT NULL 约束（如果存在）
        try:
            op.alter_column('schedule_templates', 'weekday', nullable=True)
        except Exception:
            pass
        
        # 删除字段
        op.drop_column('schedule_templates', 'weekday')
    
    # 删除旧的 total_slots 字段（如果存在）
    # 因为已经迁移到 slot_capacity 字段了
    if column_exists('schedule_templates', 'total_slots'):
        op.drop_column('schedule_templates', 'total_slots')


def downgrade() -> None:
    # 回滚：重新添加 weekday 字段
    if not column_exists('schedule_templates', 'weekday'):
        op.add_column('schedule_templates', sa.Column('weekday', sa.Integer, nullable=True, comment='星期 1-7'))
        # 从 weekdays 字段恢复数据到 weekday（取第一个值）
        connection = op.get_bind()
        try:
            import json
            # 获取所有记录
            result = connection.execute(sa.text("SELECT id, weekdays FROM schedule_templates WHERE weekdays IS NOT NULL AND weekdays != ''"))
            rows = result.fetchall()
            for row in rows:
                template_id, weekdays_str = row
                try:
                    weekdays_list = json.loads(weekdays_str)
                    if weekdays_list and len(weekdays_list) > 0:
                        weekday_value = weekdays_list[0]
                        connection.execute(sa.text("UPDATE schedule_templates SET weekday = :weekday WHERE id = :id"), 
                                       {"weekday": weekday_value, "id": template_id})
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            # 设置 NOT NULL
            op.alter_column('schedule_templates', 'weekday', nullable=False)
        except Exception as e:
            print(f"恢复 weekday 字段数据时出错: {e}")
    
    # 回滚：重新添加 total_slots 字段
    if not column_exists('schedule_templates', 'total_slots'):
        op.add_column('schedule_templates', sa.Column('total_slots', sa.Integer, nullable=True, server_default='10', comment='班次人数'))
        # 从 slot_capacity 恢复数据
        connection = op.get_bind()
        try:
            connection.execute(sa.text("UPDATE schedule_templates SET total_slots = slot_capacity WHERE total_slots IS NULL"))
        except Exception as e:
            print(f"恢复 total_slots 字段数据时出错: {e}")

