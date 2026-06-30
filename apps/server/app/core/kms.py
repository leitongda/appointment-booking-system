"""
KMS（密钥管理服务）集成模块

提供统一的 KMS 接口，支持阿里云 KMS 和腾讯云 KMS。
用于获取数据加密密钥（DEK），实现信封加密模式。

信封加密流程：
1. 从 KMS 获取 DEK（Data Encryption Key）
2. 用 DEK 加密本地数据
3. 将加密的 DEK（Encrypted DEK）存储在配置中
4. 解密时：先用 KMS 解密 Encrypted DEK 得到 DEK，再用 DEK 解密数据

本地开发模式：
- 不依赖 KMS，直接使用环境变量 ENCRYPTION_KEY
- 通过 KMS_PROVIDER=local 切换
"""
import base64
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class KMSProvider(ABC):
    """KMS 提供者抽象基类"""

    @abstractmethod
    def generate_data_key(self) -> tuple[bytes, bytes]:
        """生成数据加密密钥（DEK）

        Returns:
            (plaintext_key, encrypted_key): 明文密钥和加密后的密钥
        """
        pass

    @abstractmethod
    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """解密数据加密密钥

        Args:
            encrypted_key: 加密后的密钥

        Returns:
            明文密钥
        """
        pass


class LocalKMSProvider(KMSProvider):
    """本地 KMS 提供者（开发环境）

    不依赖外部 KMS 服务，直接使用环境变量中的密钥。
    """

    def __init__(self):
        key_b64 = os.getenv("ENCRYPTION_KEY")
        if key_b64:
            self._key = base64.b64decode(key_b64)
        else:
            # 生成随机密钥（开发环境）
            self._key = os.urandom(32)
            logger.warning("未设置 ENCRYPTION_KEY，使用随机密钥（仅限开发环境）")

        if len(self._key) != 32:
            raise ValueError(f"ENCRYPTION_KEY 必须是 32 字节（当前 {len(self._key)} 字节）")

    def generate_data_key(self) -> tuple[bytes, bytes]:
        """返回固定密钥（本地模式不实际生成新密钥）"""
        # 本地模式下返回固定密钥，encrypted_key 为占位
        return self._key, base64.b64encode(self._key)

    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """直接返回 base64 解码后的密钥"""
        return base64.b64decode(encrypted_key)


class AliyunKMSProvider(KMSProvider):
    """阿里云 KMS 提供者

    需要安装：pip install alibabacloud-kms20160120>=3.0.0
    配置项：ALIBABA_CLOUD_ACCESS_KEY_ID, ALIBABA_CLOUD_ACCESS_KEY_SECRET, KMS_KEY_ID
    """

    def __init__(self):
        self._key_id = os.getenv("KMS_KEY_ID")
        if not self._key_id:
            raise ValueError("阿里云 KMS 需要配置 KMS_KEY_ID")

        try:
            from alibabacloud_kms20160120 import models as kms_models
            from alibabacloud_kms20160120.client import Client as KmsClient
            from alibabacloud_tea_openapi import models as open_api_models

            access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
            access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

            if not access_key_id or not access_key_secret:
                raise ValueError("阿里云 KMS 需要配置 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET")

            config = open_api_models.Config(
                access_key_id=access_key_id,
                access_key_secret=access_key_secret,
            )
            config.endpoint = f"kms.{os.getenv('ALIBABA_CLOUD_REGION', 'cn-hangzhou')}.aliyuncs.com"
            self._client = KmsClient(config)
            self._kms_models = kms_models
        except ImportError:
            raise ImportError("使用阿里云 KMS 需要安装：pip install alibabacloud-kms20160120>=3.0.0")

    def generate_data_key(self) -> tuple[bytes, bytes]:
        """调用阿里云 KMS GenerateDataKey 接口"""
        request = self._kms_models.GenerateDataKeyRequest(
            key_id=self._key_id,
            key_spec="AES_256",
        )
        response = self._client.generate_data_key(request)
        plaintext_key = base64.b64decode(response.body.plaintext)
        encrypted_key = base64.b64decode(response.body.ciphertext_blob)
        return plaintext_key, encrypted_key

    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """调用阿里云 KMS Decrypt 接口"""
        request = self._kms_models.DecryptRequest(
            ciphertext_blob=base64.b64encode(encrypted_key).decode(),
        )
        response = self._client.decrypt(request)
        return base64.b64decode(response.body.plaintext)


class TencentKMSProvider(KMSProvider):
    """腾讯云 KMS 提供者

    需要安装：pip install tencentcloud-sdk-python>=3.0.0
    配置项：TENCENT_SECRET_ID, TENCENT_SECRET_KEY, KMS_KEY_ID
    """

    def __init__(self):
        self._key_id = os.getenv("KMS_KEY_ID")
        if not self._key_id:
            raise ValueError("腾讯云 KMS 需要配置 KMS_KEY_ID")

        try:
            from tencentcloud.common import credential
            from tencentcloud.kms.v20190118 import kms_client, models as kms_models

            secret_id = os.getenv("TENCENT_SECRET_ID")
            secret_key = os.getenv("TENCENT_SECRET_KEY")

            if not secret_id or not secret_key:
                raise ValueError("腾讯云 KMS 需要配置 TENCENT_SECRET_ID 和 TENCENT_SECRET_KEY")

            cred = credential.Credential(secret_id, secret_key)
            self._client = kms_client.KmsClient(cred, os.getenv("TENCENT_CLOUD_REGION", "ap-guangzhou"))
            self._kms_models = kms_models
        except ImportError:
            raise ImportError("使用腾讯云 KMS 需要安装：pip install tencentcloud-sdk-python>=3.0.0")

    def generate_data_key(self) -> tuple[bytes, bytes]:
        """调用腾讯云 KMS GenerateDataKey 接口"""
        request = self._kms_models.GenerateDataKeyRequest()
        request.KeyId = self._key_id
        request.KeySpec = "AES_256"
        response = self._client.GenerateDataKey(request)
        plaintext_key = base64.b64decode(response.Plaintext)
        encrypted_key = base64.b64decode(response.EncryptedDataKey)
        return plaintext_key, encrypted_key

    def decrypt_data_key(self, encrypted_key: bytes) -> bytes:
        """调用腾讯云 KMS Decrypt 接口"""
        request = self._kms_models.DecryptRequest()
        request.CiphertextBlob = base64.b64encode(encrypted_key).decode()
        response = self._client.Decrypt(request)
        return base64.b64decode(response.Plaintext)


def get_kms_provider() -> KMSProvider:
    """获取 KMS 提供者实例

    根据环境变量 KMS_PROVIDER 选择提供者：
    - local（默认）：本地密钥，开发环境
    - aliyun：阿里云 KMS
    - tencent：腾讯云 KMS

    Returns:
        KMSProvider 实例
    """
    provider = os.getenv("KMS_PROVIDER", "local").lower()

    if provider == "local":
        return LocalKMSProvider()
    elif provider == "aliyun":
        return AliyunKMSProvider()
    elif provider == "tencent":
        return TencentKMSProvider()
    else:
        raise ValueError(f"不支持的 KMS_PROVIDER: {provider}（支持：local/aliyun/tencent）")
