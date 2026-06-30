"""
敏感数据加密模块

提供 AES-256-GCM 加密/解密、SHA-256 哈希、脱敏函数。
用于 patient.id_card 和 patient.phone 的加密存储。

加密策略：
- AES-256-GCM：认证加密，提供机密性 + 完整性
- SHA-256 哈希：用于搜索/去重（不可逆）
- 脱敏函数：用于 API 返回（前3后4，中间用*替换）

密钥管理：
- 生产环境：KMS（阿里云 KMS / 腾讯云 KMS）
- 本地开发：环境变量 ENCRYPTION_KEY（32 字节 base64）
"""
import base64
import hashlib
import logging
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# 默认测试密钥（仅用于本地开发，生产环境必须使用 KMS）
_DEV_KEY = "2O8Qodgdf11Az8hGbvX7Af4TU1BEmMQNL1x6OsfzdRw="


def _get_encryption_key() -> bytes:
    """获取加密密钥

    优先级：
    1. 环境变量 ENCRYPTION_KEY（base64 编码的 32 字节密钥）
    2. 默认测试密钥（仅开发环境）

    Returns:
        32 字节密钥
    """
    key_b64 = os.getenv("ENCRYPTION_KEY", _DEV_KEY)
    key = base64.b64decode(key_b64)
    if len(key) != 32:
        raise ValueError(f"ENCRYPTION_KEY 必须是 32 字节（当前 {len(key)} 字节）")
    return key


def encrypt(plaintext: str | None) -> bytes | None:
    """AES-256-GCM 加密

    Args:
        plaintext: 明文字符串

    Returns:
        加密后的字节（nonce + ciphertext + tag），明文为 None 时返回 None
    """
    if plaintext is None:
        return None

    key = _get_encryption_key()
    aesgcm = AESGCM(key)

    # 12 字节随机 nonce（GCM 推荐）
    nonce = os.urandom(12)

    # 加密（GCM 自带认证标签）
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

    # 返回 nonce + ciphertext（nonce 在前，解密时先提取）
    return nonce + ciphertext


def decrypt(encrypted: bytes | None) -> str | None:
    """AES-256-GCM 解密

    Args:
        encrypted: encrypt() 返回的字节

    Returns:
        解密后的明文字符串，加密数据为 None 时返回 None
    """
    if encrypted is None:
        return None

    key = _get_encryption_key()
    aesgcm = AESGCM(key)

    # 提取 nonce（前 12 字节）和 ciphertext
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        logger.error(f"解密失败: {e}")
        return None


def hash_value(plaintext: str | None) -> str | None:
    """SHA-256 哈希（用于搜索/去重，不可逆）

    Args:
        plaintext: 明文字符串

    Returns:
        十六进制哈希字符串，明文为 None 时返回 None
    """
    if plaintext is None:
        return None
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def mask_id_card(id_card: str | None) -> str | None:
    """身份证号脱敏：保留前3位和后4位，中间用*替换

    Args:
        id_card: 身份证号

    Returns:
        脱敏后的身份证号，如 "110***********1234"
        原始值为 None 或长度不足时返回原值
    """
    if not id_card or len(id_card) < 8:
        return id_card
    return id_card[:3] + "*" * (len(id_card) - 7) + id_card[-4:]


def mask_phone(phone: str | None) -> str | None:
    """手机号脱敏：保留前3位和后4位，中间用*替换

    Args:
        phone: 手机号

    Returns:
        脱敏后的手机号，如 "138****5678"
        原始值为 None 或长度不足时返回原值
    """
    if not phone or len(phone) < 7:
        return phone
    return phone[:3] + "*" * (len(phone) - 7) + phone[-4:]


# 旧密钥支持（密钥轮换时使用）
def _get_previous_key() -> bytes | None:
    """获取旧密钥（用于密钥轮换期间解密历史数据）"""
    key_b64 = os.getenv("ENCRYPTION_KEY_PREVIOUS")
    if not key_b64:
        return None
    key = base64.b64decode(key_b64)
    if len(key) != 32:
        logger.warning(f"ENCRYPTION_KEY_PREVIOUS 长度错误（{len(key)} 字节），忽略")
        return None
    return key


def decrypt_with_fallback(encrypted: bytes | None) -> str | None:
    """解密（支持旧密钥 fallback）

    先用当前密钥解密，失败则用旧密钥尝试。
    适用于密钥轮换期间的历史数据读取。

    Args:
        encrypted: encrypt() 返回的字节

    Returns:
        解密后的明文字符串
    """
    if encrypted is None:
        return None

    # 先尝试当前密钥
    result = decrypt(encrypted)
    if result is not None:
        return result

    # 尝试旧密钥
    prev_key = _get_previous_key()
    if prev_key is None:
        return None

    try:
        aesgcm = AESGCM(prev_key)
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        logger.error(f"旧密钥解密也失败: {e}")
        return None
