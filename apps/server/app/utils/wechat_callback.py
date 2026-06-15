"""微信回调签名校验工具。

支持微信小程序审核回调的 AES 解密和签名校验。
"""

import base64
import hashlib
import hmac
import json
import logging
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

logger = logging.getLogger(__name__)


class WeChatCallbackError(Exception):
    """微信回调校验异常。"""
    pass


def _derive_aes_key(app_secret: str) -> bytes:
    """从 AppSecret 派生 AES 密钥 (43 字符 base64 -> 32 字节)。

    微信小程序使用 AppSecret 的前 43 个字符作为 base64 编码的 AES 密钥。
    """
    if not app_secret:
        raise WeChatCallbackError("AppSecret 不能为空")

    # 取前 43 个字符并补全 base64 padding
    key_str = app_secret[:43]
    # base64 要求长度是 4 的倍数，补 '='
    padding = 4 - len(key_str) % 4
    if padding != 4:
        key_str += "=" * padding

    try:
        key = base64.b64decode(key_str, validate=False)
        # 如果解码后长度不是 32，尝试使用 hashlib 生成确定性密钥
        if len(key) != 32:
            # 使用 SHA-256 从原始字符串生成 32 字节密钥
            key = hashlib.sha256(app_secret[:43].encode("utf-8")).digest()
        return key
    except Exception as e:
        raise WeChatCallbackError(f"AES 密钥派生失败: {e}")


def decrypt_callback_data(
    encrypted_data: str,
    app_secret: str,
) -> dict[str, Any]:
    """解密微信回调数据。

    微信小程序审核回调使用 AES-256-CBC 加密，解密后为 JSON 格式。

    Args:
        encrypted_data: Base64 编码的加密数据
        app_secret: 微信小程序 AppSecret

    Returns:
        解密后的 JSON 数据字典

    Raises:
        WeChatCallbackError: 解密失败或数据格式错误
    """
    try:
        key = _derive_aes_key(app_secret)

        # 解码 base64
        encrypted_bytes = base64.b64decode(encrypted_data)

        # 提取 IV (前 16 字节) 和密文
        if len(encrypted_bytes) < 16:
            raise WeChatCallbackError("加密数据长度不足")

        iv = encrypted_bytes[:16]
        ciphertext = encrypted_bytes[16:]

        # AES-256-CBC 解密
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()

        # PKCS7 去填充
        unpadder = PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()

        # 解析 JSON
        data = json.loads(decrypted.decode("utf-8"))
        return data

    except WeChatCallbackError:
        raise
    except json.JSONDecodeError as e:
        raise WeChatCallbackError(f"回调数据 JSON 解析失败: {e}")
    except Exception as e:
        raise WeChatCallbackError(f"回调数据解密失败: {e}")


def verify_callback_signature(
    timestamp: str,
    nonce: str,
    encrypt: str,
    signature: str,
    token: str,
) -> bool:
    """验证微信回调消息签名。

    微信服务器发送回调时会在 URL 参数中携带 signature，
    使用 SHA1(sort(token, timestamp, nonce, encrypt)) 计算。

    Args:
        timestamp: 时间戳
        nonce: 随机字符串
        encrypt: 加密的消息体
        signature: 微信传来的签名
        token: 微信后台配置的 Token

    Returns:
        签名是否有效
    """
    if not all([timestamp, nonce, encrypt, signature, token]):
        return False

    # 按字典序排序并拼接
    items = sorted([token, timestamp, nonce, encrypt])
    raw_string = "".join(items)

    # SHA1 哈希
    hash_obj = hashlib.sha1(raw_string.encode("utf-8"))
    computed_signature = hash_obj.hexdigest()

    return hmac.compare_digest(computed_signature, signature)


def parse_callback_request(
    body: bytes,
    query_params: dict[str, str],
    app_secret: str,
    token: str | None = None,
) -> dict[str, Any]:
    """解析并验证微信回调请求。

    完整流程：
    1. 验证 URL 参数中的签名 (如果提供了 token)
    2. 解密请求体

    Args:
        body: 原始请求体 (JSON 格式，包含 encrypt 字段)
        query_params: URL 查询参数
        app_secret: 微信小程序 AppSecret
        token: 微信后台配置的 Token (可选，用于签名验证)

    Returns:
        解密后的回调数据

    Raises:
        WeChatCallbackError: 校验失败或解密失败
    """
    try:
        request_data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise WeChatCallbackError(f"请求体解析失败: {e}")

    # 如果提供了 token，验证签名
    if token:
        signature = query_params.get("signature", "")
        timestamp = query_params.get("timestamp", "")
        nonce = query_params.get("nonce", "")
        encrypt = request_data.get("encrypt", "")

        if not verify_callback_signature(timestamp, nonce, encrypt, signature, token):
            logger.warning("微信回调签名校验失败: timestamp=%s, nonce=%s", timestamp, nonce)
            raise WeChatCallbackError("回调签名校验失败")

    # 解密数据
    encrypt_data = request_data.get("encrypt")
    if not encrypt_data:
        raise WeChatCallbackError("请求体缺少 encrypt 字段")

    decrypted = decrypt_callback_data(encrypt_data, app_secret)
    return decrypted
