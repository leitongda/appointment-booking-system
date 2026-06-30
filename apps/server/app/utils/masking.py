"""
敏感数据脱敏工具

提供统一的脱敏函数，用于 API 返回时隐藏敏感信息。
所有角色（包括超管）都只能看到脱敏值，不允许导出明文。
"""
from app.core.encryption import mask_id_card, mask_phone, decrypt, decrypt_with_fallback


def get_masked_id_card(encrypted_data: bytes | None, fallback_plaintext: str | None = None) -> str | None:
    """获取脱敏的身份证号

    优先从加密列解密并脱敏，fallback 到明文列脱敏（迁移期间兼容）。

    Args:
        encrypted_data: 加密后的身份证号数据
        fallback_plaintext: 明文 fallback（迁移期间使用）

    Returns:
        脱敏后的身份证号，如 "110***********1234"
    """
    if encrypted_data:
        plaintext = decrypt_with_fallback(encrypted_data)
        if plaintext:
            return mask_id_card(plaintext)

    # fallback 到明文（迁移期间兼容）
    if fallback_plaintext:
        return mask_id_card(fallback_plaintext)

    return None


def get_masked_phone(encrypted_data: bytes | None, fallback_plaintext: str | None = None) -> str | None:
    """获取脱敏的手机号

    优先从加密列解密并脱敏，fallback 到明文列脱敏（迁移期间兼容）。

    Args:
        encrypted_data: 加密后的手机号数据
        fallback_plaintext: 明文 fallback（迁移期间使用）

    Returns:
        脱敏后的手机号，如 "138****5678"
    """
    if encrypted_data:
        plaintext = decrypt_with_fallback(encrypted_data)
        if plaintext:
            return mask_phone(plaintext)

    # fallback 到明文（迁移期间兼容）
    if fallback_plaintext:
        return mask_phone(fallback_plaintext)

    return None


def is_masked_value(value: str | None) -> bool:
    """检查值是否为脱敏值（包含 * 号）

    Args:
        value: 待检查的值

    Returns:
        True 表示是脱敏值，应跳过保存
    """
    if not value:
        return False
    return '*' in value


def get_decrypted_for_edit(encrypted_data: bytes | None, fallback_plaintext: str | None = None) -> str | None:
    """获取解密值（仅用于编辑表单回填）

    注意：此函数返回明文，仅用于需要用户编辑的场景。
    编辑表单应显示脱敏值，提示用户重新输入。

    Args:
        encrypted_data: 加密后的数据
        fallback_plaintext: 明文 fallback

    Returns:
        明文值（仅在编辑场景使用）
    """
    if encrypted_data:
        plaintext = decrypt_with_fallback(encrypted_data)
        if plaintext:
            return plaintext

    return fallback_plaintext
