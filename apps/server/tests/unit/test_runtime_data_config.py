from app.core.config import Settings


def test_runtime_data_defaults_point_outside_source_roots(monkeypatch):
    for key in ("RUNTIME_DATA_DIR", "LOG_DIR", "LOCAL_UPLOAD_DIR"):
        monkeypatch.delenv(key, raising=False)

    test_settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/test",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="test-secret-key",
    )

    assert test_settings.RUNTIME_DATA_DIR == "var/server"
    assert test_settings.LOG_DIR.startswith("var/server/")
    assert test_settings.LOCAL_UPLOAD_DIR.startswith("var/server/")
