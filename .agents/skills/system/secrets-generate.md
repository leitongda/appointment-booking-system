---
name: Generate Secrets
description: 生成新的密钥和凭据
category: system
tags: [security, secrets]
parameters:
  - name: type
    type: choice
    required: false
    default: all
    description: 密钥类型
    choices: [all, jwt, secret, api-key]
---

**用途**
生成新的密钥和凭据用于系统配置。

**前置条件**
- Python 或 OpenSSL 已安装

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --type | choice | 否 | all | 密钥类型 |

**执行步骤**

根据 type 生成：

1. **jwt**: JWT 密钥
   ```bash
   openssl rand -base64 64
   ```

2. **secret**: 应用密钥
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **api-key**: API 密钥
   ```bash
   python -c "import uuid; print(str(uuid.uuid4()))"
   ```

4. **all**: 生成所有类型

显示生成的密钥，并提示用户配置到环境变量或配置文件。

**注意事项**
- 生成的密钥请妥善保管
- 建议定期轮换密钥
- 更新密钥后需要重启服务

**示例**
```bash
# 生成所有密钥
/secrets-generate

# 仅生成 JWT 密钥
/secrets-generate --type jwt

# 仅生成应用密钥
/secrets-generate --type secret
```
