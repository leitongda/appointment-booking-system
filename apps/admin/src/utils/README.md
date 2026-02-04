# Utils - 工具函数

## proTable.ts - ProTable 请求工具

提供 ProTable 的请求封装，支持错误重试、防抖、Loading 延迟等高级功能。

### 核心函数

#### toProTableResult

将 API 响应转换为 ProTable 需要的格式。

```typescript
// 支持数组或分页对象
const result = toProTableResult(apiResponse);
// 返回 { data: T[], success: boolean, total: number }
```

#### createListRequest

创建 ProTable 的 request 函数，自动处理参数转换和结果包装。

**基础配置**

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `paramTransform` | `function` | - | 参数转换函数 |
| `retryCount` | `number` | `0` | 错误重试次数 |
| `retryDelay` | `number` | `1000` | 重试间隔（毫秒） |
| `debounceWait` | `number` | - | 防抖等待时间（毫秒） |
| `loadingDelay` | `number` | `0` | Loading 延迟显示时间（毫秒） |
| `retryOnNetworkErrorOnly` | `boolean` | `true` | 仅在网络错误时重试 |
| `onError` | `function` | - | 错误回调函数 |

**使用示例**

```tsx
// 基础用法
<ProTable request={createListRequest(api.getList)} />

// 自定义参数转换
<ProTable request={createListRequest(api.getList, {
  paramTransform: (params) => ({ ...params, keyword: params.name }),
})} />

// 带重试和防抖
<ProTable request={createListRequest(api.getList, {
  retryCount: 2,       // 失败后重试 2 次
  retryDelay: 1000,    // 重试间隔 1 秒
  debounceWait: 300,   // 防抖 300ms
  loadingDelay: 200,   // loading 至少显示 200ms
})} />

// 向后兼容：直接传函数
<ProTable request={createListRequest(
  api.getList,
  (params) => ({ ...params, status: 1 })
)} />
```

**配置项详解**

| 功能 | 适用场景 | 示例 |
|------|----------|------|
| 错误重试 | 网络不稳定环境 | `retryCount: 3` |
| 防抖 | 搜索输入框 | `debounceWait: 300` |
| Loading 延迟 | 避免闪烁 | `loadingDelay: 200` |

---

## request.ts - API 请求配置

统一配置 `@hospital/api` 包的请求和响应拦截器。

### 功能

#### 1. 请求拦截器 (setupRequestInterceptor)

- **自动添加 Token**: 从 localStorage 读取 token 并添加到请求头 `Authorization: Bearer <token>`
- **错误处理**: 捕获并记录请求错误

#### 2. 响应拦截器 (setupResponseInterceptor)

统一处理以下错误情况：

| 状态码 | 处理方式 | 说明 |
|--------|---------|------|
| 401 | 清除 token，跳转登录页 | Token 过期或无效 |
| 403 | 显示错误提示 | 没有权限访问 |
| 404 | 显示错误提示 | 资源不存在 |
| 500+ | 显示错误提示 | 服务器错误 |
| 网络错误 | 显示错误提示 | 网络连接问题 |

### 使用方式

在应用启动时调用 `initApiConfig()` 初始化配置：

```typescript
// app.tsx
import { initApiConfig } from '@/utils/request';

// 初始化 API 请求配置（拦截器）
initApiConfig();
```

### 初始化时机

配置需要在以下时机之前初始化：
- 任何 API 调用之前
- 应用启动时（推荐在 `app.tsx` 顶部）

### 代码示例

```typescript
// apps/admin/src/app.tsx
import { initApiConfig } from '@/utils/request';

// 初始化配置
initApiConfig();

// 之后的所有 API 调用都会自动携带 token
export async function getInitialState() {
  const currentUser = await adminApi.getCurrentAdmin(); // 自动添加 token
  return { currentUser };
}
```

### 自定义配置

如果需要自定义拦截器行为，可以直接修改 `request.ts` 中的相关函数：

```typescript
// 自定义请求拦截器
export const setupRequestInterceptor = () => {
  setRequestInterceptor(
    (config: InternalAxiosRequestConfig) => {
      // 添加自定义逻辑
      const token = getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      
      // 添加其他自定义 header
      config.headers['X-Custom-Header'] = 'value';
      
      return config;
    },
    (error) => {
      // 自定义错误处理
      return Promise.reject(error);
    }
  );
};
```

### 注意事项

1. **单例模式**: `initApiConfig()` 只需调用一次，通常在应用启动时
2. **跨端使用**: 每个端（admin、doctor、patient-h5）都有独立的配置文件
3. **Token 管理**: Token 的存储和获取由 `@hospital/shared` 包统一管理
4. **错误提示**: 响应拦截器会自动处理常见错误，无需在每个 API 调用处重复处理

### 相关文件

- `apps/admin/src/utils/request.ts` - 机构端配置
- `apps/doctor/src/utils/request.ts` - 医生端配置  
- `apps/patient-h5/src/utils/request.ts` - 患者端 H5 配置
- `packages/api/src/request.ts` - 基础 axios 实例和配置方法
