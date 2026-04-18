/**
 * 从后端错误响应中提取租户暂停原因
 *
 * 同时识别：
 * 1. 新的结构化 error_code（BusinessError → HTTPException detail dict）
 * 2. 旧版 detail 字符串匹配（向后兼容）
 */

import type { TenantSuspendReason } from './tenantStatus';

// 结构化错误码 → 暂停原因
const ERROR_CODE_MAP: Record<string, TenantSuspendReason> = {
  TENANT_DISABLED: 'disabled',
  TENANT_OVERDUE: 'overdue',
  TENANT_TRIAL_EXPIRED: 'trial_expired',
  TENANT_SUSPENDED_WRITE: 'overdue',
};

// 旧版 detail 字符串关键词
const DETAIL_PATTERNS: Array<{ pattern: RegExp; reason: TenantSuspendReason }> = [
  { pattern: /租户已欠费|欠费.*续费/, reason: 'overdue' },
  { pattern: /订阅已到期|到期.*续费/, reason: 'overdue' },
  { pattern: /试用期.*结束|试用.*到期/, reason: 'trial_expired' },
  { pattern: /租户已被禁用|机构已暂停/, reason: 'disabled' },
];

interface ParsedError {
  message?: string;
  error_code?: string;
  detail?: string;
  code?: number;
}

/**
 * 解析后端错误，返回租户暂停原因；若非租户相关错误返回 null
 */
export function parseTenantError(err: ParsedError | any): TenantSuspendReason | null {
  // 1. 优先识别结构化 error_code
  const errorCode = err?.error_code ?? err?.data?.error_code;
  if (errorCode && ERROR_CODE_MAP[errorCode]) {
    return ERROR_CODE_MAP[errorCode];
  }

  // 2. 回落到 detail / message 字符串匹配
  const text = err?.detail ?? err?.message ?? (typeof err === 'string' ? err : '');
  if (text && typeof text === 'string') {
    for (const { pattern, reason } of DETAIL_PATTERNS) {
      if (pattern.test(text)) return reason;
    }
  }

  return null;
}
