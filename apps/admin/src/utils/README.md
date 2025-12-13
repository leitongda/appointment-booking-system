# Utils - 工具函数

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

