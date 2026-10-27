"""PUBLIC_MEDIA_BASE_URL 出口/入口转换的单测（app/schemas/media.py）。

出口 publicize_media：/uploads/ 相对路径 → 公网绝对 URL（中间件统一调用）；
入口 normalize_media：客户端回写的「基址 + /uploads/」还原为相对路径
（BaseRequestSchema 统一校验器 + 个别直连 BaseModel 请求模型显式校验器）。
基址未配置时两者均为 no-op。
"""
import json

import pytest

from app.schemas.media import normalize_media, publicize_media


@pytest.fixture
def media_base(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.PUBLIC_MEDIA_BASE_URL", "https://yy.aicm.online/")


@pytest.fixture
def no_base(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.PUBLIC_MEDIA_BASE_URL", "")


class TestPublicizeMedia:
    def test_noop_when_base_empty(self, no_base):
        data = {"avatar": "/uploads/a.png"}
        assert publicize_media(data) == data

    def test_string(self, media_base):
        assert publicize_media("/uploads/doctor/a.jpg") == "https://yy.aicm.online/uploads/doctor/a.jpg"

    def test_list_and_nested_dict(self, media_base):
        data = {"user": {"avatar": "/uploads/a.png"}, "tags": ["/uploads/b.png", "hello"]}
        assert publicize_media(data) == {
            "user": {"avatar": "https://yy.aicm.online/uploads/a.png"},
            "tags": ["https://yy.aicm.online/uploads/b.png", "hello"],
        }

    def test_absolute_url_untouched(self, media_base):
        url = "https://cdn.example.com/x.png"
        assert publicize_media(url) == url

    def test_non_upload_path_untouched(self, media_base):
        assert publicize_media("/api/v1/doctors") == "/api/v1/doctors"

    def test_json_encoded_list_string(self, media_base):
        # department.intro_images：JSON 编码的图片路径列表
        raw = json.dumps(["/uploads/1.png", "/uploads/2.png"])
        out = publicize_media(raw)
        assert json.loads(out) == ["https://yy.aicm.online/uploads/1.png", "https://yy.aicm.online/uploads/2.png"]

    def test_plain_text_with_bracket_untouched(self, media_base):
        text = "[备忘] 待办清单"
        assert publicize_media(text) == text


class TestNormalizeMedia:
    def test_noop_when_base_empty(self, no_base):
        data = {"avatar": "https://yy.aicm.online/uploads/a.png"}
        assert normalize_media(data) == data

    def test_strips_base(self, media_base):
        data = {"avatar": "https://yy.aicm.online/uploads/a.png"}
        assert normalize_media(data) == {"avatar": "/uploads/a.png"}

    def test_relative_untouched(self, media_base):
        assert normalize_media({"avatar": "/uploads/a.png"}) == {"avatar": "/uploads/a.png"}

    def test_foreign_base_untouched(self, media_base):
        # 别的域名的绝对 URL 不动
        assert normalize_media({"avatar": "https://evil.com/uploads/a.png"}) == {
            "avatar": "https://evil.com/uploads/a.png"
        }

    def test_list(self, media_base):
        data = ["https://yy.aicm.online/uploads/a.png", "/uploads/b.png"]
        assert normalize_media(data) == ["/uploads/a.png", "/uploads/b.png"]

    def test_json_encoded_list_string(self, media_base):
        raw = json.dumps(["https://yy.aicm.online/uploads/1.png"])
        assert json.loads(normalize_media(raw)) == ["/uploads/1.png"]


class TestRoundTrip:
    def test_publicize_then_normalize_is_identity(self, media_base):
        original = {
            "avatar": "/uploads/a.png",
            "images": ["/uploads/b.png"],
            "intro_images": json.dumps(["/uploads/c.png"]),
            "content": "普通文本",
        }
        assert normalize_media(publicize_media(original)) == original
