"""双写过渡期同步服务单元测试

测试 AccountSyncService 的核心逻辑，使用 mock 模拟数据库会话。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.common.account_sync import AccountSyncService, _is_dual_write_enabled


# ================================================================
# _is_dual_write_enabled 测试
# ================================================================


@pytest.mark.unit
class TestIsDualWriteEnabled:
    """测试双写开关检查"""

    @patch("app.common.account_sync.settings")
    def test_enabled(self, mock_settings):
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        assert _is_dual_write_enabled() is True

    @patch("app.common.account_sync.settings")
    def test_disabled(self, mock_settings):
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = False
        assert _is_dual_write_enabled() is False

    @patch("app.common.account_sync.settings")
    def test_default_disabled(self, mock_settings):
        """默认关闭"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = False
        assert _is_dual_write_enabled() is False


# ================================================================
# sync_admin_to_account 测试
# ================================================================


@pytest.mark.unit
class TestSyncAdminToAccount:
    """测试 Admin 同步到 Account"""

    @patch("app.common.account_sync.settings")
    async def test_skips_when_dual_write_disabled(self, mock_settings):
        """双写关闭时不同步"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = False
        db = AsyncMock()
        await AccountSyncService.sync_admin_to_account(db, "admin_123")
        db.get.assert_not_called()

    @patch("app.common.account_sync.settings")
    @patch("app.common.account_sync.set_create_audit")
    async def test_creates_account_when_not_exists(self, mock_audit, mock_settings):
        """Account 不存在时创建新记录"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        mock_audit.return_value = None

        db = AsyncMock()

        # 模拟 Admin 记录
        mock_admin = MagicMock()
        mock_admin.id = "admin_123"
        mock_admin.tenant_id = "tenant_123"
        mock_admin.phone = "13800138000"
        mock_admin.username = "testadmin"
        mock_admin.password_hash = "hash123"
        mock_admin.name = "测试管理员"
        mock_admin.avatar = None
        mock_admin.status = 1
        mock_admin.last_login_at = None
        mock_admin.last_login_ip = None
        mock_admin.role_id = "role_123"
        mock_admin.current_store_id = "store_123"
        mock_admin.email = "admin@test.com"

        # db.get 依次返回: Admin 记录, Account(None=不存在), AccountAdmin(None=不存在)
        db.get = AsyncMock(side_effect=[mock_admin, None, None])

        # 模拟门店关联查询
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        await AccountSyncService.sync_admin_to_account(db, "admin_123")

        # 验证 db.add 被调用了两次（Account + AccountAdmin）
        assert db.add.call_count == 2
        db.flush.assert_called()

    @patch("app.common.account_sync.settings")
    @patch("app.common.account_sync.set_update_audit")
    async def test_updates_account_when_exists(self, mock_audit, mock_settings):
        """Account 已存在时更新记录"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        mock_audit.return_value = None

        db = AsyncMock()

        # 模拟 Admin 记录
        mock_admin = MagicMock()
        mock_admin.id = "admin_123"
        mock_admin.tenant_id = "tenant_123"
        mock_admin.phone = "13900139000"  # 新手机号
        mock_admin.username = "updatedadmin"
        mock_admin.password_hash = "newhash"
        mock_admin.name = "更新管理员"
        mock_admin.avatar = "avatar_url"
        mock_admin.status = 1
        mock_admin.last_login_at = None
        mock_admin.last_login_ip = None
        mock_admin.role_id = "role_456"
        mock_admin.current_store_id = "store_456"
        mock_admin.email = "updated@test.com"

        # 模拟已存在的 Account
        mock_account = MagicMock()
        # 模拟已存在的 AccountAdmin
        mock_account_admin = MagicMock()

        db.get = AsyncMock(side_effect=[mock_admin, mock_account, mock_account_admin])

        # 模拟门店关联查询
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        await AccountSyncService.sync_admin_to_account(db, "admin_123")

        # 验证 Account 字段被更新
        assert mock_account.phone == "13900139000"
        assert mock_account.username == "updatedadmin"
        assert mock_account.password_hash == "newhash"
        assert mock_account.name == "更新管理员"

        # 验证 AccountAdmin 字段被更新
        assert mock_account_admin.role_id == "role_456"
        assert mock_account_admin.current_store_id == "store_456"
        assert mock_account_admin.email == "updated@test.com"

        # db.add 不应被调用（upsert 走更新路径）
        db.add.assert_not_called()

    @patch("app.common.account_sync.settings")
    async def test_skips_when_admin_not_found(self, mock_settings):
        """旧表 Admin 记录不存在时跳过"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True

        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        await AccountSyncService.sync_admin_to_account(db, "nonexistent_id")

        # 不应有写操作
        db.add.assert_not_called()

    @patch("app.common.account_sync.settings")
    async def test_exception_does_not_propagate(self, mock_settings):
        """同步异常不应向上抛出"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True

        db = AsyncMock()
        db.get = AsyncMock(side_effect=Exception("DB error"))

        # 不应抛出异常
        await AccountSyncService.sync_admin_to_account(db, "admin_123")


# ================================================================
# sync_doctor_to_account 测试
# ================================================================


@pytest.mark.unit
class TestSyncDoctorToAccount:
    """测试 Doctor 同步到 Account"""

    @patch("app.common.account_sync.settings")
    async def test_skips_when_dual_write_disabled(self, mock_settings):
        """双写关闭时不同步"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = False
        db = AsyncMock()
        await AccountSyncService.sync_doctor_to_account(db, "doctor_123")
        db.get.assert_not_called()

    @patch("app.common.account_sync.settings")
    @patch("app.common.account_sync.set_create_audit")
    async def test_creates_account_when_not_exists(self, mock_audit, mock_settings):
        """Account 不存在时创建新记录"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        mock_audit.return_value = None

        db = AsyncMock()

        # 模拟 Doctor 记录
        mock_doctor = MagicMock()
        mock_doctor.id = "doctor_123"
        mock_doctor.tenant_id = "tenant_123"
        mock_doctor.phone = "13700137000"
        mock_doctor.username = "doctor_zhang"
        mock_doctor.password_hash = "hash_doctor"
        mock_doctor.name = "张医生"
        mock_doctor.avatar = None
        mock_doctor.gender = 1
        mock_doctor.status = 1
        mock_doctor.last_login_at = None
        mock_doctor.last_login_ip = None
        mock_doctor.store_id = "store_123"
        mock_doctor.department_id = "dept_123"
        mock_doctor.banner = None
        mock_doctor.title = "主治医师"
        mock_doctor.years_of_experience = 10
        mock_doctor.education = "本科"
        mock_doctor.graduate_school = "北京大学"
        mock_doctor.license_number = "LIC123"
        mock_doctor.license_image = None
        mock_doctor.honors = None
        mock_doctor.schedule_desc = "周一至周五"
        mock_doctor.max_daily_appointments = 30
        mock_doctor.online_consult_enabled = 1
        mock_doctor.online_consult_fee = 50.0
        mock_doctor.page_style = 1
        mock_doctor.promo_video = None
        mock_doctor.tags = "内科,消化"
        mock_doctor.specialty = "消化内科"
        mock_doctor.introduction = "资深医师"
        mock_doctor.is_recommended = 1
        mock_doctor.sort_order = 0
        mock_doctor.use_fee_template = 0
        mock_doctor.deleted_at = None

        db.get = AsyncMock(side_effect=[mock_doctor, None, None])

        await AccountSyncService.sync_doctor_to_account(db, "doctor_123")

        assert db.add.call_count == 2
        db.flush.assert_called()

    @patch("app.common.account_sync.settings")
    @patch("app.common.account_sync.set_update_audit")
    async def test_updates_account_when_exists(self, mock_audit, mock_settings):
        """Account 已存在时更新记录"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        mock_audit.return_value = None

        db = AsyncMock()

        mock_doctor = MagicMock()
        mock_doctor.id = "doctor_123"
        mock_doctor.tenant_id = "tenant_123"
        mock_doctor.phone = "13700137000"
        mock_doctor.username = "doctor_zhang"
        mock_doctor.password_hash = "hash_doctor"
        mock_doctor.name = "张医生更新"
        mock_doctor.avatar = "new_avatar"
        mock_doctor.gender = 1
        mock_doctor.status = 1
        mock_doctor.last_login_at = None
        mock_doctor.last_login_ip = None
        # Doctor 扩展字段
        mock_doctor.store_id = "store_456"
        mock_doctor.department_id = "dept_456"
        mock_doctor.banner = "banner_url"
        mock_doctor.title = "副主任医师"
        mock_doctor.years_of_experience = 15
        mock_doctor.education = "硕士"
        mock_doctor.graduate_school = "清华大学"
        mock_doctor.license_number = "LIC456"
        mock_doctor.license_image = "lic_img"
        mock_doctor.honors = "荣誉1"
        mock_doctor.schedule_desc = "周一至周六"
        mock_doctor.max_daily_appointments = 40
        mock_doctor.online_consult_enabled = 0
        mock_doctor.online_consult_fee = 100.0
        mock_doctor.page_style = 2
        mock_doctor.promo_video = "video_url"
        mock_doctor.tags = "外科"
        mock_doctor.specialty = "骨科"
        mock_doctor.introduction = "专家简介"
        mock_doctor.is_recommended = 0
        mock_doctor.sort_order = 1
        mock_doctor.use_fee_template = 1
        mock_doctor.deleted_at = None

        mock_account = MagicMock()
        mock_account_doctor = MagicMock()

        db.get = AsyncMock(side_effect=[mock_doctor, mock_account, mock_account_doctor])

        await AccountSyncService.sync_doctor_to_account(db, "doctor_123")

        assert mock_account.name == "张医生更新"
        assert mock_account_doctor.title == "副主任医师"
        assert mock_account_doctor.department_id == "dept_456"
        db.add.assert_not_called()

    @patch("app.common.account_sync.settings")
    async def test_skips_when_doctor_not_found(self, mock_settings):
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        await AccountSyncService.sync_doctor_to_account(db, "nonexistent_id")
        db.add.assert_not_called()

    @patch("app.common.account_sync.settings")
    async def test_exception_does_not_propagate(self, mock_settings):
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        db = AsyncMock()
        db.get = AsyncMock(side_effect=Exception("DB error"))
        await AccountSyncService.sync_doctor_to_account(db, "doctor_123")


# ================================================================
# sync_user_to_account 测试
# ================================================================


@pytest.mark.unit
class TestSyncUserToAccount:
    """测试 User 同步到 Account"""

    @patch("app.common.account_sync.settings")
    async def test_skips_when_dual_write_disabled(self, mock_settings):
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = False
        db = AsyncMock()
        await AccountSyncService.sync_user_to_account(db, "user_123")
        db.get.assert_not_called()

    @patch("app.common.account_sync.settings")
    @patch("app.common.account_sync.set_create_audit")
    async def test_creates_account_when_not_exists(self, mock_audit, mock_settings):
        """Account 不存在时创建新记录"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        mock_audit.return_value = None

        db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user_123"
        mock_user.tenant_id = "tenant_123"
        mock_user.phone = "13800138000"
        mock_user.password_hash = "hash_user"
        mock_user.nickname = "测试用户"
        mock_user.avatar = None
        mock_user.gender = 0
        mock_user.status = 1
        mock_user.openid = "wx_openid_123"
        mock_user.unionid = "wx_unionid_123"
        mock_user.wechat_nickname = "微信昵称"
        mock_user.wechat_avatar = "wx_avatar"
        mock_user.wechat_synced_at = None
        mock_user.points = 100

        db.get = AsyncMock(side_effect=[mock_user, None, None])

        await AccountSyncService.sync_user_to_account(db, "user_123")

        assert db.add.call_count == 2
        db.flush.assert_called()

    @patch("app.common.account_sync.settings")
    @patch("app.common.account_sync.set_update_audit")
    async def test_updates_account_when_exists(self, mock_audit, mock_settings):
        """Account 已存在时更新记录"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        mock_audit.return_value = None

        db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user_123"
        mock_user.tenant_id = "tenant_123"
        mock_user.phone = "13800138000"
        mock_user.password_hash = "hash_user"
        mock_user.nickname = "更新昵称"
        mock_user.avatar = "new_avatar"
        mock_user.gender = 1
        mock_user.status = 1
        mock_user.openid = "wx_openid_123"
        mock_user.unionid = "wx_unionid_123"
        mock_user.wechat_nickname = "新微信昵称"
        mock_user.wechat_avatar = "new_wx_avatar"
        mock_user.wechat_synced_at = None
        mock_user.points = 200

        mock_account = MagicMock()
        mock_account_user = MagicMock()

        db.get = AsyncMock(side_effect=[mock_user, mock_account, mock_account_user])

        await AccountSyncService.sync_user_to_account(db, "user_123")

        assert mock_account.nickname == "更新昵称"
        assert mock_account_user.points == 200
        assert mock_account_user.openid == "wx_openid_123"
        db.add.assert_not_called()

    @patch("app.common.account_sync.settings")
    async def test_skips_when_user_not_found(self, mock_settings):
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        await AccountSyncService.sync_user_to_account(db, "nonexistent_id")
        db.add.assert_not_called()

    @patch("app.common.account_sync.settings")
    async def test_exception_does_not_propagate(self, mock_settings):
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        db = AsyncMock()
        db.get = AsyncMock(side_effect=Exception("DB error"))
        await AccountSyncService.sync_user_to_account(db, "user_123")


# ================================================================
# Upsert 逻辑验证
# ================================================================


@pytest.mark.unit
class TestUpsertLogic:
    """测试 upsert 逻辑：已存在时更新，不存在时创建"""

    @patch("app.common.account_sync.settings")
    @patch("app.common.account_sync.set_create_audit")
    async def test_create_path_calls_db_add(self, mock_audit, mock_settings):
        """不存在时走 db.add 创建路径"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        mock_audit.return_value = None

        db = AsyncMock()
        mock_entity = MagicMock()
        mock_entity.id = "id_123"
        mock_entity.tenant_id = "t_123"
        mock_entity.phone = "13800000000"
        mock_entity.password_hash = "h"
        mock_entity.name = "n"
        mock_entity.avatar = None
        mock_entity.status = 1
        mock_entity.last_login_at = None
        mock_entity.last_login_ip = None
        # User 特有字段
        mock_entity.nickname = "nn"
        mock_entity.gender = 0
        mock_entity.openid = None
        mock_entity.unionid = None
        mock_entity.wechat_nickname = None
        mock_entity.wechat_avatar = None
        mock_entity.wechat_synced_at = None
        mock_entity.points = 0

        # Admin/Doctor 特有字段（不会被访问，但防止 AttributeError）
        mock_entity.username = "u"
        mock_entity.role_id = None
        mock_entity.current_store_id = None
        mock_entity.email = None

        db.get = AsyncMock(side_effect=[mock_entity, None, None])

        await AccountSyncService.sync_user_to_account(db, "id_123")
        assert db.add.call_count == 2  # Account + AccountUser

    @patch("app.common.account_sync.settings")
    @patch("app.common.account_sync.set_update_audit")
    async def test_update_path_does_not_call_db_add(self, mock_audit, mock_settings):
        """已存在时走更新路径，不调用 db.add"""
        mock_settings.ACCOUNT_DUAL_WRITE_ENABLED = True
        mock_audit.return_value = None

        db = AsyncMock()
        mock_entity = MagicMock()
        mock_entity.id = "id_123"
        mock_entity.tenant_id = "t_123"
        mock_entity.phone = "13800000000"
        mock_entity.password_hash = "h"
        mock_entity.name = "n"
        mock_entity.avatar = None
        mock_entity.status = 1
        mock_entity.last_login_at = None
        mock_entity.last_login_ip = None
        mock_entity.nickname = "nn"
        mock_entity.gender = 0
        mock_entity.openid = None
        mock_entity.unionid = None
        mock_entity.wechat_nickname = None
        mock_entity.wechat_avatar = None
        mock_entity.wechat_synced_at = None
        mock_entity.points = 0
        mock_entity.username = "u"

        mock_account = MagicMock()
        mock_account_user = MagicMock()

        db.get = AsyncMock(side_effect=[mock_entity, mock_account, mock_account_user])

        await AccountSyncService.sync_user_to_account(db, "id_123")
        db.add.assert_not_called()
