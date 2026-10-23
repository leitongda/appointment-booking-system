/**
 * 重试机制单元测试
 *
 * 通过自定义 axios adapter 驱动真实拦截器链（请求拦截器分配 retryId、
 * 响应拦截器按幂等性 + 错误类型决定重试），验证 setupRetryInterceptor 的行为。
 */

import axios from 'axios';
import { vi } from 'vitest';
import { setupRetryInterceptor, withRetry } from '../retry';

/** 造一个「前 failTimes 次返回 status，之后成功」的 adapter，并记录调用次数 */
function createFlakyAdapter(failTimes: number, status = 500) {
  let calls = 0;
  const adapter = {
    calls: () => calls,
    fn: async (config: any) => {
      calls++;
      if (calls <= failTimes) {
        const error: any = new Error(`Request failed with status code ${status}`);
        error.config = config;
        error.response = { status, data: {}, headers: {}, config };
        throw error;
      }
      return {
        data: { success: true },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      };
    },
  };
  return adapter;
}

function createInstance(adapter: any) {
  const instance = axios.create({ adapter: adapter.fn as any });
  setupRetryInterceptor(instance, {
    maxRetries: 3,
    retryDelay: 100,
    retryDelayFactor: 2,
    enableJitter: false,
    logRetry: false,
    enableCircuitBreaker: false,
  });
  return instance;
}

describe('Retry Mechanism', () => {
  test('should retry failed GET requests until success', async () => {
    const adapter = createFlakyAdapter(2);
    const instance = createInstance(adapter);

    const response = await instance.get('/test');

    expect(response.data).toEqual({ success: true });
    // 2 次失败 + 1 次成功
    expect(adapter.calls()).toBe(3);
  });

  test('should not retry non-idempotent requests', async () => {
    const adapter = createFlakyAdapter(3);
    const instance = createInstance(adapter);

    await expect(instance.post('/test', {})).rejects.toMatchObject({
      response: { status: 500 },
    });
    // POST 非幂等，失败后不重试
    expect(adapter.calls()).toBe(1);
  });

  test('should never retry 401/403 even for GET', async () => {
    const adapter = createFlakyAdapter(3, 403);
    const instance = createInstance(adapter);

    await expect(instance.get('/test')).rejects.toMatchObject({
      response: { status: 403 },
    });
    expect(adapter.calls()).toBe(1);
  });

  test('should give up after maxRetries', async () => {
    const adapter = createFlakyAdapter(99);
    const instance = createInstance(adapter);

    await expect(instance.get('/test')).rejects.toMatchObject({
      response: { status: 500 },
    });
    // 1 次原始请求 + 3 次重试
    expect(adapter.calls()).toBe(4);
  });

  test('should use exponential backoff', async () => {
    const delays: number[] = [];
    const originalSetTimeout = global.setTimeout;
    // 记录 retry.ts 期望的延迟，但用 0ms 真实执行，避免测试耗时
    const spy = vi.spyOn(global, 'setTimeout').mockImplementation(
      ((callback: any, ms?: any, ...rest: any[]) => {
        delays.push(Number(ms) || 0);
        return originalSetTimeout(callback, 0, ...rest);
      }) as any,
    );

    try {
      const adapter = createFlakyAdapter(99); // 永远失败 → 触发全部退避梯度
      const instance = createInstance(adapter);
      await expect(instance.get('/test')).rejects.toBeTruthy();
    } finally {
      spy.mockRestore();
    }

    // retryDelay=100、factor=2、无 jitter：100ms → 200ms → 400ms
    expect(delays).toEqual([100, 200, 400]);
  });

  test('withRetry marks idempotent methods and carries custom options', () => {
    const config = withRetry({ maxRetries: 5, retryDelay: 10 });
    expect((config as any)._isIdempotent).toBe(true);
    expect((config as any)._retryOptions).toMatchObject({ maxRetries: 5, retryDelay: 10 });

    const postConfig = withRetry({ method: 'POST', url: '/x' });
    expect((postConfig as any)._isIdempotent).toBe(false);
  });
});
