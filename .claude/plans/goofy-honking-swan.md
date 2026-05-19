# 微信配置页门店下拉默认选中第一项

## Context

用户访问 `/system/config/wechat` 页面时，门店下拉为空白状态，页面显示"请先选择门店以查看或编辑微信配置"。需要在门店列表加载完成后自动选中第一项，减少一次无意义的点击。

## 现状分析

- 文件：`apps/admin/src/pages/system/settings.tsx`
- `selectedStoreId` 初始为 `''`（第 139 行）
- `stores` 通过 `loadStores()` 异步加载（第 216-231 行），在 `useEffect`（第 233 行）中触发
- 微信 tab 渲染时：`selectedStoreId` 为空则显示占位提示（第 936-939 行），非空则调用 `loadStoreWechatConfig` 加载配置
- 当前没有自动选中逻辑
- `Select` 组件支持 `allowClear`，用户可以手动清空选择

## 实施方案

### 修改文件

`apps/admin/src/pages/system/settings.tsx`

### 具体改动

在现有的两个 `useEffect`（第 233、240 行）之后，新增一个 `useEffect`：

```tsx
// 门店加载完成后，微信 tab 自动选中第一项
useEffect(() => {
  if (stores.length > 0 && !selectedStoreId && activeTab === 'wechat') {
    const firstStore = stores[0];
    setSelectedStoreId(firstStore.id);
    loadStoreWechatConfig(firstStore.id);
  }
}, [stores, activeTab]);
```

**逻辑说明：**
- 触发条件：`stores` 数组非空 + 当前未选中门店 + 当前在微信 tab
- `activeTab === 'wechat'` 避免在其他 tab 下触发不必要的 API 调用
- `!selectedStoreId` 确保用户手动选择/清空后不会被覆盖
- 依赖数组 `[stores, activeTab]` 覆盖两种场景：
  1. 用户已在微信 tab，stores 加载完成 → 自动选中
  2. stores 已加载，用户切换到微信 tab → 自动选中

**不影响的区域：**
- 预约规则 tab（使用 `selectedBookingStoreId`，独立状态，且有"全局配置（默认）"选项）
- 黑名单 tab（门店选择在黑名单新增弹窗内，独立逻辑）
- 用户点击 `allowClear` 清空后，`selectedStoreId` 变为 `''`，如果用户切换 tab 再切回来会重新触发选中（合理行为）

## 验证方式

1. 启动 dev server：`pnpm dev:admin`
2. 访问 `/system/config/wechat`，确认门店下拉自动选中第一项，表单直接显示
3. 切换到其他 tab 再切回微信 tab，确认门店仍保持选中
4. 点击下拉的清除按钮，确认可以清空选择并显示占位提示
5. 手动选择其他门店，确认切换正常
6. 访问 `/system/config/booking`，确认预约规则 tab 不受影响
