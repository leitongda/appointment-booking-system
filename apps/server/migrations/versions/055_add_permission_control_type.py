"""add permission control type

Revision ID: 055_add_permission_control_type
Revises: 054_add_tenant_id_to_blacklists
Create Date: 2026-04-17 22:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "055_add_permission_control_type"
down_revision = "054_add_tenant_id_to_blacklists"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "permissions",
        sa.Column("control_type", sa.String(length=20), nullable=True, comment="控制类型: page/tab/action/api"),
    )

    op.execute(
        """
        WITH child_counts AS (
            SELECT parent_code, COUNT(*) AS child_count
            FROM permissions
            WHERE parent_code IS NOT NULL
            GROUP BY parent_code
        ),
        permission_depths AS (
            WITH RECURSIVE permission_tree AS (
                SELECT
                    p.code,
                    0 AS depth
                FROM permissions p
                WHERE p.parent_code IS NULL
                UNION ALL
                SELECT
                    child.code,
                    tree.depth + 1 AS depth
                FROM permissions child
                JOIN permission_tree tree ON child.parent_code = tree.code
            )
            SELECT * FROM permission_tree
        ),
        permission_metadata AS (
            SELECT
                p.code,
                p.type,
                depth_info.depth,
                COALESCE(child_counts.child_count, 0) AS child_count,
                split_part(p.code, ':', array_length(string_to_array(p.code, ':'), 1)) AS last_segment
            FROM permissions p
            JOIN permission_depths AS depth_info ON depth_info.code = p.code
            LEFT JOIN child_counts ON child_counts.parent_code = p.code
        )
        UPDATE permissions AS p
        SET control_type = CASE
            WHEN meta.depth = 0 THEN 'page'
            WHEN meta.child_count > 0 THEN 'tab'
            WHEN meta.last_segment IN (
                'create', 'update', 'delete', 'approve', 'refund', 'send', 'reply',
                'reset-password', 'manage', 'cancel', 'bind', 'import', 'batch',
                'sort', 'kick', 'generate-username', 'check-username', 'check-unique', 'status'
            ) THEN 'action'
            WHEN meta.last_segment IN (
                'list', 'detail', 'view', 'export', 'statistics', 'all', 'history'
            ) THEN 'api'
            WHEN meta.depth = 1 OR meta.type = 'menu' THEN 'tab'
            ELSE 'action'
        END
        FROM permission_metadata AS meta
        WHERE p.code = meta.code
        """
    )

    op.alter_column("permissions", "control_type", existing_type=sa.String(length=20), nullable=False)
    op.create_index("ix_permissions_control_type", "permissions", ["control_type"])


def downgrade() -> None:
    op.drop_index("ix_permissions_control_type", table_name="permissions")
    op.drop_column("permissions", "control_type")
