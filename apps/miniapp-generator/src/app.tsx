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
