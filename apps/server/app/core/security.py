import base64
import json
import logging
import os
from datetime import datetime, timedelta

import bcrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# RSA 密钥缓存
_rsa_private_key = None
_rsa_public_key = None
_rsa_public_key_pem = None

# 开发环境密钥对文件路径
_RSA_KEYS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '.keys', 'rsa.json')


def generate_rsa_key_pair() -> tuple[bytes, bytes]:
    """生成 RSA 密钥对"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return private_pem, public_pem


def _load_keys_from_file() -> tuple[bytes | None, bytes | None]:
    """从本地文件加载密钥对（开发环境）"""
    if not os.path.exists(_RSA_KEYS_FILE):
        return None, None
    try:
        with open(_RSA_KEYS_FILE) as f:
            keys = json.load(f)
        return keys['private'].encode(), keys['public'].encode()
    except Exception as e:
        logger.warning(f"加载本地密钥文件失败: {e}")
        return None, None


def _save_keys_to_file(private_pem: bytes, public_pem: bytes) -> None:
    """将密钥对保存到本地文件（开发环境）"""
    try:
        os.makedirs(os.path.dirname(_RSA_KEYS_FILE), exist_ok=True)
        with open(_RSA_KEYS_FILE, 'w') as f:
            json.dump({'private': private_pem.decode(), 'public': public_pem.decode()}, f)
        logger.info("RSA 密钥对已保存到 .keys/rsa.json")
    except Exception as e:
        logger.warning(f"保存密钥文件失败: {e}")


def load_rsa_keys():
    """加载或生成 RSA 密钥对

    加载优先级：
    1. 环境变量（生产环境）
    2. 本地文件 .keys/rsa.json（开发环境，重启复用）
    3. 首次生成并保存到文件
    """
    global _rsa_private_key, _rsa_public_key, _rsa_public_key_pem

    if _rsa_private_key is not None:
        return

    # 1. 优先从环境变量加载密钥
    if settings.RSA_PRIVATE_KEY and settings.RSA_PUBLIC_KEY:
        private_key_str = settings.RSA_PRIVATE_KEY.replace('\\n', '\n')
        public_key_str = settings.RSA_PUBLIC_KEY.replace('\\n', '\n')
        private_pem = private_key_str.encode()
        public_pem = public_key_str.encode()
    # 2. 开发环境从本地文件加载
    else:
        private_pem, public_pem = _load_keys_from_file()
        if private_pem is None:
            # 3. 首次生成并保存
            private_pem, public_pem = generate_rsa_key_pair()
            _save_keys_to_file(private_pem, public_pem)
            print("警告: 使用自动生成的 RSA 密钥对，已保存到 .keys/rsa.json，生产环境请配置 RSA_PRIVATE_KEY 和 RSA_PUBLIC_KEY")

    _rsa_private_key = serialization.load_pem_private_key(
        private_pem,
        password=None,
        backend=default_backend()
    )
    _rsa_public_key = serialization.load_pem_public_key(
        public_pem,
        backend=default_backend()
    )
    _rsa_public_key_pem = public_pem.decode()


def get_rsa_public_key() -> str:
    """获取 RSA 公钥（PEM 格式）"""
    load_rsa_keys()
    return _rsa_public_key_pem


def rsa_decrypt(encrypted_data: str) -> str:
    """RSA 解密（使用私钥解密）
    
    Args:
        encrypted_data: Base64 编码的加密数据
    
    Returns:
        解密后的明文字符串
    
    Raises:
        ValueError: 当解密失败时抛出，包含详细的错误信息
    """
    import logging
    logger = logging.getLogger(__name__)
    
    load_rsa_keys()
    
    try:
        # Base64 解码
        encrypted_bytes = base64.b64decode(encrypted_data, validate=True)
    except Exception as e:
        logger.error(f"RSA解密失败: Base64解码错误 - {str(e)}")
        raise ValueError("密码加密数据格式错误: Base64解码失败")
    
    try:
        # RSA 解密
        decrypted_bytes = _rsa_private_key.decrypt(
            encrypted_bytes,
            padding.PKCS1v15()
        )
    except Exception as e:
        logger.error(f"RSA解密失败: 解密错误 - {str(e)}, 加密数据长度: {len(encrypted_bytes)}")
        raise ValueError("密码解密失败: 可能是RSA密钥不匹配或数据已损坏")
    
    try:
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"RSA解密失败: UTF-8解码错误 - {str(e)}")
        raise ValueError("密码解密失败: 无法解码为UTF-8字符串")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    if "type" not in to_encode:
        to_encode["type"] = "access"
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode["exp"] = expire
    if "type" not in to_encode:
        to_encode["type"] = "refresh"
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        # Token 已过期
        import logging
        logging.getLogger(__name__).warning("Token 已过期")
        return None
    except JWTError as e:
        # 其他 JWT 错误
        import logging
        logging.getLogger(__name__).warning(f"Token 解码失败: {e}")
        return None

