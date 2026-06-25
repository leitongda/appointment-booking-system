"""第三方平台审批回调签名校验工具。

各平台回调签名机制不同，此处统一封装校验逻辑。
钉钉/企业微信/飞书均支持通过应用加密配置接收事件回调，
此处实现基础的签名校验，生产环境需配置对应的加密密钥。
"""
from __future__ import annotations

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def verify_dingtalk_signature(timestamp: str, app_secret: str, signature: str) -> bool:
    """钉钉事件回调签名校验。

    钉钉签名算法：HmacSHA256(timestamp, app_secret) → Base64。
    """
    try:
        string_to_sign = timestamp
        hmac_code = hmac.new(
            app_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        import base64

        computed = base64.b64encode(hmac_code).decode("utf-8")
        return hmac.compare_digest(computed, signature)
    except Exception:
        logger.exception("dingtalk_signature_verify_failed")
        return False


def verify_wecom_signature(token: str, timestamp: str, nonce: str, encrypted_msg: str, signature: str) -> bool:
    """企业微信回调签名校验。

    企业微信签名算法：SHA1(sort([token, timestamp, nonce, encrypted_msg]))。
    """
    try:
        sort_list = sorted([token, timestamp, nonce, encrypted_msg])
        sha1 = hashlib.sha1("".join(sort_list).encode("utf-8")).hexdigest()
        return hmac.compare_digest(sha1, signature)
    except Exception:
        logger.exception("wecom_signature_verify_failed")
        return False


def verify_feishu_signature(encrypt_key: str, timestamp: str, nonce: str, body: str, signature: str) -> bool:
    """飞书事件回调签名校验。

    飞书签名算法：SHA256(timestamp + nonce + encrypt_key + body)。
    """
    try:
        content = f"{timestamp}{nonce}{encrypt_key}{body}"
        computed = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return hmac.compare_digest(computed, signature)
    except Exception:
        logger.exception("feishu_signature_verify_failed")
        return False
