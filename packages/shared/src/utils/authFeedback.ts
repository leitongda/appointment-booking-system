import { getToken } from './storage';

const AUTH_FEEDBACK_SILENT_PATHS = new Set(['/login', '/']);

const normalizePathname = (pathname?: string | null): string => {
  if (!pathname) return '';
  if (pathname === '/') return pathname;
  return pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
};

const getCurrentPathname = (pathname?: string | null): string => {
  if (pathname !== undefined) {
    return normalizePathname(pathname);
  }

  if (typeof window === 'undefined') {
    return '';
  }

  return normalizePathname(window.location.pathname);
};

/**
 * 当前路由是否属于公共入口页。
 * 在这些页面上，认证失败应尽量静默处理，避免重复打断用户。
 */
export const isPublicEntryRoute = (pathname?: string | null): boolean => {
  return AUTH_FEEDBACK_SILENT_PATHS.has(getCurrentPathname(pathname));
};

/**
 * 当前场景是否应该静默处理认证失效提示。
 * 适用于 401/未授权拦截器：
 * - 已位于公共入口页（/login、/）
 * - 本地已没有 token，说明退登流程已经开始或已完成
 */
export const shouldSilenceAuthExpiredFeedback = (pathname?: string | null): boolean => {
  return isPublicEntryRoute(pathname) || !getToken();
};
