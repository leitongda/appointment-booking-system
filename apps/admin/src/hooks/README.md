# Hooks - 自定义 Hook

## useListPage - 列表页通用 Hook

封装列表页的通用逻辑，包括 actionRef、message、access、handleDelete 等。

### 配置选项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `deleteFn` | `(id: string) => Promise<any>` | - | 删除 API 函数 |
| `deleteSuccessText` | `string` | `'删除成功'` | 删除成功提示 |
| `deleteErrorText` | `string` | `'删除失败'` | 删除失败提示 |

### 返回值

| 属性 | 类型 | 说明 |
|------|------|------|
| `actionRef` | `RefObject<ActionType>` | ProTable actionRef |
| `message` | `MessageInstance` | Ant Design message API |
| `access` | `AccessType` | 权限对象 |
| `handleDelete` | `(id: string) => Promise<void>` | 通用删除处理函数 |
| `reload` | `() => void` | 刷新表格 |
| `handleAction` | `function` | 通用操作处理函数 |

### 使用示例

```tsx
import { useListPage } from '@/hooks/useListPage';
import { createListRequest } from '@/utils/proTable';

const NewsPage = () => {
  const { actionRef, handleDelete } = useListPage({
    deleteFn: contentApi.deleteNews,
  });

  return (
    <ProTable
      actionRef={actionRef}
      request={createListRequest(contentApi.getNewsList)}
      // ...
    />
  );
};
```

---

## useListRequest - 列表数据请求 Hook

基于 `@umijs/max` 的 `useRequest`，专门用于列表数据请求场景。
提供 SWR 缓存、屏幕聚焦刷新、轮询、防抖节流等功能。

### 配置选项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `cacheKey` | `string` | - | 缓存 key，设置后启用缓存 |
| `staleTime` | `number` | `5000` | 数据新鲜时间（毫秒） |
| `refreshOnWindowFocus` | `boolean` | `false` | 窗口聚焦时是否重新请求 |
| `focusTimespan` | `number` | `5000` | 聚焦刷新间隔（毫秒） |
| `manual` | `boolean` | `false` | 是否手动触发请求 |
| `retryCount` | `number` | `0` | 错误重试次数 |
| `retryInterval` | `number` | `1000` | 重试间隔（毫秒） |
| `loadingDelay` | `number` | `0` | Loading 延迟显示（毫秒） |
| `pollingInterval` | `number` | - | 轮询间隔（毫秒） |
| `pollingWhenHidden` | `boolean` | `true` | 页面隐藏时是否继续轮询 |
| `debounceWait` | `number` | - | 防抖等待时间（毫秒） |
| `throttleWait` | `number` | - | 节流等待时间（毫秒） |
| `onSuccess` | `function` | - | 成功回调 |
| `onError` | `function` | - | 失败回调 |
| `onFinally` | `function` | - | 完成回调 |

### 返回值

| 属性 | 类型 | 说明 |
|------|------|------|
| `data` | `TData` | 当前数据 |
| `loading` | `boolean` | 是否正在加载 |
| `error` | `Error` | 错误信息 |
| `run` | `function` | 手动触发请求 |
| `runAsync` | `function` | 手动触发请求（返回 Promise） |
| `refresh` | `function` | 刷新请求 |
| `refreshAsync` | `function` | 刷新请求（返回 Promise） |
| `cancel` | `function` | 取消请求 |
| `mutate` | `function` | 修改数据 |

### 使用场景

#### 1. 基础用法

```tsx
const { data, loading, refresh } = useListRequest(
  () => api.getDepartments()
);
```

#### 2. 带缓存和窗口聚焦刷新

适用于数据变化不频繁、希望减少重复请求的场景。

```tsx
const { data, loading } = useListRequest(
  () => api.getDepartments(),
  {
    cacheKey: 'department-list',
    staleTime: 60000,  // 1分钟内使用缓存
    refreshOnWindowFocus: true,  // 切换标签页后刷新
  }
);
```

#### 3. 轮询（实时数据）

适用于需要实时更新的场景，如签到队列、消息列表等。

```tsx
const { data, loading } = useListRequest(
  () => api.getQueue(),
  {
    pollingInterval: 5000,  // 5秒轮询
    pollingWhenHidden: false,  // 页面隐藏时暂停
    retryCount: 3,  // 错误重试
  }
);
```

#### 4. 手动触发 + 防抖（搜索）

适用于搜索输入框等需要防抖的场景。

```tsx
const { data, loading, run } = useListRequest(
  (keyword) => api.search({ keyword }),
  {
    manual: true,
    debounceWait: 300,
  }
);

// 在搜索框 onChange 时调用
<Input onChange={(e) => run(e.target.value)} />
```

#### 5. 与 ProTable 配合使用（dataSource 模式）

```tsx
const { data, loading, refresh } = useListRequest(
  () => api.getList(),
  { cacheKey: 'my-list' }
);

<ProTable
  dataSource={data?.items || []}
  loading={loading}
  search={false}  // dataSource 模式下需要禁用或手动处理搜索
  toolBarRender={() => [
    <Button onClick={refresh}>刷新</Button>
  ]}
/>
```

---

## usePaginatedRequest - 分页列表请求 Hook

专门用于分页列表场景，自动处理分页参数。

### 额外配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `defaultCurrent` | `number` | `1` | 默认当前页 |
| `defaultPageSize` | `number` | `10` | 默认每页条数 |

### 额外返回值

| 属性 | 类型 | 说明 |
|------|------|------|
| `pagination.current` | `number` | 当前页 |
| `pagination.pageSize` | `number` | 每页条数 |
| `pagination.total` | `number` | 总条数 |
| `pagination.totalPage` | `number` | 总页数 |
| `pagination.onChange` | `function` | 分页变化回调 |
| `pagination.changeCurrent` | `function` | 修改当前页 |
| `pagination.changePageSize` | `function` | 修改每页条数 |

### 使用示例

```tsx
import { usePaginatedRequest } from '@/hooks/useListRequest';

const { data, loading, pagination } = usePaginatedRequest(
  ({ page, pageSize }) => api.getList({ page, pageSize }),
  { defaultPageSize: 10 }
);

<ProTable
  dataSource={data?.items}
  loading={loading}
  pagination={{
    current: pagination.current,
    pageSize: pagination.pageSize,
    total: pagination.total,
    onChange: pagination.onChange,
  }}
/>
```

---

## 功能对比

| 功能 | useListPage | createListRequest | useListRequest |
|------|-------------|-------------------|----------------|
| actionRef 管理 | ✅ | - | - |
| 权限管理 | ✅ | - | - |
| 删除操作 | ✅ | - | - |
| 错误重试 | - | ✅ | ✅ |
| 防抖 | - | ✅ | ✅ |
| 节流 | - | - | ✅ |
| Loading 延迟 | - | ✅ | ✅ |
| 轮询 | - | ProTable 配置 | ✅ |
| SWR/缓存 | - | - | ✅ |
| 窗口聚焦刷新 | - | - | ✅ |

### 选择建议

1. **标准列表页**：使用 `useListPage` + `createListRequest`
2. **需要轮询的页面**：使用 `useListRequest` 配合 `pollingInterval`
3. **需要缓存的下拉选项**：使用 `useListRequest` 配合 `cacheKey`
4. **复杂场景（手动分页）**：使用 `usePaginatedRequest`
