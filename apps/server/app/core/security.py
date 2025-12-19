from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import jwt, JWTError
import bcrypt
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from app.core.config import settings


# RSA 密钥缓存
_rsa_private_key = None
_rsa_public_key = None
_rsa_public_key_pem = None


def generate_rsa_key_pair() -> Tuple[bytes, bytes]:
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


def load_rsa_keys():
    """加载或生成 RSA 密钥对"""
    global _rsa_private_key, _rsa_public_key, _rsa_public_key_pem
    
    if _rsa_private_key is not None:
        return
    
    # 尝试从配置加载密钥
    if settings.RSA_PRIVATE_KEY and settings.RSA_PUBLIC_KEY:
        # 处理环境变量中的换行符（可能是字面量 \n）
        private_key_str = settings.RSA_PRIVATE_KEY.replace('\\n', '\n')
        public_key_str = settings.RSA_PUBLIC_KEY.replace('\\n', '\n')
        private_pem = private_key_str.encode()
        public_pem = public_key_str.encode()
    else:
        # 生成新的密钥对（仅用于开发环境）
        private_pem, public_pem = generate_rsa_key_pair()
        print("警告: 使用自动生成的 RSA 密钥对，生产环境请配置 RSA_PRIVATE_KEY 和 RSA_PUBLIC_KEY")
    
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
    """
    load_rsa_keys()
    
    # Base64 解码
    encrypted_bytes = base64.b64decode(encrypted_data)
    
    # RSA 解密
    decrypted_bytes = _rsa_private_key.decrypt(
        encrypted_bytes,
        padding.PKCS1v15()
    )
    
    return decrypted_bytes.decode('utf-8')


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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    if "type" not in to_encode:
        to_encode["type"] = "access"
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode["exp"] = expire
    if "type" not in to_encode:
        to_encode["type"] = "refresh"
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
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

