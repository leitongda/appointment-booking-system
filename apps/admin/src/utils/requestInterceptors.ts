import type { RequestConfig } from '@umijs/max';
import { getToken, handleTokenExpired, markAuthExpired, shouldSilenceAuthExpiredFeedback } from '@hospital/shared';
import { Modal, message, notification } from 'antd';
import { LOGIN_PATH } from '@/constants/paths';

/**
 * Handle structured error codes from the server's ErrorResponse envelope.
 * Returns `true` if the error was fully handled.
 */
const handleStructuredErrorCode = (data: any): boolean => {
  const errorCode = data?.error?.code;
  if (!errorCode) return false;

  const errorDetails = data?.error?.details;
  const errorMessage = data?.message;

  switch (errorCode) {
    case 'SCHEDULE_CONFLICT': {
      const conflicts = errorDetails?.conflicts as Array<{ message?: string }> | undefined;
      const conflictMessages = conflicts?.map(c => c.message).filter(Boolean);
      notification.warning({
        message: '排班冲突',
        description: conflictMessages?.length
          ? conflictMessages.join('\n')
          : errorMessage || '存在排班冲突，请调整后重试',
        duration: 6,
      });
      return true;
    }
    case 'PERMISSION_DENIED': {
      message.error(errorMessage || '权限不足，请联系管理员');
      return true;
    }
    case 'RATE_LIMITED': {
      notification.warning({
        message: '请求过于频繁',
        description: errorMessage || '请稍后再试',
        duration: 4,
      });
      return true;
    }
    default:
      return false;
  }
};

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

      // Structured error codes: handle before generic HTTP status checks
      if (data?.code && data.code >= 400 && handleStructuredErrorCode(data)) {
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
