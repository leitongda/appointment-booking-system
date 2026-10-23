/**
 * R4-9：403 + 租户暂停必须触发 onTenantSuspended（先于结构化错误码分支）。
 *
 * 覆盖两条拦截路径：
 * - ApiError 路径（request.ts 已将 error.code 归一化到 errorCode）
 * - 原始 Axios 路径（响应体 { code, error: { code } }）
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { state } = vi.hoisted(() => ({
  state: {
    rejected: null as null | ((error: any) => any),
  },
}));

vi.mock('../../request', () => {
  class ApiError extends Error {
    code: number;
    data: any;
    url?: string;
    errorCode?: string;
    errorDetails?: Record<string, any>;

    constructor(
      code: number,
      message: string,
      data?: any,
      url?: string,
      errorCode?: string,
      errorDetails?: Record<string, any>,
    ) {
      super(message);
      this.name = 'ApiError';
      this.code = code;
      this.data = data;
      this.url = url;
      this.errorCode = errorCode;
      this.errorDetails = errorDetails;
    }

    isUnauthorized() {
      return this.code === 401;
    }
    isForbidden() {
      return this.code === 403;
    }
    isNotFound() {
      return this.code === 404;
    }
    isServerError() {
      return this.code >= 500 && this.code < 600;
    }
  }

  return {
    ApiError,
    setRequestInterceptor: vi.fn(),
    setResponseInterceptor: vi.fn((_onFulfilled: any, onRejected: (error: any) => any) => {
      state.rejected = onRejected;
    }),
  };
});

import { ApiError } from '../../request';
import { createWebInterceptors } from '../../web-interceptors';

const setup = () => {
  const showError = vi.fn();
  const showWarning = vi.fn();
  const onTenantSuspended = vi.fn();

  createWebInterceptors({
    excludeTokenPaths: [],
    deps: { showError, showWarning },
    onTenantSuspended,
    useStructuredErrorCode: true, // 复现 admin 的接线
  }).apply();

  return { showError, showWarning, onTenantSuspended, rejected: state.rejected! };
};

describe('403 tenant suspension (R4-9)', () => {
  beforeEach(() => {
    state.rejected = null;
  });

  it('ApiError path: TENANT_OVERDUE triggers onTenantSuspended even with structured handling on', async () => {
    const { rejected, onTenantSuspended } = setup();

    await expect(
      Promise.resolve().then(() =>
        rejected(new ApiError(403, '租户已欠费', undefined, '/api/v1/x', 'TENANT_OVERDUE')),
      ),
    ).rejects.toBeInstanceOf(ApiError);

    expect(onTenantSuspended).toHaveBeenCalledTimes(1);
    expect(onTenantSuspended.mock.calls[0][0].reason).toBe('overdue');
  });

  it('raw axios path: {code:403,error:{code:TENANT_OVERDUE}} triggers onTenantSuspended', async () => {
    const { rejected, onTenantSuspended } = setup();

    const axiosError = {
      response: {
        status: 403,
        data: {
          code: 403,
          message: '租户已欠费',
          error: { code: 'TENANT_OVERDUE', message: '租户已欠费' },
        },
      },
      config: { url: '/api/v1/x' },
      message: 'Request failed with status code 403',
    };

    await expect(Promise.resolve().then(() => rejected(axiosError))).rejects.toBeTruthy();

    expect(onTenantSuspended).toHaveBeenCalledTimes(1);
    expect(onTenantSuspended.mock.calls[0][0].reason).toBe('overdue');
  });

  it('non-tenant 403 (PERMISSION_DENIED) does not trigger onTenantSuspended', async () => {
    const { rejected, onTenantSuspended, showError } = setup();

    await expect(
      Promise.resolve().then(() =>
        rejected(new ApiError(403, '权限不足', undefined, '/api/v1/x', 'PERMISSION_DENIED')),
      ),
    ).rejects.toBeInstanceOf(ApiError);

    expect(onTenantSuspended).not.toHaveBeenCalled();
    expect(showError).toHaveBeenCalledWith('权限不足');
  });
});
