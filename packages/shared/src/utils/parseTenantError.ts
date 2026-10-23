/**
 * 从后端错误响应中提取租户暂停原因
 *
 * 同时识别：
 * 1. 后端统一结构化信封 `{ code, message, error: { code, message, details } }`
 *    中的 `error.code`（BusinessError → HTTPException detail dict）
 * 2. 旧版扁平 `error_code` 字段（向后兼容）
 * 3. 旧版 detail / message 字符串匹配（向后兼容）
 *
 * 注意：后端自 P4 起把机器可读错误码放在 `error.code`，而 `code` 是 HTTP
 * 状态码。历史前端只读 `error_code`，导致 403 + TENANT_OVERDUE 无法识别。
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
 * 从各种错误形态中取出机器可读错误码。
 *
 * 兼容的形态：
 * - ApiError（packages/api 已把 `error.code` / `error_code` 归一化到 `errorCode`）
 * - 后端结构化信封 `{ code: 403, error: { code: 'TENANT_OVERDUE' } }`
 * - 旧版扁平字段 `{ error_code: 'TENANT_OVERDUE' }`（可能挂在 `data` 下）
 * - 原始 Axios error（响应体在 `response.data`）
 */
function extractErrorCode(err: any): string | null {
  if (!err) return null;

  const candidates = [
    err.errorCode,                          // ApiError
    err.error_code,                         // 旧版扁平字段
    err.data?.error_code,                   // 旧版扁平字段（响应体）
    err.data?.error?.code,                  // 后端结构化信封（响应体）
    err.error?.code,                        // 已解包的结构化信封
    err.response?.data?.error?.code,        // 原始 Axios error
    err.response?.data?.error_code,         // 原始 Axios error（旧版）
  ];

  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.length > 0) {
      return candidate;
    }
  }
  return null;
}

/**
 * 解析后端错误，返回租户暂停原因；若非租户相关错误返回 null
 */
export function parseTenantError(err: ParsedError | any): TenantSuspendReason | null {
  // 1. 优先识别结构化错误码（统一读 error.code，兼容旧版 error_code）
  const errorCode = extractErrorCode(err);
  if (errorCode && ERROR_CODE_MAP[errorCode]) {
    return ERROR_CODE_MAP[errorCode];
  }

  // 2. 回落到 detail / message 字符串匹配
  //    message 放在响应体之后，避免原始 Axios error 的
  //    "Request failed with status code 403" 抢先匹配并吞掉后端文案。
  const text =
    err?.detail ??
    err?.data?.detail ??
    err?.data?.message ??
    err?.response?.data?.detail ??
    err?.response?.data?.message ??
    err?.message ??
    (typeof err === 'string' ? err : '');
  if (text && typeof text === 'string') {
    for (const { pattern, reason } of DETAIL_PATTERNS) {
      if (pattern.test(text)) return reason;
    }
  }

  return null;
}
