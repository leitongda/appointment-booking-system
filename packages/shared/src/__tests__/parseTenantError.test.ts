import { describe, expect, it } from 'vitest';
import { parseTenantError } from '../utils/parseTenantError';

// ---------------------------------------------------------------------------
// R4-9：前端统一读取后端结构化信封的 error.code
// 后端信封：{ code: 403, message, error: { code: 'TENANT_OVERDUE', message } }
// ---------------------------------------------------------------------------

describe('parseTenantError - structured error.code envelope', () => {
  it('reads error.code from the backend structured envelope', () => {
    expect(
      parseTenantError({
        code: 403,
        message: '租户已欠费',
        error: { code: 'TENANT_OVERDUE', message: '租户已欠费' },
      }),
    ).toBe('overdue');
  });

  it('reads error.code when the envelope is nested under data', () => {
    expect(
      parseTenantError({
        data: { code: 403, error: { code: 'TENANT_DISABLED' } },
      }),
    ).toBe('disabled');
  });

  it('reads error.code from a raw axios error (response.data)', () => {
    expect(
      parseTenantError({
        message: 'Request failed with status code 403',
        response: { data: { code: 403, error: { code: 'TENANT_TRIAL_EXPIRED' } } },
      }),
    ).toBe('trial_expired');
  });

  it('maps TENANT_SUSPENDED_WRITE to overdue', () => {
    expect(
      parseTenantError({ code: 403, error: { code: 'TENANT_SUSPENDED_WRITE' } }),
    ).toBe('overdue');
  });
});

describe('parseTenantError - legacy sources', () => {
  it('reads the ApiError.errorCode field', () => {
    expect(parseTenantError({ code: 403, errorCode: 'TENANT_OVERDUE' })).toBe('overdue');
  });

  it('reads the legacy flat error_code field', () => {
    expect(parseTenantError({ error_code: 'TENANT_DISABLED' })).toBe('disabled');
  });

  it('reads the legacy flat error_code nested under data', () => {
    expect(parseTenantError({ data: { error_code: 'TENANT_TRIAL_EXPIRED' } })).toBe(
      'trial_expired',
    );
  });

  it('falls back to detail string matching', () => {
    expect(parseTenantError({ detail: '租户已欠费，请续费后继续使用' })).toBe('overdue');
  });

  it('falls back to message string matching', () => {
    expect(parseTenantError({ message: '试用期已结束' })).toBe('trial_expired');
  });

  it('prefers the backend message over the generic axios message', () => {
    expect(
      parseTenantError({
        message: 'Request failed with status code 403',
        response: { data: { message: '租户已欠费，请续费' } },
      }),
    ).toBe('overdue');
  });

  it('handles a plain string error', () => {
    expect(parseTenantError('机构已暂停服务')).toBe('disabled');
  });
});

describe('parseTenantError - non-tenant errors', () => {
  it('returns null for unrelated structured codes', () => {
    expect(parseTenantError({ code: 403, error: { code: 'PERMISSION_DENIED' } })).toBeNull();
  });

  it('returns null for unrelated messages', () => {
    expect(parseTenantError({ message: '请求参数错误' })).toBeNull();
  });

  it('returns null for empty / null input', () => {
    expect(parseTenantError(null)).toBeNull();
    expect(parseTenantError(undefined)).toBeNull();
  });
});
