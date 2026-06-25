# 第三方集成部署指南（钉钉 / 企业微信 / 飞书）

本文档说明如何配置和启用第三方平台集成，涵盖消息推送、扫码登录、审批同步、组织架构同步四大能力。

## 目录

- [架构概览](#架构概览)
- [前置准备](#前置准备)
- [1. 数据库迁移](#1-数据库迁移)
- [2. 环境变量配置](#2-环境变量配置)
- [3. 各平台开放平台配置](#3-各平台开放平台配置)
- [4. 管理后台启用](#4-管理后台启用)
- [5. 能力详解与启用](#5-能力详解与启用)
- [故障排查](#故障排查)
- [安全须知](#安全须知)

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        管理后台 (admin)                         │
│  系统配置 → 第三方集成（凭证配置 + 测试连接 + 组织同步）          │
│  登录页（钉钉/企业微信/飞书扫码 Tab）                            │
│  账号设置 → 第三方账号（绑定/解绑）                              │
└──────────────────────┬──────────────────────────────────────┘
                       │ /api/v1/integration (CRUD)
                       │ /api/v1/admin/integration (OAuth登录)
┌──────────────────────▼──────────────────────────────────────┐
│                    后端 (FastAPI server)                       │
│                                                                │
│  Integration 模块          IntegrationGateway (入站回调)       │
│  ├ 配置 CRUD               ├ /dingtalk/approval-callback      │
│  ├ 连接测试                ├ /wecom/approval-callback         │
│  └ 组织同步                └ /feishu/approval-callback        │
│                                                                │
│  Provider 基础设施            通知渠道                          │
│  ├ DingtalkProvider          ├ dingtalk (通知渠道)             │
│  ├ WecomProvider             ├ wecom                          │
│  └ FeishuProvider            └ feishu                         │
│                                                                │
│  Celery 定时：每6小时同步组织架构                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     ┌─────────┐ ┌──────────┐ ┌─────────┐
     │  钉钉    │ │ 企业微信  │ │  飞书   │
     │ 开放平台  │ │          │ │         │
     └─────────┘ └──────────┘ └─────────┘
```

### 数据库表

| 表 | 用途 |
|----|------|
| `integrations` | 租户级第三方凭证（AppID/Secret引用/Webhook） |
| `integration_bindings` | 用户账号与第三方平台的绑定关系 |

> 凭证安全：敏感 Secret **不入库明文**，以 `env:变量名` 引用形式存储，实际值在环境变量中。

---

## 前置准备

1. **已完成接线合并**：参考 `patches/README-接线应用指南.md`，确保路由、渠道、配置项已注册
2. **已执行迁移**（见下文）
3. **各平台开发者账号**：已注册钉钉/企业微信/飞书的开放平台开发者账号

---

## 1. 数据库迁移

```bash
cd apps/server
alembic upgrade head
```

验证迁移成功：
```bash
# 确认两张新表已创建
psql -c "\dt integrations"
psql -c "\dt integration_bindings"

# 确认扩展字段
psql -c "\d notification_preferences" | grep -E "dingtalk|wecom|feishu"
psql -c "\d unified_templates" | grep -E "dingtalk_msg|robot_msg"
```

---

## 2. 环境变量配置

在 `apps/server/.env`（或部署环境的 env）中配置各平台凭证：

```bash
# ============ 钉钉 ============
# 获取：https://open-dev.dingtalk.com → 应用开发 → 企业内部应用
DINGTALK_APP_KEY=ding1234567890abcdef
DINGTALK_APP_SECRET=your_dingtalk_app_secret
DINGTALK_AGENT_ID=1234567890

# ============ 企业微信 ============
# 获取：https://work.weixin.qq.com → 应用管理 → 自建应用
WECOM_CORP_ID=ww1234567890abcdef
WECOM_APP_SECRET=your_wecom_app_secret
WECOM_AGENT_ID=1000002

# ============ 飞书 ============
# 获取：https://open.feishu.cn → 开发者后台 → 企业自建应用
FEISHU_APP_ID=cli1234567890abcdef
FEISHU_APP_SECRET=your_feishu_app_secret
```

> **多租户覆盖**：以上为全局默认值。每个租户可在管理后台「第三方集成」页面配置自己的凭证（Secret 字段填环境变量名，如 `DINGTALK_APP_SECRET`，系统会自动解析为 `env:` 引用）。

---

## 3. 各平台开放平台配置

### 3.1 钉钉 (DingTalk)

**应用类型**：企业内部应用

**需要开启的权限**：
| 权限 | 用途 |
|------|------|
| 通讯录管理（部门/成员读取） | 组织架构同步 |
| 企业内发送工作通知 | 消息推送 |
| 身份验证（扫码登录） | 扫码登录 SSO |
| 审批（审批事件订阅） | 审批同步 |

**回调地址配置**（开放平台 → 应用 → 事件订阅）：

| 用途 | URL |
|------|-----|
| 扫码登录回调 | `https://你的域名/login/integration-callback?provider=dingtalk` |
| 审批结果回调 | `https://你的域名/api/v1/integration-gateway/dingtalk/approval-callback` |

**加密配置**：事件订阅需配置 AES 密钥，用于回调加密。当前实现接受明文回调，如需加密请额外开发。

### 3.2 企业微信 (WeCom)

**应用类型**：自建应用

**需要开启的权限（API 权限）**：
| 权限 | 用途 |
|------|------|
| 通讯录读取 | 组织架构同步 |
| 应用消息发送 | 消息推送 |
| 网页授权（OAuth2） | 扫码登录 |
| 审批数据 | 审批同步 |

**可信赖域名 / 回调地址**：

| 用途 | URL |
|------|-----|
| OAuth 授权回调 | `https://你的域名/login/integration-callback?provider=wecom` |
| 审批事件回调 | `https://你的域名/api/v1/integration-gateway/wecom/approval-callback` |

> 企业微信回调需配置 **Token + EncodingAESKey**，当前实现已做 SHA1 签名校验。

### 3.3 飞书 (Feishu)

**应用类型**：企业自建应用

**需要开启的权限（权限管理）**：
| 权限 | 用途 |
|------|------|
| 获取通讯录（部门/用户） | 组织架构同步 |
| 发送消息（im:message） | 消息推送 |
| 获取用户身份（登录） | 扫码登录 |
| 审批（approval:approval） | 审批同步 |

**事件订阅 URL（开发者后台 → 事件订阅）**：

| 用途 | URL |
|------|-----|
| 登录授权回调 | `https://你的域名/login/integration-callback?provider=feishu` |
| 审批事件回调 | `https://你的域名/api/v1/integration-gateway/feishu/approval-callback` |

> 飞书回调需配置 **Encrypt Key**，当前实现已做 SHA256 签名校验。

---

## 4. 管理后台启用

1. 登录管理后台（需超级管理员权限）
2. 进入 **系统管理 → 系统配置 → 第三方集成**
3. 选择平台 Tab（钉钉/企业微信/飞书），填写：
   - **应用 ID**：直接填写（如 AppKey / CorpID / App ID）
   - **App Secret 环境变量名**：填**变量名**（如 `DINGTALK_APP_SECRET`），不是密钥本身
   - **AgentID**：钉钉/企业微信需要
   - **群机器人 Webhook**：如需群消息推送则填写
   - **群机器人加签密钥**：开启加签时填变量名
4. 点击 **测试连接** —— 系统会尝试获取 access_token 验证凭证
5. 看到「连接成功」后，开启 **启用状态** 并保存

---

## 5. 能力详解与启用

### 5.1 消息推送通知

**自动生效**：凭证启用后，钉钉/企业微信/飞书自动成为可选通知渠道。

**配置推送渠道**：
- 在 **通知偏好**（用户级）：勾选 dingtalk/wecom/feishu
- 在 **统一消息模板**：配置各平台的模板映射
- 在 **渠道策略**（事件级）：设置哪些事件走哪个渠道

**两种推送形态**：
| 形态 | 配置要求 | 能力 |
|------|---------|------|
| 群机器人 | 仅 Webhook | 推送到群，无法 @ 具体人 |
| 企业应用消息 | AppID + Secret + 用户绑定 | 精准 @ 审批人/申请人（需用户已绑定） |

> 用户需通过扫码登录建立绑定关系后，才能收到点对点工作通知。

### 5.2 扫码登录 (SSO)

**前提**：已在开放平台配置 OAuth 回调地址。

**首次使用流程**：
1. 登录页点击对应平台 Tab（钉钉/企业微信/飞书）
2. 用平台 App 扫描二维码
3. 首次扫码 → 系统提示「绑定手机号」→ 输入管理员手机号 → 匹配本地账号 → 建立绑定
4. 后续扫码 → 直接登录（无需再次绑定）

**查看绑定**：账号设置 → 第三方账号 → 可查看/解绑

### 5.3 审批同步

**出站（本系统 → 平台）**：
在审批流程设计器的节点/全局监听器中配置 `integration_push` 动作：
- 选择平台（钉钉/企业微信/飞书）
- 选择目标：`work_message`（点对点）或 `robot`（群机器人）
- 配置接收人、标题模板、内容模板

**入站（平台 → 本系统）**：
前提：已在开放平台配置审批事件回调地址。
平台审批结果会自动回写到本系统的审批引擎（approve/reject），并记录来源审计。

### 5.4 组织架构同步

**自动同步**：Celery 定时任务每 **6 小时**自动拉取三平台通讯录，同步部门和成员绑定。

**手动触发**：管理后台「第三方集成」页面 → 点击「同步组织架构」按钮。

**同步规则**：
- 部门：按 `tenant_id + name` upsert（幂等，重复同步不产生重复）
- 成员：按手机号匹配本地管理员，匹配成功则建立 `IntegrationBinding`
- **不会自动创建管理员**（需预先在系统创建），未匹配的成员仅记录日志

---

## 故障排查

### 测试连接失败

| 错误 | 可能原因 | 解决 |
|------|---------|------|
| `获取 access_token 失败` | AppID/Secret 错误 | 检查开放平台凭证，确认环境变量名拼写 |
| `未配置 X 集成` | 租户未配置或已禁用 | 在管理后台启用该平台 |
| `Provider 未注册` | 后端接线未完成 | 检查 `registry.py` 是否注册渠道 |

### 扫码登录无反应

1. 检查浏览器控制台是否获取到二维码 URL
2. 确认开放平台的**回调地址**与实际一致（含 `https://` 和完整路径）
3. 确认 `login/integration-callback` 路由已在 `config/routes/auth.ts` 注册
4. 确认 state CSRF 校验通过（Redis 可用）

### 消息推送未送达

```bash
# 查看通知日志，确认发送状态
psql -c "SELECT channel, status, error_message, recipient FROM notification_logs 
         WHERE channel IN ('dingtalk','wecom','feishu') 
         ORDER BY created_at DESC LIMIT 20;"
```

常见原因：
- `用户未绑定X账号`：收件人未通过扫码登录建立绑定
- `租户未配置集成`：该租户未启用对应平台
- `缺少 agent_id`：钉钉/企业微信未配置 AgentID

### 组织同步失败

```bash
# 查看 Celery 任务日志
# 搜索 "org_sync" 关键字
```

常见原因：
- access_token 获取失败（凭证错误）
- 权限不足（未开通通讯录读取权限）
- 成员无手机号（无法匹配本地管理员）

### 审批回调未生效

1. 确认开放平台**事件订阅 URL** 可达（用 curl 测试）
2. 确认签名校验通过（查看后端日志 `signature_failed`）
3. 确认 `ApprovalInstance` 的 ID 与平台审批单号映射正确

---

## 安全须知

### 凭证安全

- ✅ **Secret 仅存环境变量**：数据库只存 `env:变量名` 引用，明文密钥不落库
- ✅ **前端表单排除 Secret**：配置页的 Secret 字段不写入 localStorage 草稿
- ✅ **API 响应脱敏**：集成配置查询返回 `env:****`，不暴露完整引用

### OAuth 安全

- ✅ **state 参数防 CSRF**：`/qrcode` 生成 state 存 Redis（10分钟过期），`/login` 校验后删除
- ✅ **严格 admin token**：第三方登录签发的 token 类型为 `admin`，复用现有权限体系

### 回调安全

- ✅ **签名校验**：三平台回调均验证签名（钉钉 HmacSHA256 / 企业微信 SHA1 / 飞书 SHA256）
- ✅ **租户隔离**：回调通过 external_id → binding → tenant 解析，跨租户不串数据
- ⚠️ **建议生产启用 IP 白名单**：在反向代理层限制回调来源 IP 为各平台官方 IP 段

---

## 验证清单

部署完成后，逐项验证：

- [ ] `alembic upgrade head` 成功，两张新表存在
- [ ] 环境变量已配置（`echo $DINGTALK_APP_KEY` 等）
- [ ] 管理后台「第三方集成」页面可访问
- [ ] 测试连接返回「连接成功」
- [ ] 扫码登录：首次绑定手机号成功，第二次直接登录
- [ ] 消息推送：`notification_logs` 表有对应渠道的 sent 记录
- [ ] 审批同步：审批设计器能选 `integration_push` 动作
- [ ] 组织同步：点击同步按钮后 `integration_bindings` 表有新增记录
- [ ] 单元测试：`pytest tests/unit/test_integration_*.py` 全部通过
