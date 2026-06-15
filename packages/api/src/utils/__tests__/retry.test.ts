/**
 * 重试机制单元测试
 */

import { setupRetryInterceptor, withRetry } from '../retry';
import { axios } from 'axios';

describe('Retry Mechanism', () => {
  let axiosInstance: any;

  beforeEach(() => {
    // 创建 axios 实例
    axiosInstance = axios.create();
    // 设置重试拦截器
    setupRetryInterceptor(axiosInstance, {
      maxRetries: 3,
      retryDelay: 100, // 测试时使用较短的延迟
      logRetry: false, // 关闭日志
    });
  });

  test('should retry failed GET requests', async () => {
    let attemptCount = 0;

    // Mock 拦截器
    axiosInstance.interceptors.response.use(
      (response: any) => response,
      (error: any) => {
        attemptCount++;
        if (attemptCount < 3) {
          // 前两次返回 500 错误
          error.response = { status: 500 };
          return Promise.reject(error);
        }
        // 第三次返回成功
        return Promise.resolve({ data: { success: true } });
      }
    );

    const result = await axiosInstance.get('/test');
    expect(attemptCount).toBe(3);
  });

  test('should not retry non-idempotent requests', async () => {
    let attemptCount = 0;

    axiosInstance.interceptors.response.use(
      (response: any) => response,
      (error: any) => {
        attemptCount++;
        error.response = { status: 500 };
        return Promise.reject(error);
      }
    );

    try {
      await axiosInstance.post('/test', {});
    } catch (error) {
      // POST 请求不应该重试
      expect(attemptCount).toBe(1);
    }
  });

  test('should use exponential backoff', async () => {
    const delays: number[] = [];
    const originalSetTimeout = global.setTimeout;

    // Mock setTimeout 来捕获延迟时间
    global.setTimeout = jest.fn((callback, delay) => {
      delays.push(delay as number);
      return originalSetTimeout(callback, 0);
    } as any);

    let attemptCount = 0;
    axiosInstance.interceptors.response.use(
      (response: any) => response,
      (error: any) => {
        attemptCount++;
        if (attemptCount < 4) {
          error.response = { status: 500 };
          return Promise.reject(error);
        }
        return Promise.resolve({ data: { success: true } });
      }
    );

    try {
      await axiosInstance.get('/test');
    } catch (error) {
      // 验证指数退避：100, 200, 400
      expect(delays).toEqual([100, 200, 400]);
    }

    global.setTimeout = originalSetTimeout;
  });
});
