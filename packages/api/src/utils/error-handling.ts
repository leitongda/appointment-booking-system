/**
 * 共享错误处理工具
 *
 * 提供跨端统一的 HTTP 错误消息映射、URL 路径解析、token 路径匹配、
 * 结构化错误码处理。各端通过传入 UI 依赖（message/notification）来
 * 避免硬绑定到特定 UI 库。
 */
import { ApiError } from '../request';

// ─── HTTP 错误消息映射 ──────────────────────────────────────────────

/**
 * HTTP 状态码 → 用户友好消息
 * 三端共享，新增状态码只需修改此处
 */
export const ERROR_MESSAGES: Record<number, string> = {
  400: '请求参数错误',
  401: '登录已过期，请重新登录',
  403: '没有权限访问该资源',
  404: '请求的资源不存在',
  405: '请求方法不被允许',
  408: '请求超时，请稍后重试',
  429: '请求过于频繁，请稍后重试',
  500: '服务器错误，请稍后重试',
  502: '网关错误，请稍后重试',
  503: '服务暂时不可用，请稍后重试',
  504: '网关超时，请稍后重试',
};

// ─── URL 路径工具 ───────────────────────────────────────────────────

/**
 * 从 URL 中提取 pathname，用于精确路径匹配
 * 支持相对路径和完整 URL
 */
export const getRequestPath = (url: string): string => {
  try {
    return new URL(url, window.location.origin).pathname;
  } catch {
    return url.split('?')[0];
  }
};

/**
 * 默认的 token 排除路径（认证相关端点）
 * 各端可在此基础上扩展
 */
export const DEFAULT_EXCLUDE_TOKEN_PATHS = [
  '/auth/login',
  '/auth/register',
];

/**
 * 检查是否需要添加 token
 * 使用精确路径匹配，避免 /auth/login 错误匹配 /auth/login-history
 *
 * @param url 请求 URL
 * @param excludePaths 不需要 token 的路径列表（默认使用 DEFAULT_EXCLUDE_TOKEN_PATHS）
 */
export const shouldAddToken = (
  url: string,
  excludePaths: string[] = DEFAULT_EXCLUDE_TOKEN_PATHS
): boolean => {
  const requestPath = getRequestPath(url);
  return !excludePaths.some(
    path => requestPath === path || requestPath.startsWith(path + '/')
  );
};

// ─── 结构化错误码处理 ──────────────────────────────────────────────

/**
 * UI 依赖接口 — 各端注入自己的 UI 组件方法
 * 避免共享包直接依赖 antd 或 antd-mobile
 */
export interface ErrorHandlingDeps {
  /** 显示错误消息（如 antd message.error） */
  showError: (msg: string) => void;
  /** 显示警告通知（如 antd notification.warning） */
  showWarning: (opts: { message: string; description?: string; duration?: number }) => void;
}

/**
 * 处理服务器返回的结构化错误码（SCHEDULE_CONFLICT, PERMISSION_DENIED 等）
 *
 * 返回 `true` 表示错误已完全处理（调用方应直接 reject），
 * 返回 `false` 表示调用方应继续通用错误处理。
 *
 * @param error ApiError 实例
 * @param deps UI 依赖（message/notification 方法）
 */
export const handleStructuredErrorCode = (
  error: ApiError,
  deps: ErrorHandlingDeps
): boolean => {
  const { errorCode, errorDetails, message: errorMessage } = error;
  if (!errorCode) return false;

  switch (errorCode) {
    // ── 排班冲突：展示冲突详情 ──
    case 'SCHEDULE_CONFLICT': {
      const rawConflicts = errorDetails?.conflicts;
      const conflicts = Array.isArray(rawConflicts)
        ? rawConflicts as Array<{ message?: string }>
        : undefined;
      const conflictMessages = conflicts?.map(c => c.message).filter(Boolean);
      deps.showWarning({
        message: '排班冲突',
        description: conflictMessages?.length
          ? conflictMessages.join('\n')
          : errorMessage || '存在排班冲突，请调整后重试',
        duration: 6,
      });
      return true;
    }

    // ── 权限不足 ──
    case 'PERMISSION_DENIED': {
      deps.showError(errorMessage || '权限不足，请联系管理员');
      return true;
    }

    // ── 频率限制 ──
    case 'RATE_LIMITED': {
      deps.showWarning({
        message: '请求过于频繁',
        description: errorMessage || '请稍后再试',
        duration: 4,
      });
      return true;
    }

    // ── 参数校验失败：展示字段级错误 ──
    case 'VALIDATION_ERROR': {
      const rawFields = errorDetails?.fields;
      const fields = Array.isArray(rawFields)
        ? rawFields as Array<{ field?: string; message?: string }>
        : undefined;
      if (fields?.length) {
        const fieldMsgs = fields.map(f => `${f.field}: ${f.message}`).join('\n');
        deps.showWarning({
          message: '参数校验失败',
          description: fieldMsgs,
          duration: 6,
        });
      } else {
        deps.showError(errorMessage || '请求参数错误');
      }
      return true;
    }

    // ── 租户状态错误（由各端在 403 分支处理，此处仅标记已处理） ──
    case 'TENANT_SUSPENDED':
    case 'TENANT_OVERDUE': {
      return true;
    }

    default:
      return false;
  }
};

// ─── RSA 解密错误检测 ──────────────────────────────────────────────

/**
 * 检测是否为 RSA 解密相关错误（登录接口自动重试场景）
 */
export const isRsaDecryptError = (message: string): boolean => {
  return (
    message.includes('解密失败') ||
    message.includes('密码解密失败') ||
    message.includes('RSA密钥不匹配') ||
    message.includes('Base64解码失败') ||
    message.includes('无法解码为UTF-8字符串')
  );
};

// ─── 网络错误处理 ──────────────────────────────────────────────────

/**
 * 处理网络层错误（超时、断网等）
 *
 * @param error 原始 Error 对象
 * @param showError UI 错误提示方法
 * @returns `true` 表示已处理
 */
export const handleNetworkError = (
  error: Error,
  showError: (msg: string) => void
): boolean => {
  if (error.message === 'Network Error') {
    showError('网络连接失败，请检查网络设置');
    return true;
  }
  if (error.message.includes('timeout')) {
    showError('请求超时，请稍后重试');
    return true;
  }
  return false;
};
