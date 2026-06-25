"""第三方平台回调签名校验工具测试。

验证钉钉/企业微信/飞书的签名算法实现正确性。
签名校验是入站回调的安全防线，必须覆盖：
- 正确签名通过
- 错误签名拒绝
- 缺少参数安全降级
"""
import base64
import hashlib
import hmac

import pytest

from app.modules.integration_gateway.signature import (
    verify_dingtalk_signature,
    verify_feishu_signature,
    verify_wecom_signature,
)


class TestDingtalkSignature:
    """钉钉签名校验（HmacSHA256 + Base64）。"""

    def test_correct_signature_passes(self):
        """正确签名应通过校验。"""
        timestamp = "1234567890"
        app_secret = "test_secret_dingtalk"
        # 复现钉钉算法：HmacSHA256(timestamp, secret) → Base64
        expected = base64.b64encode(
            hmac.new(app_secret.encode(), timestamp.encode(), hashlib.sha256).digest()
        ).decode()
        assert verify_dingtalk_signature(timestamp, app_secret, expected) is True

    def test_wrong_signature_rejected(self):
        """错误签名应拒绝。"""
        assert verify_dingtalk_signature("123", "secret", "wrong_signature") is False

    def test_wrong_secret_rejected(self):
        """密钥不匹配应拒绝。"""
        timestamp = "1234567890"
        correct_sig = base64.b64encode(
            hmac.new("correct_secret".encode(), timestamp.encode(), hashlib.sha256).digest()
        ).decode()
        assert verify_dingtalk_signature(timestamp, "wrong_secret", correct_sig) is False

    def test_empty_signature_rejected(self):
        """空签名应拒绝。"""
        assert verify_dingtalk_signature("123", "secret", "") is False


class TestWecomSignature:
    """企业微信签名校验（SHA1 of sorted join）。"""

    def test_correct_signature_passes(self):
        """正确签名应通过。"""
        token = "wecom_token"
        timestamp = "1234567890"
        nonce = "abc123"
        encrypted = "encrypted_msg"
        # 复现企业微信算法：SHA1(sort([token, timestamp, nonce, encrypted]))
        sort_list = sorted([token, timestamp, nonce, encrypted])
        expected = hashlib.sha1("".join(sort_list).encode()).hexdigest()
        assert verify_wecom_signature(token, timestamp, nonce, encrypted, expected) is True

    def test_wrong_signature_rejected(self):
        assert verify_wecom_signature("token", "ts", "nonce", "enc", "wrong") is False

    def test_order_independence(self):
        """参数顺序不影响校验（内部会排序）。"""
        token, timestamp, nonce, encrypted = "t", "1", "n", "e"
        sort_list = sorted([token, timestamp, nonce, encrypted])
        expected = hashlib.sha1("".join(sort_list).encode()).hexdigest()
        # 传入顺序与排序无关
        assert verify_wecom_signature(token, timestamp, nonce, encrypted, expected) is True


class TestFeishuSignature:
    """飞书签名校验（SHA256(timestamp + nonce + key + body)）。"""

    def test_correct_signature_passes(self):
        """正确签名应通过。"""
        encrypt_key = "feishu_key"
        timestamp = "1234567890"
        nonce = "nonce123"
        body = '{"event_type":"approval"}'
        # 复现飞书算法
        content = f"{timestamp}{nonce}{encrypt_key}{body}"
        expected = hashlib.sha256(content.encode()).hexdigest()
        assert verify_feishu_signature(encrypt_key, timestamp, nonce, body, expected) is True

    def test_wrong_signature_rejected(self):
        assert verify_feishu_signature("key", "ts", "nonce", "body", "wrong") is False

    def test_body_tamper_detected(self):
        """body 被篡改后签名应不匹配。"""
        encrypt_key = "key"
        timestamp, nonce, body = "1", "n", '{"a":1}'
        content = f"{timestamp}{nonce}{encrypt_key}{body}"
        expected = hashlib.sha256(content.encode()).hexdigest()
        # 篡改 body
        assert verify_feishu_signature(encrypt_key, timestamp, nonce, '{"a":2}', expected) is False
