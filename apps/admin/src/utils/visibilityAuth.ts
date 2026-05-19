import { adminApi } from '@hospital/api';
import { isTokenExpired, markAuthExpired, handleTokenExpired, getToken, isPublicEntryRoute } from '@hospital/shared';
import { Modal } from 'antd';
import { LOGIN_PATH } from '@/constants/paths';

const VISIBILITY_AUTH_CHECK_INTERVAL = 30 * 1000;

let cleanupVisibilityAuthCheck: (() => void) | null = null;
let isCheckingAuth = false;
let lastCheckedAt = 0;

const showTokenExpiredModal = (content = '您的登录已过期，请重新登录。') => {
  handleTokenExpired(() => {
    Modal.confirm({
      title: '登录已过期',
      content,
      okText: '重新登录',
      cancelButtonProps: { style: { display: 'none' } },
      closable: false,
      maskClosable: false,
      onOk: () => {
        Modal.destroyAll();
        window.location.href = LOGIN_PATH;
      },
    });
  });
};

/**
 * 监听浏览器 tab 切入事件，主动校验 JWT 是否过期
 *
 * 先通过客户端 exp 快速判断，未过期时再调用 /admin/me 让服务端确认登录态。
 * 服务端返回 401 时由全局响应拦截器统一弹窗和清理 token。
 */
export function initVisibilityAuthCheck(): () => void {
  cleanupVisibilityAuthCheck?.();

  const onVisibilityChange = async () => {
    if (document.visibilityState !== 'visible') return;
    if (isPublicEntryRoute()) return;
    if (!getToken()) return;

    if (isTokenExpired()) {
      markAuthExpired();
      showTokenExpiredModal();
      return;
    }

    const now = Date.now();
    if (isCheckingAuth || now - lastCheckedAt < VISIBILITY_AUTH_CHECK_INTERVAL) {
      return;
    }

    isCheckingAuth = true;
    lastCheckedAt = now;

    try {
      await adminApi.getCurrentAdmin();
    } catch {
      // 401/403/网络错误已由 @hospital/api 响应拦截器统一处理；这里避免未处理 Promise 报错。
    } finally {
      isCheckingAuth = false;
    }
  };

  document.addEventListener('visibilitychange', onVisibilityChange);

  cleanupVisibilityAuthCheck = () => {
    document.removeEventListener('visibilitychange', onVisibilityChange);
    if (cleanupVisibilityAuthCheck) {
      cleanupVisibilityAuthCheck = null;
    }
  };

  return cleanupVisibilityAuthCheck;
}
