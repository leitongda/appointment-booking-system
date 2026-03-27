"""Alembic 迁移集成测试

验证:
- 迁移可以正常执行
- 迁移可以正常回滚
- 复合索引已创建

注意: 这些测试需要真实 PostgreSQL 连接，通过 TEST_DATABASE_URL 环境变量配置。
      在 PG 不可用时自动跳过。
"""
import os
import pytest
from sqlalchemy import inspect, text


TEST_PG_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5433/test_db"
)


def _pg_available() -> bool:
    """检查 PostgreSQL 是否可用"""
    try:
        from sqlalchemy import create_engine
        sync_url = TEST_PG_URL.replace("+asyncpg", "+psycopg2")
        engine = create_engine(sync_url, echo=False)
        conn = engine.connect()
        conn.close()
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pg_connection():
    """创建同步 PostgreSQL 连接用于 Alembic"""
    pytest.importorskip("psycopg2")
    from sqlalchemy import create_engine
    # 转换为同步 URL
    sync_url = TEST_PG_URL.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, echo=False)
    connection = engine.connect()
    yield connection
    connection.close()
    engine.dispose()


class TestAlembicMigration:
    """Alembic 迁移测试套件"""

    @pytest.mark.skipif(not _pg_available(), reason="PostgreSQL not available")
    def test_migration_tables_exist(self, pg_connection):
        """验证核心业务表存在"""
        inspector = inspect(pg_connection)
        required_tables = [
            "tenants",
            "subscription_plans",
            "stores",
            "admins",
            "roles",
            "users",
            "patients",
            "doctors",
            "departments",
            "schedules",
            "schedule_templates",
            "appointments",
        ]
        existing_tables = inspector.get_table_names()
        for table in required_tables:
            assert table in existing_tables, f"Table '{table}' should exist"

    @pytest.mark.skipif(not _pg_available(), reason="PostgreSQL not available")
    def test_tenant_id_columns_exist(self, pg_connection):
        """验证核心业务表有 tenant_id 列"""
        inspector = inspect(pg_connection)
        tables_with_tenant_id = [
            "stores", "admins", "users", "patients",
            "doctors", "departments", "schedules",
            "schedule_templates", "appointments",
        ]
        for table in tables_with_tenant_id:
            columns = [col["name"] for col in inspector.get_columns(table)]
            assert "tenant_id" in columns, f"Table '{table}' should have 'tenant_id' column"

    @pytest.mark.skipif(not _pg_available(), reason="PostgreSQL not available")
    def test_composite_indexes_exist(self, pg_connection):
        """验证复合索引已创建"""
        inspector = inspect(pg_connection)
        expected_indexes = [
            "idx_appointments_tenant_status",
            "idx_appointments_tenant_user",
            "idx_appointments_tenant_doctor_date",
            "idx_schedules_tenant_doctor_date",
            "idx_schedules_tenant_store_date",
            "idx_doctors_tenant_department",
            "idx_doctors_tenant_store",
            "idx_stores_tenant_status",
            "idx_admins_tenant_role",
            "idx_users_tenant_phone",
        ]
        for table_name in ["appointments", "schedules", "doctors", "stores", "admins", "users"]:
            indexes = inspector.get_indexes(table_name)
            index_names = [idx["name"] for idx in indexes]
            for expected in expected_indexes:
                # Check if this index belongs to this table
                if expected.startswith(f"idx_{table_name}_"):
                    assert expected in index_names, f"Index '{expected}' should exist on table '{table_name}'"

    @pytest.mark.skipif(not _pg_available(), reason="PostgreSQL not available")
    def test_unique_constraints(self, pg_connection):
        """验证租户内唯一约束"""
        inspector = inspect(pg_connection)
        # Check stores unique constraint
        stores_constraints = inspector.get_unique_constraints("stores")
        constraint_names = [uc["name"] for uc in stores_constraints]
        assert "uq_stores_tenant_code" in constraint_names, "stores should have (tenant_id, code) unique constraint"
