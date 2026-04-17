from unittest.mock import MagicMock, patch

from app.models.blacklist import Blacklist
from app.tasks.blacklist_task import _get_setting_value, check_and_add_blacklist


def _mock_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def test_get_setting_value_supports_snake_case_key():
    db = MagicMock()
    setting = MagicMock()
    setting.value = "30"
    db.execute.side_effect = [_mock_result(setting)]

    assert _get_setting_value(db, "booking", "blacklist_days", 7) == "30"
    assert db.execute.call_count == 1


def test_get_setting_value_falls_back_to_camel_case_key():
    db = MagicMock()
    setting = MagicMock()
    setting.value = "5"
    db.execute.side_effect = [_mock_result(None), _mock_result(setting)]

    assert _get_setting_value(db, "booking", "no_show_limit", 3) == "5"
    assert db.execute.call_count == 2


@patch("app.tasks.blacklist_task.get_sync_db")
@patch("app.middleware.tenant_context.get_current_tenant_id", return_value="tenant-1")
def test_check_and_add_blacklist_creates_model_compatible_record(_, mock_get_sync_db):
    db = MagicMock()
    db.scalar.side_effect = [3, None]

    user = MagicMock()
    user.nickname = "测试用户"
    user.phone = "13800138000"
    db.get.return_value = user

    ctx = MagicMock()
    ctx.__enter__.return_value = db
    ctx.__exit__.return_value = False
    mock_get_sync_db.return_value = ctx

    with patch("app.tasks.blacklist_task._notify_admins_sync") as mock_notify:
        result = check_and_add_blacklist("user-1")

    assert result == {"blacklisted": True, "user_id": "user-1"}
    db.add.assert_called_once()
    blacklist = db.add.call_args.args[0]
    assert isinstance(blacklist, Blacklist)
    assert blacklist.tenant_id == "tenant-1"
    assert blacklist.user_id == "user-1"
    assert blacklist.no_show_count == 3
    assert blacklist.source == 2
    assert blacklist.status == 1
    mock_notify.assert_called_once()
    db.commit.assert_called_once()
