"""merge custom_schedules into schedules

Revision ID: 021_merge_custom_schedules
Revises: 020_schedule_template_fields
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision = '021_merge_custom_schedules'
down_revision = '020_schedule_template_fields'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # 确保 schedules 表的 time_slot 可以为空（用于自定义排班）
    if column_exists('schedules', 'time_slot'):
        op.alter_column('schedules', 'time_slot',
                       existing_type=sa.String(10),
                       nullable=True)
    
    # 如果 custom_schedules 表存在，迁移数据到 schedules
    if table_exists('custom_schedules'):
        # 迁移数据：将 custom_schedules 的数据插入到 schedules
        # 使用 SQL 直接迁移，因为需要计算 time_slot
        connection = op.get_bind()
        
        # 迁移语句：将 custom_schedules 数据转换为 schedules 格式
        migration_sql = """
        INSERT INTO schedules (
            id, doctor_id, store_id, template_id, schedule_date, 
            time_slot, start_time, end_time, total_slots, booked_slots, 
            appointment_type, status, created_at, updated_at
        )
        SELECT 
            cs.id,
            cs.doctor_id,
            cs.store_id,
            NULL as template_id,  -- 自定义排班没有模板ID
            cs.schedule_date,
            CASE 
                WHEN EXTRACT(HOUR FROM cs.start_time) < 12 THEN 'morning'
                WHEN EXTRACT(HOUR FROM cs.start_time) < 18 THEN 'afternoon'
                ELSE 'evening'
            END as time_slot,
            cs.start_time,
            cs.end_time,
            cs.max_patients as total_slots,
            cs.booked_count as booked_slots,
            cs.appointment_type,
            cs.status,
            cs.created_at,
            cs.updated_at
        FROM custom_schedules cs
        WHERE NOT EXISTS (
            SELECT 1 FROM schedules s 
            WHERE s.id = cs.id
        )
        """
        
        connection.execute(text(migration_sql))
        
        # 删除 custom_schedules 表
        op.drop_index('ix_custom_schedules_schedule_date', 'custom_schedules', if_exists=True)
        op.drop_index('ix_custom_schedules_doctor_id', 'custom_schedules', if_exists=True)
        op.drop_index('ix_custom_schedules_store_id', 'custom_schedules', if_exists=True)
        op.drop_table('custom_schedules')


def downgrade() -> None:
    # 重新创建 custom_schedules 表
    op.create_table(
        'custom_schedules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('store_id', sa.String(36), sa.ForeignKey('stores.id'), nullable=False),
        sa.Column('department_id', sa.String(36), sa.ForeignKey('departments.id'), nullable=False),
        sa.Column('doctor_id', sa.String(36), sa.ForeignKey('doctors.id'), nullable=False),
        sa.Column('schedule_date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('appointment_type', sa.String(20), nullable=False),
        sa.Column('max_patients', sa.Integer(), default=1),
        sa.Column('booked_count', sa.Integer(), default=0),
        sa.Column('status', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    
    # 创建索引
    op.create_index('ix_custom_schedules_store_id', 'custom_schedules', ['store_id'])
    op.create_index('ix_custom_schedules_doctor_id', 'custom_schedules', ['doctor_id'])
    op.create_index('ix_custom_schedules_schedule_date', 'custom_schedules', ['schedule_date'])
    
    # 从 schedules 恢复数据到 custom_schedules（仅恢复 template_id 为 NULL 的记录）
    connection = op.get_bind()
    restore_sql = """
    INSERT INTO custom_schedules (
        id, store_id, department_id, doctor_id, schedule_date,
        start_time, end_time, appointment_type, max_patients, booked_count,
        status, created_at, updated_at
    )
    SELECT 
        s.id,
        s.store_id,
        d.department_id,  -- 从医生表获取科室ID
        s.doctor_id,
        s.schedule_date,
        s.start_time,
        s.end_time,
        s.appointment_type,
        s.total_slots as max_patients,
        s.booked_slots as booked_count,
        s.status,
        s.created_at,
        s.updated_at
    FROM schedules s
    LEFT JOIN doctors d ON s.doctor_id = d.id
    WHERE s.template_id IS NULL
    """
    
    connection.execute(text(restore_sql))
    
    # 恢复 time_slot 为非空
    if column_exists('schedules', 'time_slot'):
        op.alter_column('schedules', 'time_slot',
                       existing_type=sa.String(10),
                       nullable=False)

