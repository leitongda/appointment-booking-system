from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.infrastructure.storage.base import build_tenant_storage_folder
from app.modules.tenants.service import TenantUsageService
from app.core.config import settings


def test_build_tenant_storage_folder_with_tenant():
    folder = build_tenant_storage_folder("images", "tenant-a")
    assert folder == "tenants/tenant-a/images"


def test_build_tenant_storage_folder_without_tenant():
    folder = build_tenant_storage_folder("avatars", None)
    assert folder == "avatars"


@pytest.mark.asyncio
async def test_get_storage_usage_sums_only_current_tenant_files(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_TYPE", "local", raising=False)
    monkeypatch.setattr(settings, "LOCAL_UPLOAD_DIR", str(tmp_path), raising=False)

    tenant_a_dir = tmp_path / "tenants" / "tenant-a"
    tenant_b_dir = tmp_path / "tenants" / "tenant-b"
    tenant_a_dir.mkdir(parents=True)
    tenant_b_dir.mkdir(parents=True)

    (tenant_a_dir / "images").mkdir()
    (tenant_a_dir / "avatars").mkdir()
    (tenant_b_dir / "images").mkdir()

    (tenant_a_dir / "images" / "a.png").write_bytes(b"a" * 1024)
    (tenant_a_dir / "avatars" / "b.png").write_bytes(b"b" * 2048)
    (tenant_b_dir / "images" / "c.png").write_bytes(b"c" * 4096)

    service = TenantUsageService(MagicMock())
    usage = await service._get_storage_usage("tenant-a")

    assert usage == Decimal("0.0029")


@pytest.mark.asyncio
async def test_get_storage_usage_returns_zero_for_missing_or_non_local_storage(tmp_path, monkeypatch):
    service = TenantUsageService(MagicMock())

    monkeypatch.setattr(settings, "STORAGE_TYPE", "local", raising=False)
    monkeypatch.setattr(settings, "LOCAL_UPLOAD_DIR", str(tmp_path), raising=False)
    missing_usage = await service._get_storage_usage("missing-tenant")
    assert missing_usage == Decimal("0")

    monkeypatch.setattr(settings, "STORAGE_TYPE", "minio", raising=False)
    non_local_usage = await service._get_storage_usage("tenant-a")
    assert non_local_usage == Decimal("0")
