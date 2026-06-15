"""微信回调签名校验工具测试。"""

import base64
import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend

from app.utils.wechat_callback import (
    WeChatCallbackError,
    _derive_aes_key,
    decrypt_callback_data,
    verify_callback_signature,
)


class TestDeriveAESKey:
    """测试 AES 密钥派生。"""

    def test_derive_key_success(self):
        """正常 AppSecret 派生密钥。"""
        app_secret = "a" * 43 + "="  # 44 字符，模拟 base64 编码
        key = _derive_aes_key(app_secret)
        assert len(key) == 32

    def test_derive_key_empty_secret(self):
        """空 AppSecret 抛出异常。"""
        with pytest.raises(WeChatCallbackError, match="AppSecret 不能为空"):
            _derive_aes_key("")

    def test_derive_key_short_secret(self):
        """短 AppSecret 派生密钥（自动补全 padding）。"""
        # 40 字符是 4 的倍数，可以正常 base64 解码
        app_secret = "abcdefghij" * 4  # 40 字符
        key = _derive_aes_key(app_secret)
        assert len(key) == 32


class TestVerifyCallbackSignature:
    """测试回调签名验证。"""

    def _make_signature(self, token: str, timestamp: str, nonce: str, encrypt: str) -> str:
        """生成测试签名。"""
        items = sorted([token, timestamp, nonce, encrypt])
        raw_string = "".join(items)
        return hashlib.sha1(raw_string.encode("utf-8")).hexdigest()

    def test_verify_success(self):
        """签名验证成功。"""
        token = "test_token"
        timestamp = "1234567890"
        nonce = "abc123"
        encrypt = "encrypted_data"

        signature = self._make_signature(token, timestamp, nonce, encrypt)

        assert verify_callback_signature(timestamp, nonce, encrypt, signature, token) is True

    def test_verify_wrong_signature(self):
        """签名不匹配。"""
        token = "test_token"
        timestamp = "1234567890"
        nonce = "abc123"
        encrypt = "encrypted_data"
        wrong_signature = "wrong_signature"

        assert verify_callback_signature(timestamp, nonce, encrypt, wrong_signature, token) is False

    def test_verify_missing_params(self):
        """缺少必要参数。"""
        assert verify_callback_signature("", "123", "enc", "sig", "token") is False
        assert verify_callback_signature("123", "", "enc", "sig", "token") is False
        assert verify_callback_signature("123", "456", "", "sig", "token") is False
        assert verify_callback_signature("123", "456", "789", "", "token") is False
        assert verify_callback_signature("123", "456", "789", "sig", "") is False


class TestDecryptCallbackData:
    """测试回调数据解密。"""

    def _encrypt_data(self, data: dict, app_secret: str) -> str:
        """辅助方法：加密数据用于测试。"""
        key = _derive_aes_key(app_secret)
        iv = b"\x00" * 16  # 测试用固定 IV

        # JSON 编码
        json_data = json.dumps(data).encode("utf-8")

        # PKCS7 填充
        padder = PKCS7(128).padder()
        padded_data = padder.update(json_data) + padder.finalize()

        # AES-256-CBC 加密
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # 返回 base64 编码 (IV + 密文)
        return base64.b64encode(iv + ciphertext).decode("utf-8")

    def test_decrypt_success(self):
        """解密成功。"""
        app_secret = "a" * 43 + "="
        original_data = {"auditid": "audit_123", "status": 0}

        encrypted = self._encrypt_data(original_data, app_secret)
        result = decrypt_callback_data(encrypted, app_secret)

        assert result["auditid"] == "audit_123"
        assert result["status"] == 0

    def test_decrypt_wrong_key(self):
        """密钥错误解密失败。"""
        app_secret = "a" * 43 + "="
        wrong_secret = "b" * 43 + "="
        original_data = {"auditid": "audit_123", "status": 0}

        encrypted = self._encrypt_data(original_data, app_secret)

        with pytest.raises(WeChatCallbackError, match="解密失败"):
            decrypt_callback_data(encrypted, wrong_secret)

    def test_decrypt_invalid_base64(self):
        """无效的 base64 数据。"""
        with pytest.raises(WeChatCallbackError):
            decrypt_callback_data("not_valid_base64!!!", "secret")

    def test_decrypt_empty_data(self):
        """空数据。"""
        with pytest.raises(WeChatCallbackError):
            decrypt_callback_data("", "secret")

    def test_decrypt_too_short_data(self):
        """数据长度不足。"""
        # 只有 10 字节的 base64 数据
        short_data = base64.b64encode(b"\x00" * 10).decode("utf-8")
        with pytest.raises(WeChatCallbackError):
            decrypt_callback_data(short_data, "secret")
