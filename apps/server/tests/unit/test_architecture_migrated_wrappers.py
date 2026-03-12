from pathlib import Path


SERVICE_WRAPPERS = {
    "admin_service.py": {
        "imports": ["from app.modules.admin.service_admins import AdminService"],
        "allow_class": False,
    },
    "consultation_fee_service.py": [
        "from app.modules.consultation_fees.service import ConsultationFeeService"
    ],
    "doctor_service.py": ["from app.modules.doctors.service import DoctorService"],
    "excel_service.py": ["from app.infrastructure.excel.export_service import ExcelExportService"],
    "image_processor.py": ["from app.infrastructure.image.processor import"],
    "message_service.py": ["from app.modules.messages.service_messages import MessageService"],
    "notification_service.py": [
        "from app.infrastructure.notification.service import NotificationService"
    ],
    "rule_engine_service.py": ["from app.modules.rule_engine import RuleEngineService"],
    "rule_set_import_service.py": [
        "from app.modules.import_export.service_rule_set_import import RuleSetImportService"
    ],
    "rule_set_service.py": ["from app.modules.rule_sets.service import RuleSetService"],
    "schedule_service.py": ["from app.modules.schedules.service import ScheduleService"],
    "schedule_template_service.py": [
        "from app.modules.schedule_templates.service import ScheduleTemplateService"
    ],
    "settings_service.py": ["from app.modules.settings.service import SettingsService"],
    "sms_service.py": ["from app.infrastructure.sms.service import SmsService"],
    "store_service.py": ["from app.modules.stores.service import StoreService"],
    "waitlist_service.py": ["from app.modules.waitlist.service import WaitlistService"],
    "wechat_service.py": ["from app.infrastructure.wechat.service import WechatService"],
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_api_v1_only_contains_init():
    """验证 api/v1 目录只保留 __init__.py 作为路由注册层"""
    api_dir = Path("app/api/v1")
    py_files = list(api_dir.glob("*.py"))
    assert len(py_files) == 1, f"api/v1 应只包含 __init__.py，但发现: {[f.name for f in py_files]}"
    assert py_files[0].name == "__init__.py"


def test_storage_compat_layer_removed():
    storage_dir = Path("app/services/storage")
    assert not list(storage_dir.glob("*.py"))


def test_migrated_service_wrappers_stay_thin():
    services_dir = Path("app/services")
    default_forbidden_tokens = ["class ", "async def "]
    facade_forbidden_tokens = ["db.execute(", "db.scalar("]

    for filename, config in SERVICE_WRAPPERS.items():
        if isinstance(config, dict):
            import_lines = config["imports"]
            allow_class = config.get("allow_class", False)
        else:
            import_lines = config
            allow_class = False
        text = _read(services_dir / filename)
        assert any(
            marker in text for marker in ("from app.modules.", "from app.infrastructure.")
        ), f"{filename} should delegate to app.modules or app.infrastructure"
        for import_line in import_lines:
            assert import_line in text
        forbidden_tokens = facade_forbidden_tokens if allow_class else default_forbidden_tokens
        for token in forbidden_tokens:
            assert token not in text, f"{filename} should stay a thin wrapper; found {token}"
