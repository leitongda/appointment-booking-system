import { message } from 'antd';
import type { RequestConfig, RunTimeLayoutConfig } from 'umi';
import { history } from 'umi';
import { getToken, removeToken } from '@hospital/shared';

/**
 * 初始化状态
 */
export async function getInitialState(): Promise<{
  currentUser?: API.User;
}> {
  const token = getToken();
  if (!token) {
    return {};
  }
  
  try {
    // TODO: 获取用户信息
    return {
      currentUser: undefined,
    };
  } catch (error) {
    return {};
  }
}

/**
 * Layout 配置
 */
export const layout: RunTimeLayoutConfig = ({ initialState }) => {
  return {
    logo: '/logo.svg',
    menu: {
      locale: false,
    },
    rightContentRender: () => null,
    onPageChange: () => {
      const { location } = history;
      // 如果没有登录，重定向到登录页
      if (!initialState?.currentUser && location.pathname !== '/login') {
        history.push('/login');
      }
    },
  };
};

/**
 * Request 配置
 */
export const request: RequestConfig = {
  timeout: 30000,
  errorConfig: {
    errorHandler: (error: any) => {
      message.error(error.message || '请求失败');
    },
  },
  requestInterceptors: [
    (config: any) => {
      const token = getToken();
      if (token) {
        config.headers = {
          ...config.headers,
          Authorization: `Bearer ${token}`,
        };
      }
      return config;
    },
  ],
  responseInterceptors: [
    (response: any) => {
      const { data } = response;
      
      if (data?.code === 401) {
        removeToken();
        history.push('/login');
        return response;
      }
      
      if (data?.code !== 200) {
        message.error(data?.message || '请求失败');
      }
      
      return response;
    },
  ],
};

// API 类型定义
declare namespace API {
  interface User {
    id: string;
    phone: string;
    name: string;
    avatar?: string;
    role: string;
  }
}

