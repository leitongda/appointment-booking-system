"""seed dictionary data - third batch (P2 deeply-coupled types)

Revision ID: 114
Revises: 113
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime

revision = '114'
down_revision = '113'
branch_labels = None
depends_on = None

# P2 字典类型：深度耦合字典
DICT_TYPES = [
    (
        "appointment_type",
        "预约类型",
        "预约挂号的类型分类",
        [
            ("加急", "urgent", 1),
            ("普通", "normal", 2),
            ("专家", "expert", 3),
            ("医保", "medical_insurance", 4),
            ("自费", "self_pay", 5),
        ],
    ),
]


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.utcnow()

    for type_code, type_name, type_desc, items in DICT_TYPES:
        type_id = str(uuid.uuid4())

        # 检查是否已存在
        existing = conn.execute(
            sa.text("SELECT id FROM dict_types WHERE code = :code AND tenant_id IS NULL"),
            {"code": type_code},
        ).fetchone()

        if existing:
            type_id = existing[0]
        else:
            conn.execute(
                sa.text(
                    """INSERT INTO dict_types (id, code, name, description, status, tenant_id, created_at, updated_at)
                    VALUES (:id, :code, :name, :desc, 1, NULL, :now, :now)"""
                ),
                {"id": type_id, "code": type_code, "name": type_name, "desc": type_desc, "now": now},
            )

        for label, value, sort_order in items:
            item_id = str(uuid.uuid4())
            # 检查是否已存在
            existing_item = conn.execute(
                sa.text(
                    "SELECT id FROM dict_items WHERE dict_type_id = :type_id AND value = :value AND tenant_id IS NULL"
                ),
                {"type_id": type_id, "value": value},
            ).fetchone()

            if not existing_item:
                conn.execute(
                    sa.text(
                        """INSERT INTO dict_items (id, dict_type_id, label, value, sort_order, status, extra, tenant_id, created_at, updated_at)
                        VALUES (:id, :type_id, :label, :value, :sort, 1, NULL, NULL, :now, :now)"""
                    ),
                    {
                        "id": item_id,
                        "type_id": type_id,
                        "label": label,
                        "value": value,
                        "sort": sort_order,
                        "now": now,
                    },
                )


def downgrade() -> None:
    conn = op.get_bind()
    for type_code, _, _, _ in DICT_TYPES:
        type_row = conn.execute(
            sa.text("SELECT id FROM dict_types WHERE code = :code AND tenant_id IS NULL"),
            {"code": type_code},
        ).fetchone()
        if type_row:
            conn.execute(
                sa.text("DELETE FROM dict_items WHERE dict_type_id = :type_id AND tenant_id IS NULL"),
                {"type_id": type_row[0]},
            )
            conn.execute(
                sa.text("DELETE FROM dict_types WHERE id = :id"),
                {"id": type_row[0]},
            )
