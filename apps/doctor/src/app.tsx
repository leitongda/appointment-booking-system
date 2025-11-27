import { message } from 'antd';
import type { RunTimeLayoutConfig } from 'umi';
import { history } from 'umi';
import { getToken, removeToken } from '@hospital/shared';

export async function getInitialState(): Promise<{ currentUser?: any }> {
  const token = getToken();
  if (!token) return {};
  return { currentUser: undefined };
}

export const layout: RunTimeLayoutConfig = ({ initialState }) => {
  return {
    logo: '/logo.svg',
    menu: { locale: false },
    onPageChange: () => {
      if (!initialState?.currentUser && location.pathname !== '/login') {
        history.push('/login');
      }
    },
  };
};

export const request = {
  timeout: 30000,
  requestInterceptors: [(config: any) => {
    const token = getToken();
    if (token) config.headers = { ...config.headers, Authorization: `Bearer ${token}` };
    return config;
  }],
  responseInterceptors: [(response: any) => {
    if (response.data?.code === 401) { removeToken(); history.push('/login'); }
    if (response.data?.code !== 200) message.error(response.data?.message);
    return response;
  }],
};

