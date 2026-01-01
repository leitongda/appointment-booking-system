"""add snapshot fields to appointments for doctor and patient info

Revision ID: 031_appointment_snapshot
Revises: 030_visit_type_config
Create Date: 2025-01-01

Add patient_name, patient_phone, doctor_name, doctor_title, department_name
to appointments table as snapshot fields to preserve data at booking time.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision = '031_appointment_snapshot'
down_revision = '030_remove_registration_fee'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except:
        return False


def upgrade() -> None:
    # 1. 添加就诊人快照字段
    if not column_exists('appointments', 'patient_name'):
        op.add_column('appointments', sa.Column(
            'patient_name',
            sa.String(50),
            nullable=True,
            comment='就诊人姓名(快照)'
        ))
    
    if not column_exists('appointments', 'patient_phone'):
        op.add_column('appointments', sa.Column(
            'patient_phone',
            sa.String(20),
            nullable=True,
            comment='就诊人手机(快照)'
        ))
    
    # 2. 添加医生快照字段
    if not column_exists('appointments', 'doctor_name'):
        op.add_column('appointments', sa.Column(
            'doctor_name',
            sa.String(50),
            nullable=True,
            comment='医生姓名(快照)'
        ))
    
    if not column_exists('appointments', 'doctor_title'):
        op.add_column('appointments', sa.Column(
            'doctor_title',
            sa.String(50),
            nullable=True,
            comment='医生职称(快照)'
        ))
    
    if not column_exists('appointments', 'department_name'):
        op.add_column('appointments', sa.Column(
            'department_name',
            sa.String(100),
            nullable=True,
            comment='科室名称(快照)'
        ))
    
    # 3. 回填历史数据
    bind = op.get_bind()
    
    # 回填就诊人信息
    bind.execute(text("""
        UPDATE appointments a
        SET patient_name = p.name,
            patient_phone = p.phone
        FROM patients p
        WHERE a.patient_id = p.id
        AND (a.patient_name IS NULL OR a.patient_phone IS NULL)
    """))
    
    # 回填医生信息
    bind.execute(text("""
        UPDATE appointments a
        SET doctor_name = d.name,
            doctor_title = d.title,
            department_name = dept.name
        FROM doctors d
        LEFT JOIN departments dept ON d.department_id = dept.id
        WHERE a.doctor_id = d.id
        AND (a.doctor_name IS NULL OR a.doctor_title IS NULL OR a.department_name IS NULL)
    """))


def downgrade() -> None:
    # 删除快照字段
    if column_exists('appointments', 'department_name'):
        op.drop_column('appointments', 'department_name')
    
    if column_exists('appointments', 'doctor_title'):
        op.drop_column('appointments', 'doctor_title')
    
    if column_exists('appointments', 'doctor_name'):
        op.drop_column('appointments', 'doctor_name')
    
    if column_exists('appointments', 'patient_phone'):
        op.drop_column('appointments', 'patient_phone')
    
    if column_exists('appointments', 'patient_name'):
        op.drop_column('appointments', 'patient_name')

