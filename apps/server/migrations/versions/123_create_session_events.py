"""创建会话回放事件表与热力图坐标表

Revision ID: 123
Revises: 122
Create Date: 2026-06-17
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = '123'
down_revision = '122'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # session_events: rrweb 录制事件批次（每 batch 一行，session_id 串联）
    op.create_table(
        'session_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID'),
        sa.Column('platform', sa.String(20), nullable=False, comment='平台: admin/h5/miniapp'),
        sa.Column('session_id', sa.String(64), nullable=False, index=True, comment='会话ID，与 behavior_log 共用'),
        sa.Column('actor_id', sa.String(36), nullable=True, index=True, comment='操作者ID（员工 account_id）'),
        sa.Column('actor_name', sa.String(100), nullable=True, comment='操作者姓名'),
        sa.Column('viewport_w', sa.Integer, nullable=True, comment='录制视口宽(px)'),
        sa.Column('viewport_h', sa.Integer, nullable=True, comment='录制视口高(px)'),
        sa.Column('page_path', sa.String(255), nullable=True, index=True, comment='本批次主要页面路径'),
        sa.Column('event_count', sa.Integer, nullable=False, server_default='0', comment='本批次事件数'),
        sa.Column('storage_url', sa.String(512), nullable=True, comment='rrweb 事件 JSON 的对象存储路径'),
        sa.Column('storage_key', sa.String(512), nullable=True, comment='对象存储 key（清理用）'),
        sa.Column('sequence', sa.Integer, nullable=False, server_default='0', comment='会话内批次序号'),
        sa.Column('started_at', sa.DateTime, nullable=True, comment='本批次起始时间'),
        sa.Column('ended_at', sa.DateTime, nullable=True, comment='本批次结束时间'),
        sa.Column('ip', sa.String(50), nullable=True, comment='IP地址'),
        sa.Column('user_agent', sa.String(500), nullable=True, comment='User-Agent'),
        sa.Column(
            'created_at', sa.DateTime,
            server_default=sa.func.now(), nullable=True,
            index=True, comment='创建时间',
        ),
    )

    # heatmap_points: 热力图坐标聚合点（相对坐标 + 视口分桶 + 量化网格）
    op.create_table(
        'heatmap_points',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=True, index=True, comment='租户ID'),
        sa.Column('page_path', sa.String(255), nullable=False, index=True, comment='页面路径'),
        sa.Column('viewport_bucket', sa.String(20), nullable=False, index=True, comment='视口分桶: lg/md/sm'),
        sa.Column('event_type', sa.String(20), nullable=False, comment='事件类型: click/move'),
        sa.Column('x_ratio', sa.Numeric(5, 4), nullable=False, comment='x/视口宽，0~1（量化到 0.01）'),
        sa.Column('y_ratio', sa.Numeric(5, 4), nullable=False, comment='y/视口高，0~1（量化到 0.01）'),
        sa.Column('weight', sa.Integer, nullable=False, server_default='1', comment='聚合计数'),
        sa.Column('day', sa.Date, nullable=False, index=True, comment='日期，按天分区清理'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), nullable=True, comment='更新时间'),
    )

    # 唯一索引用 NULLS NOT DISTINCT（PG15+ CREATE INDEX 语法，ALTER TABLE ADD CONSTRAINT 不支持此语法）：
    # tenant_id 可为 NULL（平台级/未识别租户），普通 UNIQUE 中 NULL!=NULL 会导致
    # ON CONFLICT 永不命中、同坐标重复行堆积。NULLS NOT DISTINCT 让 NULL 视为相等，upsert 正常聚合。
    op.execute(
        "CREATE UNIQUE INDEX uq_heatmap_point_cell "
        "ON heatmap_points "
        "(tenant_id, page_path, viewport_bucket, event_type, x_ratio, y_ratio, day) "
        "NULLS NOT DISTINCT"
    )


def downgrade() -> None:
    op.drop_index('uq_heatmap_point_cell', table_name='heatmap_points')
    op.drop_table('heatmap_points')
    op.drop_table('session_events')
