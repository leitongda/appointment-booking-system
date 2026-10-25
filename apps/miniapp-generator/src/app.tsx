import { PropsWithChildren } from 'react';
import Taro from '@tarojs/taro';
import { useLaunch } from '@tarojs/taro';
import { TemplateProvider } from './contexts/TemplateContext';
import { setHttpClient, createTaroAdapter } from '@hospital/api';
import { getToken } from './utils/auth';
import './app.less';

// API 适配器接线：与 patient-miniapp 同模式（Taro 适配器 + 统一 baseURL + 登录态头）。
// 缺此接线时 @hospital/api 走 axios 空壳，所有请求直接 reject，页面只能渲染空态。
const apiBaseUrl = process.env.TARO_APP_API_URL || 'http://localhost:9000/api/v1';

const taroAdapter = createTaroAdapter(Taro as any, {
  baseURL: apiBaseUrl,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

if (taroAdapter.interceptors) {
  taroAdapter.interceptors.request.use((config: any) => {
    const token = getToken();
    if (token && !config.header?.Authorization) {
      config.header = {
        ...config.header,
        Authorization: `Bearer ${token}`,
      };
    }
    // 公开接口（首页推荐/门店/评价等）按租户隔离，中间件要求携带租户头，缺失时 fail-closed 400
    const tenantCode = process.env.TARO_APP_TENANT_CODE || '';
    if (tenantCode && !config.header?.['X-Tenant-Code']) {
      config.header = {
        ...config.header,
        'X-Tenant-Code': tenantCode,
      };
    }
    return config;
  });

  // 响应解包：与 patient-miniapp 同款。后端 UnifiedResponse 包裹为 {code,message,data}，
  // 分页接口为 {code,data,total,...}——不解包则业务层拿到的是包装对象
  taroAdapter.interceptors.response.use((response: any) => {
    const data = response?.data ?? response;
    if (data && typeof data === 'object' && 'code' in data && 'data' in data) {
      if ('total' in data && typeof data.total === 'number') {
        return {
          data: data.data,
          total: data.total,
          success: true,
          page: data.page ?? 1,
          pageSize: data.pageSize ?? data.page_size ?? 10,
        };
      }
      return data.data;
    }
    return data;
  });
}

setHttpClient(taroAdapter);

function App({ children }: PropsWithChildren) {
  useLaunch(() => {
    console.log('[miniapp-generator] template:', process.env.TARO_APP_TEMPLATE_CODE || 'modern-general');
    console.log('[miniapp-generator] version:', process.env.TARO_APP_TEMPLATE_VERSION || '1.0.0');
    console.log('[miniapp-generator] apiBaseUrl:', apiBaseUrl);
  });

  return (
    <TemplateProvider>
      {children}
    </TemplateProvider>
  );
}

export default App;
