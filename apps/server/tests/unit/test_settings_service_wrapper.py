from app.modules.settings.service import SettingsService as modular_settings_service
from app.modules.settings.service import SettingsService as legacy_settings_service


def test_settings_service_wrapper_reuses_modular_service():
    assert legacy_settings_service is modular_settings_service
