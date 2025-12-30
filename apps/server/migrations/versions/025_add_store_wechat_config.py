"""add wechat config fields to stores table

Revision ID: 025_add_store_wechat_config
Revises: 024_add_audit_fields
Create Date: 2024-12-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '025_add_store_wechat_config'
down_revision = '024_add_audit_fields'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    bind = op.get_bind()
    inspector = inspect(bind)
    try:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def upgrade():
    """添加微信配置字段到 stores 表"""
    wechat_columns = [
        ('wechat_app_id', sa.String(100), '微信小程序AppID'),
        ('wechat_app_secret', sa.String(100), '微信小程序Secret'),
        ('wechat_mch_id', sa.String(100), '微信支付商户号'),
        ('wechat_api_key', sa.String(100), '微信支付API密钥'),
        ('wechat_notify_url', sa.String(255), '微信支付回调地址'),
    ]
    
    for col_name, col_type, comment in wechat_columns:
        if not column_exists('stores', col_name):
            op.add_column(
                'stores',
                sa.Column(col_name, col_type, nullable=True, comment=comment)
            )
            print(f"stores 表已添加 {col_name} 字段")
        else:
            print(f"stores 表已存在 {col_name} 字段，跳过")


def downgrade():
    """删除微信配置字段"""
    wechat_columns = [
        'wechat_app_id',
        'wechat_app_secret',
        'wechat_mch_id',
        'wechat_api_key',
        'wechat_notify_url',
    ]
    
    for col_name in wechat_columns:
        if column_exists('stores', col_name):
            op.drop_column('stores', col_name)

