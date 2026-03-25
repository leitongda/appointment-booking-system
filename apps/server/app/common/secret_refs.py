"""Secret 引用解析工具。

当前阶段优先支持 `env:VAR_NAME` 形式的环境变量引用。
为兼容迁移中的配置，如果未使用 `env:` 前缀，则原样返回。
"""

from __future__ import annotations

import os
from typing import Optional


def resolve_secret_ref(secret_ref: Optional[str]) -> Optional[str]:
    if not secret_ref:
        return None

    value = secret_ref.strip()
    if not value:
        return None

    if value.startswith("env:"):
        env_name = value[4:].strip()
        if not env_name:
            return None
        return os.getenv(env_name)

    return value
