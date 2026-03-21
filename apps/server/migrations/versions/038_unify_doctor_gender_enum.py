"""unify doctor gender enum

Revision ID: 038_unify_doctor_gender_enum
Revises: 037_store_email_recipients
Create Date: 2026-03-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "038_unify_doctor_gender_enum"
down_revision = "037_store_email_recipients"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 旧医生枚举: 0=女, 1=男
    # 新统一枚举: 0=未知, 1=男, 2=女
    op.execute("UPDATE doctors SET gender = 2 WHERE gender = 0")

    with op.batch_alter_table("doctors") as batch_op:
        batch_op.alter_column(
            "gender",
            existing_type=sa.Integer(),
            server_default="0",
            existing_nullable=True,
        )


def downgrade() -> None:
    # 回退到旧医生枚举: 0=女, 1=男
    # 新语义中的未知(0)在旧语义中不存在，回退时将未知并入男(1)
    op.execute("UPDATE doctors SET gender = 1 WHERE gender = 0")
    op.execute("UPDATE doctors SET gender = 0 WHERE gender = 2")

    with op.batch_alter_table("doctors") as batch_op:
        batch_op.alter_column(
            "gender",
            existing_type=sa.Integer(),
            server_default="1",
            existing_nullable=True,
        )
