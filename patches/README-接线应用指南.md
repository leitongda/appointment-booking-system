# 第三方集成 — 接线改动应用指南

本分支 `feat/third-party-integrations` 已提交 34 个**纯新增文件**（5 个 commit）。
但由于工作区有大量会话前就存在的未提交改动，以下 **22 个现有文件**的"接线"改动
（注册路由/渠道、加配置项、加权限等）尚未提交，需要手动合并。

## 应用方式（推荐顺序）

### 方式 A：尝试自动应用补丁（可能有行号冲突）

```bash
# 1. 干净文件补丁（几乎不会冲突，可直接 apply）
git apply --3way patches/01-wiring-clean-files.patch

# 2. 混合文件补丁（行号可能漂移，用 --3way 启用三方合并）
git apply --3way patches/02-wiring-mixed-files.patch
# 若失败，用 patch 命令的模糊匹配：
patch -p1 < patches/02-wiring-mixed-files.patch
```

### 方式 B：按下方说明手动改动（最可靠）

若自动 apply 失败，按下面的逐文件说明手动修改。
每处都标注了**搜索锚点**（原文件中已存在的唯一代码行），找到它后在其附近添加。

---

## 后端接线（16 处，按重要性排序）

### 1. 注册 API 路由 — `apps/server/app/api/v1/__init__.py`
**搜索**: `RouterRegistration("app.modules.guide_tours.router_admin"`
**在其后添加**:
```python
    RouterRegistration("app.modules.integration.router", "/integration", ["第三方集成"]),
    RouterRegistration("app.modules.integration_gateway.router", "/integration-gateway", ["第三方回调"]),
```

### 2. 注册通知渠道 — `apps/server/app/infrastructure/notifications/registry.py`
**搜索**: `from app.infrastructure.notifications.channels.wechat import WechatChannel`
**在其后添加**:
```python
    # 第三方集成渠道
    from app.infrastructure.notifications.channels.dingtalk import DingtalkChannel
    from app.infrastructure.notifications.channels.feishu import FeishuChannel
    from app.infrastructure.notifications.channels.wecom import WecomChannel
```
**搜索**: `channel_registry.register(WebSocketChannel)`
**在其后添加**:
```python
    # 第三方平台（钉钉/企业微信/飞书）
    channel_registry.register(DingtalkChannel)
    channel_registry.register(WecomChannel)
    channel_registry.register(FeishuChannel)
```

### 3. 挂载 OAuth 路由 — `apps/server/app/modules/admin/router_auth.py`
**搜索**: `from .router_auth_login import router as login_router`
**在其前添加**:
```python
from .router_auth_integration import router as integration_router
```
**搜索**: `router.include_router(password_router, tags=["密码管理"])`
**在其后添加**:
```python
router.include_router(integration_router, tags=["第三方登录"])
```

### 4. 注册新模型 — `apps/server/app/models/__init__.py`
**搜索**: `from app.models.leave_request import LeaveRequest`
**在其前添加**:
```python
from app.models.integration import Integration, IntegrationBinding
```

### 5. Alembic 模型导入 — `apps/server/migrations/env.py`
**搜索**: `from app.models import miniapp_platform, tenant, refund`
**在其后添加**:
```python
from app.models import integration
```

### 6. 配置项 — `apps/server/app/core/config.py`
**搜索**: `WECHAT_CALLBACK_TOKEN: str | None = None`
**在其后添加**:
```python

    # 第三方集成默认凭证（钉钉/企业微信/飞书）
    # 注：租户级凭证存于 integrations 表，此处为全局默认值/自部署兜底。
    # 敏感 Secret 仅放环境变量，DB 以 env: 引用。
    # 钉钉
    DINGTALK_APP_KEY: str | None = None
    DINGTALK_APP_SECRET: str | None = None
    DINGTALK_AGENT_ID: str | None = None
    # 企业微信
    WECOM_CORP_ID: str | None = None
    WECOM_APP_SECRET: str | None = None
    WECOM_AGENT_ID: str | None = None
    # 飞书
    FEISHU_APP_ID: str | None = None
    FEISHU_APP_SECRET: str | None = None
```

### 7. Redis token 缓存 — `apps/server/app/core/redis.py`
**搜索**: `PREFIX_RULE_PERF = "rule_engine:"`
**在其后添加**:
```python
    PREFIX_INTEGRATION_TOKEN = "integration:token:"  # 第三方平台 access_token
```
**搜索**: get_wechat_token 方法结尾的 `return await cls.get(key)` 之后、`# ==================== 扫码登录` 之前，**添加**:
```python

    # ==================== 第三方集成 Token 缓存 ====================

    @staticmethod
    def _build_integration_token_key(provider: str, app_id: str, tenant_id: str | None = None) -> str:
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            return f"{RedisCache.PREFIX_INTEGRATION_TOKEN}{effective_tenant_id}:{provider}:{app_id}"
        return f"{RedisCache.PREFIX_INTEGRATION_TOKEN}{provider}:{app_id}"

    @classmethod
    async def set_integration_token(cls, provider, app_id, token, expire=7000, tenant_id=None) -> bool:
        key = cls._build_integration_token_key(provider, app_id, tenant_id)
        return await cls.set(key, token, expire)

    @classmethod
    async def get_integration_token(cls, provider, app_id, tenant_id=None) -> str | None:
        key = cls._build_integration_token_key(provider, app_id, tenant_id)
        return await cls.get(key)
```

### 8. 通知偏好映射 — `apps/server/app/common/notification_preference.py`
**搜索 CHANNEL_FIELD_MAP 中的**: `"websocket": "in_app_enabled",`
**在其后添加**:
```python
    # 第三方集成平台
    "dingtalk": "dingtalk_enabled",
    "wecom": "wecom_enabled",
    "feishu": "feishu_enabled",
```
（get_user_preferences 的 SELECT 语句也要加这三个字段，见补丁）

### 9. 偏好模型字段 — `apps/server/app/models/notification_preference.py`
**搜索**: `in_app_enabled = Column(Boolean, default=True, comment="站内消息")`
**在其后添加**:
```python
    # 第三方集成平台（钉钉/企业微信/飞书）
    dingtalk_enabled = Column(Boolean, default=True, comment="钉钉推送")
    wecom_enabled = Column(Boolean, default=True, comment="企业微信推送")
    feishu_enabled = Column(Boolean, default=True, comment="飞书推送")
```

### 10. UnifiedTemplate 模板字段 — `apps/server/app/modules/unified_message/models.py`
**搜索**: `wechat_template_mapping = Column(JSON, nullable=True, comment="微信字段映射")`
**在其后添加**:
```python
    # 第三方集成平台模板
    dingtalk_msg_template = Column(JSON, nullable=True, comment="钉钉工作通知消息体模板")
    wecom_msg_template = Column(JSON, nullable=True, comment="企业微信应用消息模板")
    feishu_msg_template = Column(JSON, nullable=True, comment="飞书消息模板")
    robot_msg_template = Column(Text, nullable=True, comment="群机器人通用 markdown 模板（三平台共用）")
```

### 11. NotificationEvent schema — `apps/server/app/schemas/notification.py`
**搜索**: `recipient_openid: str | None = Field`
**在其后添加**:
```python
    # 第三方集成平台收件人ID
    recipient_dingtalk_id: str | None = Field(None, description="接收人钉钉 userId")
    recipient_wecom_id: str | None = Field(None, description="接收人企业微信 userid")
    recipient_feishu_id: str | None = Field(None, description="接收人飞书 open_id")
```

### 12. Celery beat 定时任务 — `apps/server/app/celery_app.py`
**搜索 beat_schedule 中的**: `"attendance-cleanup"` 任务块结尾的 `},`
**在其后添加**:
```python

        # 第三方集成组织架构同步 - 每6小时
        "integration-org-sync": {
            "task": "app.tasks.integration_sync_task.sync_all_tenants_task",
            "schedule": crontab(minute=0, hour="*/6"),
            "options": {"queue": "scheduled"},
        },
```

### 13. .env.example — `apps/server/.env.example`
**搜索**: `WECHAT_CALLBACK_TOKEN=your-wechat-callback-token`
**在其后添加**（完整内容见补丁文件）

### 14. dispatcher 偏好映射 — `apps/server/app/infrastructure/notifications/dispatcher.py`
**搜索 `_CHANNEL_FIELD_MAP` 中的**: `"websocket": "in_app_enabled",`
**在其后添加**（与第8步相同）:
```python
    "dingtalk": "dingtalk_enabled",
    "wecom": "wecom_enabled",
    "feishu": "feishu_enabled",
```
> 注：此文件我的 grep 显示 0 行匹配，但为保持与 notification_preference.py 一致仍需添加。

---

## 前端接线（6 处）

### 15. API 包导出 — `packages/api/src/index.ts`
**搜索**: `export { settingsApi } from './modules/settings';`
**在其后添加**:
```typescript
export { integrationApi } from './modules/integration';
export type {
  IntegrationProvider, IntegrationConfig, IntegrationUpsertInput,
  IntegrationProviderInfo, IntegrationBinding, TestConnectionResult,
} from './modules/integration';
```

### 16. adminApi 登录接口 — `packages/api/src/modules/admin.ts`
**两处改动**：

**改动 A — 类型定义**：搜索 `export interface WechatCheckResult` 块的结尾（`}` 后），添加：
```typescript
// ========== 第三方集成扫码登录（钉钉/企业微信/飞书） ==========
export type IntegrationLoginProvider = 'dingtalk' | 'wecom' | 'feishu';

export interface IntegrationQrcodeResult {
  provider: IntegrationLoginProvider;
  qrcodeUrl: string;
  state: string;
  expireSeconds: number;
}

export interface IntegrationLoginResult {
  isNewUser?: boolean;
  needBindPhone?: boolean;
  provider: IntegrationLoginProvider;
  externalId?: string;
  unionId?: string;
  name?: string;
  accessToken?: string;
  refreshToken?: string;
  expiresIn?: number;
  admin?: Admin;
}

export interface IntegrationBindPhoneParams {
  provider: IntegrationLoginProvider;
  externalId: string;
  unionId?: string;
  name?: string;
  phone: string;
}

export interface IntegrationBindingItem {
  id: string;
  provider: IntegrationLoginProvider;
  external_id: string;
  name?: string;
}
```

**改动 B — API 方法**：搜索 `checkWechatScan` 方法块的结尾 `},`，在其后添加：
```typescript

  // ========== 第三方集成扫码登录（钉钉/企业微信/飞书） ==========
  getIntegrationQrcode: (
    provider: IntegrationLoginProvider,
    redirectUri: string,
  ): Promise<IntegrationQrcodeResult> => {
    return request.get(`${PREFIX}/integration/qrcode`, {
      params: { provider, redirect_uri: redirectUri },
    });
  },

  integrationLogin: (
    provider: IntegrationLoginProvider,
    code: string,
    state?: string,
  ): Promise<IntegrationLoginResult> => {
    return request.post(`${PREFIX}/integration/login?provider=${provider}`, { code, state });
  },

  integrationBindPhone: (
    data: IntegrationBindPhoneParams,
  ): Promise<IntegrationLoginResult> => {
    return request.post(`${PREFIX}/integration/bind-phone`, data);
  },

  bindIntegration: (
    provider: IntegrationLoginProvider,
    code: string,
    state?: string,
  ): Promise<{ message: string; external_id: string }> => {
    return request.post(`${PREFIX}/integration/bind?provider=${provider}`, { code, state });
  },

  listIntegrationBindings: (): Promise<IntegrationBindingItem[]> => {
    return request.get(`${PREFIX}/integration/bindings`);
  },
```

### 17. 登录回调路由 — `apps/admin/config/routes/auth.ts`
**搜索**: `{ path: '/login', layout: false, component: './login' },`
**在其后添加**:
```typescript
  { path: '/login/integration-callback', layout: false, component: './login/integration-callback' },
```

### 18. 集成配置菜单 — `apps/admin/config/routes/system.ts`
**搜索**: `email-recipients` 路由行
**在其后添加**:
```typescript
          { path: '/system/config/integrations', name: '第三方集成', icon: 'api', component: './system/integrations', access: 'canIntegrationSettings' },
```

### 19. 权限定义 — `apps/admin/src/access.ts`
**搜索**: `const canWechatSettings =`
**在其后添加**:
```typescript
  const canIntegrationSettings =
    isSuperAdmin || hasAnyPermission(['settings:integration', 'settings:edit']);
```
**搜索 canSystemManagement 中的**: `canOnlineUsers;`
**改为**: `canOnlineUsers ||\n    canIntegrationSettings;`
**搜索 return 对象中的**: `canWechatSettings,`
**在其后添加**: `canIntegrationSettings,`

### 20. 登录页 Tab — `apps/admin/src/pages/login/index.tsx`
**四处改动**：

**改动 A — import**：搜索 `WechatLogin, WechatOutlined`，在其后同一 import 块追加：
```typescript
  IntegrationLogin,
  IntegrationBindPhoneModal,
  type BindPhoneInfo,
```

**改动 B — LoginType + 常量**：搜索 `type LoginType = 'wechat' | 'phone' | 'account';`，替换为：
```typescript
type LoginType = 'wechat' | 'phone' | 'account' | 'dingtalk' | 'wecom' | 'feishu';

// 第三方集成登录平台元信息
const INTEGRATION_TABS: Array<{
  key: 'dingtalk' | 'wecom' | 'feishu';
  label: string;
  icon: React.ReactNode;
}> = [
  { key: 'dingtalk', label: '钉钉', icon: <MedicineBoxOutlined /> },
  { key: 'wecom', label: '企业微信', icon: <MedicineBoxOutlined /> },
  { key: 'feishu', label: '飞书', icon: <MedicineBoxOutlined /> },
];
```

**改动 C — bindPhone 状态**：搜索 `const [enableAnimation, setEnableAnimation] = useState(false);`，在其后添加：
```typescript

  // 第三方登录绑定手机号弹窗
  const [bindPhoneOpen, setBindPhoneOpen] = useState(false);
  const [bindPhoneInfo, setBindPhoneInfo] = useState<BindPhoneInfo | null>(null);
  const [bindPhoneLabel, setBindPhoneLabel] = useState('');
```

**改动 D — tabItems 扩展**：搜索 tabItems 数组的 `]` 结尾前（account tab 之后），在 `]` 前添加：
```typescript
    ...INTEGRATION_TABS.map((tab) => ({
      key: tab.key,
      label: (
        <span>
          {tab.icon}
          {tab.label}登录
        </span>
      ),
      children: (
        <IntegrationLogin
          provider={tab.key}
          label={tab.label}
          icon={tab.icon}
          onSuccess={handleLoginSuccess}
          onNeedBindPhone={(info) => {
            setBindPhoneInfo(info);
            setBindPhoneLabel(tab.label);
            setBindPhoneOpen(true);
          }}
        />
      ),
    })),
```

**改动 E — Modal JSX**：搜索 return 内最外层 `</div>` 前（footer 之后），添加：
```tsx
      <IntegrationBindPhoneModal
        open={bindPhoneOpen}
        info={bindPhoneInfo}
        label={bindPhoneLabel}
        onSuccess={(result) => {
          setBindPhoneOpen(false);
          handleLoginSuccess(result);
        }}
        onCancel={() => setBindPhoneOpen(false)}
      />
```

### 21. 组件导出 — `apps/admin/src/pages/login/components/index.ts`
**搜索**: `export { default as WechatLogin, WechatOutlined } from './WechatLogin';`
**在其后添加**:
```typescript
export { default as IntegrationLogin } from './IntegrationLogin';
export { default as IntegrationBindPhoneModal } from './IntegrationBindPhoneModal';
export type { BindPhoneInfo } from './IntegrationBindPhoneModal';
```

### 22. 账号设置 Tab — `apps/admin/src/pages/account/settings.tsx`
**搜索 import**: `import EmailBindingModal from '@/components/EmailBindingModal';`
**在其后添加**:
```typescript
import IntegrationBindingsSection from './IntegrationBindingsSection';
```
**搜索 Tabs items 中的 usage tab**:
```typescript
            {
              key: 'usage',
              label: '使用概览',
              children: <UsageOverviewTab adminId={admin?.id} />,
            },
```
**在其后添加**:
```typescript
            {
              key: 'integrations',
              label: '第三方账号',
              children: <IntegrationBindingsSection />,
            },
```

---

## 未跟踪文件（2 个，需特别处理）

以下两个文件在 HEAD 中不存在（别人未提交的工作），我编辑了它们但未提交：

### `apps/server/app/modules/approval_flows/listener_service.py`
我在 `_execute_action` 添加了 `integration_push` 分支，并新增 `_fire_integration_push` 方法。
**此文件整体是别人的未提交工作**，请与原作者协调后，把我的 `integration_push` 改动合并进去。
参考补丁: `patches/03-untracked-listener_service.patch`

### `apps/admin/src/pages/approval/designer/ListenerForm.tsx`
我添加了 `integration_push` action 选项和对应表单 UI。
**此文件整体是别人的未提交工作**，请与原作者协调。
参考补丁: `patches/04-untracked-ListenerForm.patch`

---

## 验证

应用所有接线后，运行验证：
```bash
cd apps/server && python -c "
from app.api.v1 import build_api_router
main_r, _ = build_api_router()
print(f'路由数: {len(main_r.routes)}')  # 应为 886
"
cd apps/server && python -m pytest tests/unit/test_integration_*.py -q  # 应 36 passed
```
