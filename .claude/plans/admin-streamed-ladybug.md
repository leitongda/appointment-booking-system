# P0 实施计划：平台公告 + 排班发布撤回 + SMS 配置

## Context

自适应多智能体研究团队评审产出的 P0 行动项，需要实施以下 3 个任务：
1. 平台公告管理（platform_announcements）— 新建 API 模块 + 列表页 + 表单页
2. 排班发布/撤回 — 扩展已有排班日历页面
3. SMS 配置 Tab — 扩展 settings.tsx

---

## Task 1: 平台公告管理（13h）

### 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| CREATE | `packages/api/src/modules/platform-announcement.ts` | API 模块（7 个函数 + 接口定义） |
| MODIFY | `packages/api/src/index.ts` | 导出新模块 |
| CREATE | `apps/admin/src/pages/platform/platform-announcement.tsx` | 列表页 |
| CREATE | `apps/admin/src/pages/platform/platform-announcement-form.tsx` | 表单页 |
| MODIFY | `apps/admin/config/routes/platform.ts` | 注册路由（3 条） |
| MODIFY | `apps/admin/src/access.ts` | 添加 `canPlatformAnnouncement` 权限 |

### 1.1 API 模块 (`packages/api/src/modules/platform-announcement.ts`)

参考 `content.ts` 的 Notice 模式，新建独立 API 模块。

接口定义（参考后端 `schemas/platform_announcement.py` 的 camelCase 字段）：
```typescript
export interface PlatformAnnouncement {
  id: string;
  title: string;
  content: string;
  targetType: 'all' | 'specific';
  targetTenantIds?: string[];
  status: 'draft' | 'published' | 'revoked';
  priority: number; // 0=普通, 1=重要, 2=紧急
  publishAt?: string;
  expireAt?: string;
  publisherId?: string;
  publisherName?: string;
  readCount: number;
  totalCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface PlatformAnnouncementCreateData {
  title: string;
  content: string;
  targetType?: 'all' | 'specific';
  targetTenantIds?: string[];
  priority?: number;
  publishAt?: string;
  expireAt?: string;
}
```

API 函数（7 个，匹配后端端点）：
```typescript
export const platformAnnouncementApi = {
  getList: (params?) => request.get('/platform-announcements', { params }),
  getDetail: (id: string) => request.get(`/platform-announcements/${id}`),
  create: (data: PlatformAnnouncementCreateData) => request.post('/platform-announcements', data),
  update: (id: string, data: Partial<PlatformAnnouncementCreateData>) => request.put(`/platform-announcements/${id}`, data),
  delete: (id: string) => request.delete(`/platform-announcements/${id}`),
  publish: (id: string) => request.post(`/platform-announcements/${id}/publish`),
  revoke: (id: string) => request.post(`/platform-announcements/${id}/revoke`),
};
```

在 `packages/api/src/index.ts` 添加导出：
```typescript
export { platformAnnouncementApi } from './modules/platform-announcement';
export type { PlatformAnnouncement, PlatformAnnouncementCreateData } from './modules/platform-announcement';
```

### 1.2 列表页 (`apps/admin/src/pages/platform/platform-announcement.tsx`)

参考 `content/notice.tsx`（53 行），使用标准 ProTable + useListPage 模式。

关键差异（与 notice.tsx 对比）：
- **状态用 string 枚举**（draft/published/revoked）而非 integer（0/1）
- **优先级列**：valueEnum `{ 0: '普通', 1: { text: '重要', status: 'Warning' }, 2: { text: '紧急', status: 'Error' } }`
- **操作列条件按钮**：draft 可编辑/发布/删除，published 可撤回，revoked 仅删除
- **使用 `createOperationColumn` 的 `extraButtons`** 实现发布/撤回按钮
- **发布/撤回使用 `useListPage` 的 `handleAction`** 方法

操作按钮逻辑：
```
draft:    [编辑] [发布] [删除]
published: [撤回]
revoked:  [删除]
```

发布/撤回使用 Popconfirm 轻量确认（非 ConfirmModal）。

### 1.3 表单页 (`apps/admin/src/pages/platform/platform-announcement-form.tsx`)

参考 `content/notice-form.tsx`（142 行），使用 FormPage + Card 模式。

表单字段：
- `title` — ProFormText（必填）
- `content` — ProFormTextArea 或 RichTextEditor（必填）
- `targetType` — ProFormSelect（all/specific）
- `targetTenantIds` — ProFormSelect 多选（仅 targetType=specific 时显示）
- `priority` — ProFormSelect（0/1/2）
- `publishAt` — ProFormDateTimePicker（可选）
- `expireAt` — ProFormDateTimePicker（可选）

不使用 switchFields（status 是 string 枚举，不是 boolean）。
编辑模式下若 status !== 'draft'，表单 disabled。

### 1.4 路由注册 (`apps/admin/config/routes/platform.ts`)

在 `platform` 路由的 `routes` 数组中添加：
```typescript
{
  path: '/platform/announcement',
  name: '平台公告',
  icon: 'notification',
  access: 'canPlatformAnnouncement',
  routes: [
    { path: '/platform/announcement', redirect: '/platform/announcement/list' },
    { path: '/platform/announcement/list', name: '公告列表', component: './platform/platform-announcement' },
    { path: '/platform/announcement/create', name: '发布公告', component: './platform/platform-announcement-form', hideInMenu: true },
    { path: '/platform/announcement/:id/edit', name: '编辑公告', component: './platform/platform-announcement-form', hideInMenu: true },
  ],
},
```

### 1.5 权限 (`apps/admin/src/access.ts`)

在 `canTenant` 附近添加：
```typescript
const canPlatformAnnouncement = isSuperAdmin || hasAnyPermission([
  'platform-announcement',
  'platform-announcement:list',
  'platform-announcement:create',
  'platform-announcement:publish',
  'platform-announcement:revoke',
  'platform-announcement:delete',
]);
```
返回对象中添加 `canPlatformAnnouncement`。

---

## Task 2: 排班发布/撤回（8h）

### 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| MODIFY | `packages/shared/src/types/schedule.ts` | 添加 scheduleStatus/publishStatus 字段 |
| MODIFY | `packages/api/src/modules/schedule.ts` | 添加 batchPublish/batchWithdraw/checkConflicts 方法 |
| MODIFY | `apps/admin/src/pages/schedule/calendar/index.tsx` | 添加发布/撤回按钮 + 确认弹窗 |
| MODIFY | `apps/admin/src/pages/schedule/calendar/components/DayDetailDrawer.tsx` | 显示发布状态 |

### 2.1 共享类型 (`packages/shared/src/types/schedule.ts`)

在 Schedule 接口中添加：
```typescript
scheduleStatus?: string;  // draft/published/booking/full/suspended/finished/withdrawn
publishStatus?: string;   // draft/published/withdrawn
```

### 2.2 API 方法 (`packages/api/src/modules/schedule.ts`)

在 `batchDelete` 方法后添加：
```typescript
batchPublish: (scheduleIds: string[]): Promise<{ success: boolean; affectedCount: number; message: string }> => {
  return request.post('/schedules/batch-publish', { schedule_ids: scheduleIds });
},

batchWithdraw: (scheduleIds: string[], reason?: string): Promise<{ success: boolean; affectedCount: number; message: string }> => {
  return request.post('/schedules/batch-withdraw', { schedule_ids: scheduleIds, reason });
},

checkConflicts: (data: {
  doctorId: string;
  scheduleDate: string;
  startTime?: string;
  endTime?: string;
  timeSlot?: string;
  storeId?: string;
  roomId?: string;
  excludeScheduleId?: string;
}): Promise<{ hasConflict: boolean; blocking: boolean; conflicts: Array<{ type: string; severity: string; message: string; details?: any }> }> => {
  return request.post('/schedules/conflicts', data);
},
```

### 2.3 日历页面修改 (`apps/admin/src/pages/schedule/calendar/index.tsx`)

**添加选择机制**：在 state 中添加 `selectedScheduleIds: string[]`，通过 Checkbox 选择排班。

**添加按钮到 action bar**（line 371-391 区域）：
```tsx
<Button
  icon={<CheckCircleOutlined />}
  onClick={handleBatchPublish}
  disabled={selectedScheduleIds.length === 0}
>
  发布
</Button>
<Button
  icon={<StopOutlined />}
  onClick={() => setWithdrawModalVisible(true)}
  disabled={selectedScheduleIds.length === 0}
>
  撤回
</Button>
```

**发布逻辑**：
- 调用 `scheduleApi.batchPublish(selectedScheduleIds)`
- 成功后 `message.success` + `refreshData()`
- 使用 Popconfirm 确认

**撤回逻辑**：
- 弹出 Modal 输入撤回原因（可选）
- 调用 `scheduleApi.batchWithdraw(selectedScheduleIds, reason)`
- 后端会检查是否有活跃预约，如有则返回失败项
- 展示结果：成功数/失败数/失败原因

**发布状态视觉指示**：
- 在排班单元格中添加状态 Tag：draft=灰色"草稿"、published=绿色"已发布"、withdrawn=红色"已撤回"
- 在 DayDetailDrawer 中显示每个排班的发布状态

### 2.4 DayDetailDrawer 修改

在每个排班的信息区域添加发布状态 Tag 显示。

---

## Task 3: SMS 配置 Tab（4h）

### 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| MODIFY | `apps/admin/src/pages/system/settings.tsx` | 添加 SMS Tab |
| MODIFY | `apps/admin/config/routes/system.ts` | 添加 SMS 路由 |

### 3.1 Settings.tsx 修改

**Tab 注册**（3 处 map 对象）：
```typescript
// TAB_PATH_TO_KEY 添加：
'/system/config/sms-config': 'sms',

// TAB_KEY_TO_PATH 添加：
sms: '/system/config/sms-config',

// TAB_KEY_TO_TITLE 添加：
sms: '短信配置',
```

**State + 权限**：
```typescript
const [smsConfig, setSmsConfig] = useState<SmsConfig | null>(null);
const canViewSms = access.hasPermission('settings:sms') || access.hasPermission('settings:edit');
const canEditSms = canViewSms;
```

**数据加载**（在 `loadSettings()` 的 `loaders` 数组中）：
```typescript
if (canViewSms) {
  loaders.push(settingsApi.getSmsConfig().then(setSmsConfig));
}
```

**提交处理**：
```typescript
async function handleSmsConfigSubmit(values: Partial<SmsConfig>) {
  try {
    await settingsApi.updateSmsConfig(values);
    message.success('保存成功');
    loadSettings();
  } catch (error) {
    message.error('保存失败');
  }
}
```

**Tab 内容**（参考 email Tab 模式，ProForm-based）：
```typescript
{
  key: 'sms',
  label: '短信配置',
  children: (
    <ProForm
      key={loading ? 'sms-loading' : 'sms-loaded'}
      onFinish={handleSmsConfigSubmit}
      initialValues={{ ...DEFAULT_SMS_CONFIG, ...smsConfig }}
      submitter={{ searchConfig: { submitText: '保存设置' }, resetButtonProps: { style: { display: 'none' } } }}
      disabled={!canEditSms}
    >
      <ProFormSelect name="smsProvider" label="短信服务商" options={[
        { label: '阿里云', value: 'aliyun' },
        { label: '腾讯云', value: 'tencent' },
        { label: '测试模式', value: 'mock' },
      ]} rules={[{ required: true }]} />
      <ProFormText name="accessKeyId" label="AccessKey ID" rules={[{ required: true }]} />
      <ProFormText.Password name="accessKeySecret" label="AccessKey Secret"
        fieldProps={{ autoComplete: 'new-password' }}
        extra="首次配置请输入密钥，已配置的显示为 ******" />
      <ProFormText name="signName" label="短信签名" rules={[{ required: true }]} />
      <ProFormText name="templateCode" label="模板编码" rules={[{ required: true }]} />
    </ProForm>
  ),
},
```

**visibleItems 过滤**：
```typescript
if (item.key === 'sms') return canViewSms;
```

### 3.2 路由注册 (`apps/admin/config/routes/system.ts`)

在 `system/config` 的 routes 数组中添加：
```typescript
{ path: '/system/config/sms-config', name: '短信配置', icon: 'message', component: './system/settings', access: 'canSmsConfig' },
```

在 `access.ts` 中添加 `canSmsConfig` 权限：
```typescript
const canSmsConfig = access.hasPermission('settings:sms') || access.hasPermission('settings:edit');
```

---

## 实施顺序

1. **Task 1: 平台公告** — 独立模块，无依赖，先做
2. **Task 3: SMS 配置** — 最简单（仅扩展现有页面），第二
3. **Task 2: 排班发布/撤回** — 涉及共享类型修改和复杂交互，最后

## 验证方式

1. **平台公告**：`pnpm dev:admin` 后登录平台管理员账号，访问 `/platform/announcement/list`，验证 CRUD + 发布/撤回流程
2. **SMS 配置**：访问 `/system/config/sms-config`，验证表单加载和保存
3. **排班发布/撤回**：访问排班日历，选择排班后点击发布/撤回按钮，验证状态变更和视觉指示
4. **Lint**：`pnpm lint` 确保无错误
