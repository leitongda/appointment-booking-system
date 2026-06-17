# P1 行动计划：统一 ProTable request + 抽取 hooks

## Context

P0 行动已全部完成（类型修复、废弃 useDataCache/useRetry、debounce 统一、ImportExport fetch 迁移）。继续执行 P1 行动项，目标：统一 ProTable 数据请求模式、抽取可复用 hooks。

---

## P1-1：内联 request 迁移到 createListRequest（28 个文件，31 处）

### 目标

将 ProTable 的 `request={async (params) => {...}}` 内联写法统一为 `request={createListRequest(apiFn, transform?)}`，消除重复的参数转换逻辑。

### 分层策略

**A 类 -- 直接替换（~10 处）**：只有 `current/pageSize/rest` 解构 + `toProTableResult` 包装，无字段映射。
- 直接改为 `request={createListRequest(apiFn)}`
- 代表文件：`doctor/list.tsx`, `patient/index.tsx`, `medical-record/index.tsx`, `examination-report/index.tsx`

**B 类 -- 带简单字段转换（~12 处）**：需要重命名字段或 `|| undefined` 过滤。
- 使用 `createListRequest(apiFn, paramTransform)` 的 transform 函数参数
- 代表文件：`store/index.tsx` (name→keyword), `schedule/rest-day.tsx`, `system/booking-notice.tsx`

**C 类 -- 复杂转换/多 ProTable/特殊逻辑（~9 处）**：状态类型转换、多个独立 ProTable、fetchData 变量模式。
- 需逐个审查，部分可能不适合迁移
- 代表文件：`appointment/list.tsx` (status Number 转换), `patient/detail.tsx` (3 个 ProTable), `points/index.tsx` (2 个 ProTable), `approval/definitions/index.tsx` (fetchData 变量)

### 逐文件清单

| 文件 | 类型 | 备注 |
|------|------|------|
| `doctor/list.tsx:550` | A | 直接替换 |
| `patient/index.tsx:216` | A | 直接替换 |
| `medical-record/index.tsx:192` | A | 直接替换 |
| `examination-report/index.tsx:263` | A | 直接替换 |
| `waitlist/index.tsx:410` | A | 直接替换 |
| `system/checkin-audit-logs.tsx:109` | A | 直接替换 |
| `system/consultation-fee-types.tsx:73` | A | 直接替换 |
| `system/dictionaries/items.tsx:203` | A | 直接替换 |
| `schedule/custom.tsx:219` | A | 直接替换 |
| `schedule/detail/index.tsx:424` | A | 直接替换 |
| `store/index.tsx:401` | B | name→keyword |
| `store/fee-types.tsx:194` | B | 需审查字段映射 |
| `schedule/rest-day.tsx:136` | B | 需审查字段映射 |
| `schedule/rule/index.tsx:568` | B | 需审查字段映射 |
| `schedule/suspension.tsx:364` | B | 需审查字段映射 |
| `system/booking-notice.tsx:193` | B | 需审查字段映射 |
| `system/dictionaries/index.tsx:153` | B | 需审查字段映射 |
| `system/rule-set-audit.tsx:235` | B | 需审查字段映射 |
| `system/rule-sets.tsx:272` | B | 需审查字段映射 |
| `system/blacklist.tsx:194,238` | B | 2 处，需审查 |
| `department/index.tsx:482` | B | 需审查字段映射 |
| `doctor/booking-setting.tsx:103` | B | 需审查字段映射 |
| `appointment/list.tsx:423` | C | status Number 转换 + 多字段 undefined |
| `approval/definitions/index.tsx:234` | C | fetchData 变量模式 |
| `approval/instances/index.tsx:220` | C | fetchData 变量模式 |
| `patient/detail.tsx:404,438,496` | C | 3 个独立 ProTable |
| `points/index.tsx:225,249` | C | 2 个独立 ProTable |
| `doctor/components/DoctorAppointmentTab.tsx:217` | C | 子组件内 ProTable |

### 执行顺序

1. 先做 A 类（10 处）-- 纯机械替换，风险最低
2. 再做 B 类（12 处）-- 逐个审查字段映射
3. 最后评估 C 类（9 处）-- 部分可能保留现状

### 验证

- 每改 5 个文件跑一次 `tsc --noEmit`
- 改完后 `pnpm lint` 全量检查

---

## P1-2：抽取 useExport hook（3 处）

### 目标

封装"调 API 拿 blob → 创建临时 a 标签 → 触发下载"的导出模式。

### 当前 3 处实现

1. `tenant/detail.tsx` -- 导出租户数据
2. `schedule/statistics` -- 导出统计数据
3. `schedule/calendar` -- 导出排班日历

### 接口设计

```typescript
// apps/admin/src/hooks/useExport.ts
interface UseExportOptions {
  /** 导出 API 函数，接收参数返回 Blob */
  exportFn: (params?: any) => Promise<Blob>;
  /** 默认文件名 */
  defaultFilename?: string;
  /** 成功回调 */
  onSuccess?: () => void;
}

interface UseExportReturn {
  /** 是否正在导出 */
  exporting: boolean;
  /** 触发导出 */
  export: (params?: any) => Promise<void>;
}
```

### 迁移

将 3 处各自的 `handleExport` 函数替换为 `useExport` hook 调用。

---

## P1-3：setInterval 迁移评估（6 处）

### 分析结果

所有 6 处 setInterval 均已有正确的 `clearInterval` cleanup，无内存泄漏风险：

| 文件 | 间隔 | 用途 | 迁移价值 |
|------|------|------|----------|
| NotificationButton | 60s | 未读消息轮询 | 低 -- 已规范 |
| online-users #1 | 1s | TTL 倒计时 | 低 -- 已规范 |
| online-users #2 | 30s | 服务端数据刷新 | 低 -- 已规范 |
| screen #1 | 1s | 数字时钟 | 低 -- 已规范 |
| screen #2 | 4.5s | 模拟通知滚动 | 低 -- 已规范 |
| WechatLogin | 2s | 微信扫码状态轮询 | 低 -- 已规范 |

### 裁决

**跳过**。所有 setInterval 使用均已规范，cleanup 完整。迁移到 ahooks useInterval 不会消除 bug 或显著改善代码，ROI 低于其他 P1 项。

---

## P1-4：formValidators.ts 推广（待定）

需要先确认 formValidators.ts 的具体内容和 8 个内联校验表单页的匹配度。此行动优先级低于 P1-1 和 P1-2。

---

## 总体执行顺序

1. **P1-1 A 类**（10 处直接替换）-- 1h
2. **P1-2 useExport**（抽取 hook + 3 处迁移）-- 3h
3. **P1-1 B 类**（12 处带字段转换）-- 2h
4. **P1-1 C 类评估**（9 处复杂场景）-- 1h 审查，决定迁移范围
5. **P1-4 formValidators**（如时间允许）-- 2h

## 验证方式

- `cd apps/admin && npx tsc --noEmit` -- 类型检查
- `npx eslint src/pages/{modified-files}` -- lint 检查
- 启动 dev server 手动验证列表页数据加载正常
