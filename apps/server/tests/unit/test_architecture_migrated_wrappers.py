from pathlib import Path


# 相对于本测试文件的 server 根目录
_SERVER_ROOT = Path(__file__).resolve().parent.parent.parent


# These wrapper files have been deleted as part of the module boundary refactor.
# This test verifies they are gone and that code no longer references them.
DELETED_WRAPPERS = [
    "admin_service.py",
    "blacklist_service.py",
    "booking_notice_service.py",
    "consultation_fee_service.py",
    "content_service.py",
    "custom_schedule_service.py",
    "department_service.py",
    "doctor_booking_setting_service.py",
    "doctor_service.py",
    "email_service.py",
    "excel_service.py",
    "export_service.py",
    "feedback_service.py",
    "image_processor.py",
    "import_service.py",
    "leave_request_service.py",
    "medical_record_service.py",
    "message_service.py",
    "notification_service.py",
    "point_service.py",
    "rest_day_service.py",
    "revenue_service.py",
    "rule_engine_service.py",
    "rule_set_import_service.py",
    "rule_set_service.py",
    "schedule_service.py",
    "schedule_suspension_service.py",
    "schedule_template_service.py",
    "settings_service.py",
    "shift_type_service.py",
    "sms_service.py",
    "store_email_recipient_service.py",
    "store_service.py",
    "user_favorite_service.py",
    "user_service.py",
    "visit_type_service.py",
    "waitlist_service.py",
    "wechat_service.py",
]

# These files contain actual implementations and remain in their module homes.
REMAINING_IMPLEMENTATIONS = [
    "app/modules/email_templates/service.py",
    "app/modules/rule_engine/rule_performance_service.py",
]


def test_api_v1_only_contains_init():
    """验证 api/v1 目录只保留 __init__.py 作为路由注册层"""
    api_dir = _SERVER_ROOT / "app" / "api" / "v1"
    py_files = list(api_dir.glob("*.py"))
    assert len(py_files) == 1, f"api/v1 应只包含 __init__.py，但发现: {[f.name for f in py_files]}"
    assert py_files[0].name == "__init__.py"


def test_storage_compat_layer_removed():
    storage_dir = _SERVER_ROOT / "app" / "services" / "storage"
    assert not list(storage_dir.glob("*.py"))


def test_deleted_wrappers_no_longer_exist():
    """验证所有兼容层 wrapper 文件已被删除"""
    services_dir = _SERVER_ROOT / "app" / "services"
    for filename in DELETED_WRAPPERS:
        assert not (services_dir / filename).exists(), f"{filename} should have been deleted"


def test_remaining_implementations_still_exist():
    """验证包含实际业务逻辑的文件仍保留"""
    for relative_path in REMAINING_IMPLEMENTATIONS:
        assert (_SERVER_ROOT / relative_path).exists(), f"{relative_path} should still exist"
