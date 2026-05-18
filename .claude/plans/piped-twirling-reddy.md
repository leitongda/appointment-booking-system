# Admin 端消息模块全面补充

## Context

审计发现 admin 端消息模块存在大量缺失：后端有 23 个 API 端点，但前端仅使用了约 8 个；通知偏好缺少 4 个字段；模板页面绕过 API 层直接用 `request`；消息列表缺少详情查看、批量操作、日期筛选等功能。

**后端 API 使用情况：**

| 模块 | 后端端点数 | 前端已用 | 前端未用 |
|------|-----------|---------|---------|
| unified_message | 14 | 6 (send, my, unread-count, read, read-all, templates CRUD) | 8 (send-batch, rules CRUD x4) |
| notification_logs | 7 | 3 (list, stats, retry) | 4 (detail, usage-stats, quota GET, quota PUT) |
| notification_preferences | 2 | 2 | 0 |
| **合计** | **23** | **11** | **12** |

## 修改步骤

### Step 1: 扩展共享类型定义

**文件: `packages/shared/src/types/message.ts`**

新增 `UnifiedTemplate` 和 `RecipientRule` 类型：

```typescript
export interface UnifiedTemplate {
  id: string;
  tenantId?: string;
  code?: string;
  name?: string;
  messageType?: string;
  eventType?: string;
  subjectTemplate?: string;
  htmlTemplate?: string;
  textTemplate?: string;
  wechatTemplateId?: string;
  variablesSchema?: Record<string, any>;
  status?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface RecipientRule {
  id: string;
  tenantId?: string;
  name?: string;
  eventType?: string;
  ruleType: 'role' | 'department' | 'user_list' | 'dynamic' | 'event_driven';
  ruleConfig: Record<string, any>;
  status?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface NotificationLogStats {
  total: number;
  sent: number;
  failed: number;
  pending: number;
  failureRate: number;
  byChannel: Record<string, number>;
  byType: Record<string, number>;
}

export interface UsageStats {
  total: number;
  byChannel: Record<string, number>;
  dailyTrend: Array<{ date: string; count: number }>;
}

export interface NotificationQuota {
  dailyLimit?: number;
  monthlyLimit?: number;
  dailyUsed?: number;
  monthlyUsed?: number;
}
```

### Step 2: 扩展 API 层

**文件: `packages/api/src/modules/message.ts`**

新增统一模板和收件人规则的 API 方法：

```typescript
// 统一模板 API（templates.tsx 目前用直接 request，需迁移）
getUnifiedTemplates: (params?: { messageType?: string; status?: number; page?: number; pageSize?: number }): Promise<PageResult<UnifiedTemplate>> =>
  request.get('/unified-messages/templates', { params: { message_type: params?.messageType, status: params?.status, page: params?.page, page_size: params?.pageSize } }),

createUnifiedTemplate: (data: Partial<UnifiedTemplate>): Promise<UnifiedTemplate> =>
  request.post('/unified-messages/templates', data),

updateUnifiedTemplate: (id: string, data: Partial<UnifiedTemplate>): Promise<UnifiedTemplate> =>
  request.put(`/unified-messages/templates/${id}`, data),

deleteUnifiedTemplate: (id: string): Promise<void> =>
  request.delete(`/unified-messages/templates/${id}`),

// 收件人规则 API
getRecipientRules: (params?: { eventType?: string }): Promise<RecipientRule[]> =>
  request.get('/unified-messages/rules', { params }),

createRecipientRule: (data: Partial<RecipientRule>): Promise<RecipientRule> =>
  request.post('/unified-messages/rules', data),

updateRecipientRule: (id: string, data: Partial<RecipientRule>): Promise<RecipientRule> =>
  request.put(`/unified-messages/rules/${id}`, data),

deleteRecipientRule: (id: string): Promise<void> =>
  request.delete(`/unified-messages/rules/${id}`),

// 批量发送（通过规则）
sendBatchByRule: (data: { ruleId: string; title: string; content?: string; messageType?: string; eventType?: string }): Promise<{ message: string }> =>
  request.post('/unified-messages/send-batch', data, { params: { rule_id: data.ruleId } }),
```

**文件: `packages/api/src/modules/notification-log.ts`**

新增缺失的 API 方法：

```typescript
getDetail: (id: string): Promise<NotificationLog> =>
  request.get(`/notification-logs/${id}`),

getUsageStats: (params?: { period?: string }): Promise<UsageStats> =>
  request.get('/notification-logs/usage-stats', { params: { period: params?.period || 'month' } }),

getQuota: (): Promise<NotificationQuota> =>
  request.get('/notification-logs/quota'),

updateQuota: (data: Partial<NotificationQuota>): Promise<NotificationQuota> =>
  request.put('/notification-logs/quota', data),
```

**文件: `packages/api/src/modules/notification-preference.ts`**

更新 `NotificationPreference` 接口，补充缺失字段：

```typescript
export interface NotificationPreference {
  id: string;
  appointmentEnabled: boolean;
  reminderEnabled: boolean;
  queueCallEnabled: boolean;    // 已有类型定义但 UI 未渲染
  stopClinicEnabled: boolean;   // 已有类型定义但 UI 未渲染
  consultationEnabled?: boolean;
  feedbackEnabled?: boolean;
  systemEnabled: boolean;
  smsEnabled: boolean;
  emailEnabled: boolean;        // 已有类型定义但 UI 未渲染
  wechatEnabled: boolean;       // 已有类型定义但 UI 未渲染
  inAppEnabled: boolean;
  quietHoursStart?: string;
  quietHoursEnd?: string;
}
```

### Step 3: 修复 templates.tsx 技术债

**文件: `apps/admin/src/pages/message/templates.tsx`**

改动：
1. 删除本地 `UnifiedTemplate` 接口定义，改用 `@hospital/shared` 的类型
2. 将所有 `request('/api/v1/unified-messages/...')` 替换为 `messageApi.getUnifiedTemplates()` 等 API 调用
3. 将 `request` 导入替换为 `messageApi` 导入
4. 列表请求改用 `createListRequest(messageApi.getUnifiedTemplates)` 工具函数

### Step 4: 补充通知偏好缺失字段

**文件: `apps/admin/src/pages/account/settings.tsx`**

在现有"通知类型"和"通知通道"两个分区中补充缺失字段：

通知类型分区新增（在 `systemEnabled` 之后）：
- `queueCallEnabled` -- "叫号通知"，`NotificationOutlined` 图标
- `stopClinicEnabled` -- "停诊通知"，`PauseCircleOutlined` 图标

通知通道分区新增（在 `inAppEnabled` 之后）：
- `emailEnabled` -- "邮件通知"，`MailOutlined` 图标
- `wechatEnabled` -- "微信推送"，`WechatOutlined` 图标

每个字段使用与现有字段相同的 Switch + flex 布局模式，调用 `handleNotificationToggle` 处理。

### Step 5: 增强消息列表页面

**文件: `apps/admin/src/pages/message/index.tsx`**

改动：
1. **日期范围筛选**：在 ProTable columns 中添加 `createdAt` 的搜索列，使用 `valueType: 'dateRange'`
2. **消息详情抽屉**：新增 `Drawer` 组件，点击标题或"查看"按钮打开，调用 `messageApi.getDetail(id)` 展示完整消息内容
3. **批量操作**：ProTable 添加 `rowSelection`，工具栏新增"批量已读"和"批量删除"按钮
4. **清空已读**：工具栏新增"清空已读"按钮，调用 `messageApi.clearRead(currentUser.id, 'admin')`
5. **操作列**：新增"查看"和"删除"操作按钮

### Step 6: 增强发送消息表单

**文件: `apps/admin/src/pages/message/form.tsx`**

改动：
1. **模板选择**：新增 `ProFormSelect` 字段，从 `messageApi.getUnifiedTemplates()` 加载模板列表，选择后自动填充标题和内容
2. **批量发送**：新增 `ProFormSwitch` "批量发送"开关，开启后 `userId` 字段切换为 `ProFormTextArea`（每行一个用户ID），调用 `messageApi.sendBatch()`
3. **消息预览**：Card 底部新增"预览"按钮，弹出 Modal 展示渲染后的消息内容

### Step 7: 增强模板管理页面

**文件: `apps/admin/src/pages/message/templates.tsx`**（在 Step 3 基础上继续）

改动：
1. **模板预览**：操作列新增"预览"按钮，点击打开 Modal 展示 subjectTemplate、textTemplate、htmlTemplate 内容
2. **克隆模板**：操作列新增"克隆"按钮，复制当前模板数据到新建 Modal（code 自动追加 `_copy` 后缀）
3. **测试发送**：ModalForm 底部新增"测试发送"按钮，调用 `messageApi.send()` 发送到指定测试用户

### Step 8: 增强通知日志页面

**文件: `apps/admin/src/pages/system/notification-logs.tsx`**

改动：
1. **日志详情抽屉**：点击"标题"或新增"查看"按钮打开 Drawer，调用 `notificationLogApi.getDetail(id)` 展示完整日志信息（含请求/响应数据）
2. **批量重试**：ProTable 添加 `rowSelection`，工具栏新增"批量重试"按钮，遍历选中失败记录逐个调用 `notificationLogApi.retry()`
3. **日期范围筛选**：添加 `startDate`/`endDate` 搜索列，使用 `valueType: 'dateRange'`
4. **用量统计卡片**：在统计卡片行下方新增一行，展示 `notificationLogApi.getUsageStats()` 的数据（按通道分布 + 每日趋势折线图）
5. **配额信息**：统计卡片行新增"今日配额"和"本月配额"卡片，数据来自 `notificationLogApi.getQuota()`

### Step 9: 新增收件人规则管理页面

**新建文件: `apps/admin/src/pages/message/recipient-rules.tsx`**

页面结构：
- `PageContainer` + `ProTable` 展示规则列表
- 列：规则名称、事件类型、规则类型（Tag 颜色区分）、状态（Switch）、创建时间、操作（编辑/删除）
- 工具栏："新建规则"按钮
- `ModalForm` 编辑规则，字段：
  - `name` -- 规则名称（必填）
  - `eventType` -- 事件类型（Select，选项从 NotificationEventType 枚举）
  - `ruleType` -- 规则类型（Select：role/department/user_list/dynamic/event_driven）
  - `ruleConfig` -- 规则配置（`ProFormTextArea`，JSON 格式，根据 ruleType 显示不同的 placeholder 提示）
- 权限控制：`message:send` / `message:delete`

**文件: `apps/admin/config/routes.ts`**

在 `message` 路由下新增子路由：
```typescript
{ path: '/content-center/message/recipient-rules', component: '@/pages/message/recipient-rules', name: '收件人规则' },
```

### Step 10: 新增通知配额管理页面

**新建文件: `apps/admin/src/pages/system/notification-quota.tsx`**

页面结构：
- `PageContainer` + `Card` 布局
- **配额设置卡片**：`ProForm` 展示和编辑配额（dailyLimit、monthlyLimit），调用 `notificationLogApi.updateQuota()`
- **用量统计卡片**：展示当前周期用量（dailyUsed、monthlyUsed），进度条显示使用比例
- **按通道分布**：`Pie` 或 `Bar` 图表（使用 `@ant-design/charts` 或简单的 Ant Design `Progress` 组件）
- 权限控制：`system:config`（编辑）/ `system:monitoring`（查看）

**文件: `apps/admin/config/routes.ts`**

在 `system` 路由下新增子路由：
```typescript
{ path: '/system/notification-quota', component: '@/pages/system/notification-quota', name: '通知配额' },
```

## 涉及文件清单

| 文件 | 改动类型 | Step |
|------|---------|------|
| `packages/shared/src/types/message.ts` | 修改 - 新增类型 | 1 |
| `packages/api/src/modules/message.ts` | 修改 - 新增 API 方法 | 2 |
| `packages/api/src/modules/notification-log.ts` | 修改 - 新增 API 方法 | 2 |
| `packages/api/src/modules/notification-preference.ts` | 修改 - 补充字段 | 2 |
| `apps/admin/src/pages/message/templates.tsx` | 修改 - API 层迁移 + 新功能 | 3, 7 |
| `apps/admin/src/pages/account/settings.tsx` | 修改 - 补充 4 个偏好字段 | 4 |
| `apps/admin/src/pages/message/index.tsx` | 修改 - 列表增强 | 5 |
| `apps/admin/src/pages/message/form.tsx` | 修改 - 表单增强 | 6 |
| `apps/admin/src/pages/system/notification-logs.tsx` | 修改 - 日志增强 | 8 |
| `apps/admin/src/pages/message/recipient-rules.tsx` | **新建** | 9 |
| `apps/admin/src/pages/system/notification-quota.tsx` | **新建** | 10 |
| `apps/admin/config/routes.ts` | 修改 - 新增路由 | 9, 10 |

## 向后兼容性

- 所有现有 API 调用保持不变，仅新增方法
- 现有页面功能不受影响，仅增加新功能
- 新路由不影响现有路由结构
- 共享类型仅新增，不修改现有类型

## 验证方式

1. `pnpm dev:admin` 启动前端开发服务器
2. 逐页面手动验证：
   - 消息列表：筛选、详情抽屉、批量操作、清空已读
   - 发送消息：模板选择、批量发送、预览
   - 模板管理：CRUD、预览、克隆、测试发送（API 层迁移后功能一致）
   - 通知日志：详情、批量重试、日期筛选、用量统计、配额
   - 通知偏好：确认新增 4 个字段正常显示和保存
   - 收件人规则：CRUD 操作
   - 通知配额：查看和编辑
3. `pnpm lint` 确保无 lint 错误
4. `pnpm build:admin` 确保构建通过
