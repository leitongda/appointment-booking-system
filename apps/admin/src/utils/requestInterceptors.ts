import type { RequestConfig } from '@umijs/max';
import { getToken, handleTokenExpired, markAuthExpired, shouldSilenceAuthExpiredFeedback } from '@hospital/shared';
import { Modal, message } from 'antd';
import { LOGIN_PATH } from '@/constants/paths';

export const umiRequestConfig: RequestConfig = {
  timeout: 30000,
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
      const { data, status } = response;

      if (status === 401 || data?.code === 401) {
        if (shouldSilenceAuthExpiredFeedback()) {
          if (getToken()) {
            markAuthExpired();
            handleTokenExpired();
          }
          return response;
        }
        markAuthExpired();
        handleTokenExpired(() => {
          Modal.confirm({
            title: '登录已过期',
            content: data?.message || '您的登录已失效，请重新登录。',
            okText: '重新登录',
            cancelButtonProps: { style: { display: 'none' } },
            closable: false,
            maskClosable: false,
            onOk: () => {
              window.location.href = LOGIN_PATH;
            },
          });
        });
        return response;
      }

      if (data?.code === 403) {
        message.error(data?.message || '没有权限访问该资源');
        return response;
      }

      if (data?.code === 404) {
        message.error(data?.message || '请求的资源不存在');
        return response;
      }

      if (data?.code && data.code !== 200 && data.code >= 400) {
        message.error(data?.message || '请求失败');
        return response;
      }

      return response;
    },
  ],
};
