"""上传模块纯函数单元测试

覆盖:
- validate_image() 内容类型 + 扩展名校验
- _generate_thumbnail_key() 路径拼接
- _extract_tenant_id_from_key() 租户提取
- _validate_tenant_access() 权限校验
- _resolve_local_file() 路径穿越防护
- _get_content_type_from_ext() MIME 映射
- 常量: ALLOWED_IMAGE_TYPES, MAX_FILE_SIZE
"""
import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.modules.upload.router import (
    ALLOWED_IMAGE_TYPES,
    MAX_FILE_SIZE,
    validate_image,
    _generate_thumbnail_key,
    _extract_tenant_id_from_key,
    _validate_tenant_access,
    _get_content_type_from_ext,
    _resolve_local_file,
)


@pytest.mark.unit
class TestConstants:
    """测试常量定义"""

    def test_allowed_image_types(self):
        assert "image/jpeg" in ALLOWED_IMAGE_TYPES
        assert "image/png" in ALLOWED_IMAGE_TYPES
        assert "image/gif" in ALLOWED_IMAGE_TYPES
        assert "image/webp" in ALLOWED_IMAGE_TYPES
        assert "image/svg+xml" in ALLOWED_IMAGE_TYPES
        assert "jpg" in ALLOWED_IMAGE_TYPES["image/jpeg"]
        assert "jpeg" in ALLOWED_IMAGE_TYPES["image/jpeg"]

    def test_max_file_size(self):
        assert MAX_FILE_SIZE == 5 * 1024 * 1024


@pytest.mark.unit
class TestValidateImage:
    """测试图片校验"""

    def _make_upload_file(self, content_type: str, filename: str = "test.jpg"):
        f = MagicMock()
        f.content_type = content_type
        f.filename = filename
        return f

    def test_valid_jpeg(self):
        f = self._make_upload_file("image/jpeg", "photo.jpg")
        validate_image(f)  # 不抛异常

    def test_valid_png(self):
        f = self._make_upload_file("image/png", "screenshot.png")
        validate_image(f)

    def test_valid_svg(self):
        f = self._make_upload_file("image/svg+xml", "icon.svg")
        validate_image(f)

    def test_invalid_content_type(self):
        f = self._make_upload_file("application/pdf", "doc.pdf")
        with pytest.raises(HTTPException) as exc_info:
            validate_image(f)
        assert exc_info.value.status_code == 400
        assert "不支持的图片格式" in exc_info.value.detail

    def test_invalid_extension(self):
        f = self._make_upload_file("image/jpeg", "virus.exe")
        with pytest.raises(HTTPException) as exc_info:
            validate_image(f)
        assert exc_info.value.status_code == 400
        assert "不支持的文件格式" in exc_info.value.detail

    def test_no_filename(self):
        """没有文件名时不校验扩展名"""
        f = self._make_upload_file("image/jpeg", filename=None)
        validate_image(f)  # 不抛异常

    def test_filename_without_extension(self):
        """文件名无扩展名时不校验"""
        f = self._make_upload_file("image/jpeg", "noext")
        validate_image(f)

    def test_extension_case_insensitive(self):
        """扩展名大小写不敏感"""
        f = self._make_upload_file("image/jpeg", "photo.JPG")
        validate_image(f)

    def test_double_extension(self):
        """双扩展名取最后一个"""
        f = self._make_upload_file("image/jpeg", "photo.tar.jpg")
        validate_image(f)

        f2 = self._make_upload_file("image/jpeg", "photo.jpg.exe")
        with pytest.raises(HTTPException):
            validate_image(f2)


@pytest.mark.unit
class TestGenerateThumbnailKey:
    """测试缩略图 key 生成"""

    def test_with_folder(self):
        result = _generate_thumbnail_key("tenants/t1/images/photo.jpg", "small")
        assert result == "tenants/t1/images/thumb_small_photo.jpg"

    def test_without_folder(self):
        result = _generate_thumbnail_key("photo.jpg", "medium")
        assert result == "thumb_medium_photo.jpg"

    def test_nested_folder(self):
        result = _generate_thumbnail_key("a/b/c/image.png", "large")
        assert result == "a/b/c/thumb_large_image.png"


@pytest.mark.unit
class TestExtractTenantIdFromKey:
    """测试从存储 key 提取租户 ID"""

    def test_tenant_key(self):
        assert _extract_tenant_id_from_key("tenants/abc-123/images/photo.jpg") == "abc-123"

    def test_tenant_key_no_subfolder(self):
        assert _extract_tenant_id_from_key("tenants/tid-1/file.jpg") == "tid-1"

    def test_platform_key(self):
        assert _extract_tenant_id_from_key("platform/logo.png") is None

    def test_empty_key(self):
        assert _extract_tenant_id_from_key("") is None

    def test_no_tenants_prefix(self):
        assert _extract_tenant_id_from_key("images/photo.jpg") is None


@pytest.mark.unit
class TestValidateTenantAccess:
    """测试租户文件访问校验"""

    def test_platform_file_allowed(self):
        """非租户目录的文件，任何人可操作"""
        admin = {"tenant_id": "t1"}
        _validate_tenant_access("platform/logo.png", admin)  # 不抛异常

    def test_platform_admin_allowed(self):
        """平台管理员（无 tenant_id）可操作任何文件"""
        admin = {"tenant_id": None}
        _validate_tenant_access("tenants/t1/images/photo.jpg", admin)

    def test_matching_tenant_allowed(self):
        """租户操作自己的文件"""
        admin = {"tenant_id": "t1"}
        _validate_tenant_access("tenants/t1/images/photo.jpg", admin)

    def test_cross_tenant_forbidden(self):
        """租户操作别人的文件 → 403"""
        admin = {"tenant_id": "t1"}
        with pytest.raises(HTTPException) as exc_info:
            _validate_tenant_access("tenants/t2/images/photo.jpg", admin)
        assert exc_info.value.status_code == 403
        assert "无权操作其他租户" in exc_info.value.detail

    def test_tenant_id_type_mismatch(self):
        """tenant_id 类型不同（int vs str）仍能匹配"""
        admin = {"tenant_id": 123}
        _validate_tenant_access("tenants/123/images/photo.jpg", admin)


@pytest.mark.unit
class TestGetContentTypeFromExt:
    """测试 MIME 类型推断"""

    def test_known_extensions(self):
        assert _get_content_type_from_ext("photo.jpg") == "image/jpeg"
        assert _get_content_type_from_ext("photo.jpeg") == "image/jpeg"
        assert _get_content_type_from_ext("photo.png") == "image/png"
        assert _get_content_type_from_ext("photo.gif") == "image/gif"
        assert _get_content_type_from_ext("photo.webp") == "image/webp"
        assert _get_content_type_from_ext("icon.svg") == "image/svg+xml"

    def test_unknown_extension(self):
        assert _get_content_type_from_ext("file.pdf") == "application/octet-stream"
        assert _get_content_type_from_ext("file.txt") == "application/octet-stream"

    def test_no_extension(self):
        assert _get_content_type_from_ext("noext") == "application/octet-stream"

    def test_case_insensitive(self):
        assert _get_content_type_from_ext("photo.JPG") == "image/jpeg"
        assert _get_content_type_from_ext("photo.PNG") == "image/png"


@pytest.mark.unit
class TestResolveLocalFile:
    """测试本地文件路径解析 + 路径穿越防护"""

    def test_path_traversal_blocked(self):
        """路径穿越被阻止"""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LOCAL_UPLOAD_DIR = "/tmp/uploads"
            result = _resolve_local_file("../../etc/passwd")
        assert result is None

    def test_absolute_escape_blocked(self):
        """绝对路径逃逸被阻止"""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LOCAL_UPLOAD_DIR = "/tmp/uploads"
            result = _resolve_local_file("/etc/passwd")
        assert result is None

    def test_nonexistent_file(self):
        """不存在的文件返回 None"""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LOCAL_UPLOAD_DIR = "/tmp/uploads"
            result = _resolve_local_file("images/nonexistent.jpg")
        assert result is None

    def test_valid_file(self, tmp_path):
        """正常文件返回路径"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        test_file = upload_dir / "images" / "photo.jpg"
        test_file.parent.mkdir(parents=True)
        test_file.write_bytes(b"fake image")

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LOCAL_UPLOAD_DIR = str(upload_dir)
            result = _resolve_local_file("images/photo.jpg")

        assert result is not None
        assert result == test_file.resolve()

    def test_directory_traversal_with_dotdot(self, tmp_path):
        """使用 .. 尝试穿越到父目录"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        # 在 upload_dir 的父目录放一个文件
        secret = tmp_path / "secret.txt"
        secret.write_text("secret")

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LOCAL_UPLOAD_DIR = str(upload_dir)
            result = _resolve_local_file("../secret.txt")

        assert result is None
