/**
 * 统一错误处理工具
 *
 * 提供统一的错误处理机制，确保所有错误都能得到正确的提示和处理
 */
import { App } from 'antd';
import { ApiError } from '@hospital/api';

/**
 * 错误级别
 */
export enum ErrorLevel {
  /** 信息 */
  INFO = 'info',
  /** 警告 */
  WARNING = 'warning',
  /** 错误 */
  ERROR = 'error',
}

/**
 * 错误上下文
 */
interface ErrorContext {
  /** 操作描述 */
  operation?: string;
  /** 附加信息 */
  extra?: Record<string, any>;
  /** 是否静默（不显示提示） */
  silent?: boolean;
  /** 自定义错误处理函数 */
  customHandler?: (error: Error) => void;
}

/**
 * 错误处理器类
 */
export class ErrorHandler {
  private static messageInstance: ReturnType<typeof App.useApp>['message'] | null = null;
  private static modalInstance: ReturnType<typeof App.useApp>['modal'] | null = null;
  private static notificationInstance: ReturnType<typeof App.useApp>['notification'] | null = null;

  /**
   * 初始化（从 App.useApp() 获取实例）
   */
  static init(app: ReturnType<typeof App.useApp>) {
    this.messageInstance = app.message;
    this.modalInstance = app.modal;
    this.notificationInstance = app.notification;
  }

  /**
   * 处理错误
   *
   * @param error 错误对象
   * @param context 错误上下文
   */
  static handle(error: unknown, context: ErrorContext = {}): void {
    const {
      operation = '操作',
      extra,
      silent = false,
      customHandler,
    } = context;

    // 如果有自定义处理函数，优先使用
    if (customHandler) {
      customHandler(error as Error);
      return;
    }

    // 静默模式，只记录日志不显示提示
    if (silent) {
      console.warn(`[${operation}] Silent error:`, error);
      return;
    }

    // 处理 ApiError
    if (error instanceof ApiError) {
      this.handleApiError(error, operation);
      return;
    }

    // 处理标准 Error
    if (error instanceof Error) {
      this.handleStandardError(error, operation);
      return;
    }

    // 处理未知错误
    this.handleUnknownError(error, operation);
  }

  /**
   * 处理 API 错误
   */
  private static handleApiError(error: ApiError, operation: string): void {
    const { message: messageApi } = this;

    // 401 未授权
    if (error.isUnauthorized()) {
      messageApi.error(error.message || '登录已过期，请重新登录');
      // 触发登出逻辑（由拦截器处理）
      return;
    }

    // 403 禁止访问
    if (error.isForbidden()) {
      messageApi.error(error.message || '没有权限执行此操作');
      return;
    }

    // 404 未找到
    if (error.isNotFound()) {
      messageApi.error(error.message || '请求的资源不存在');
      return;
    }

    // 429 请求过多
    if (error.code === 429) {
      messageApi.warning('请求过于频繁，请稍后重试');
      return;
    }

    // 5xx 服务器错误
    if (error.isServerError()) {
      messageApi.error(error.message || '服务器错误，请稍后重试');
      return;
    }

    // 其他业务错误
    if (error.message) {
      messageApi.error(error.message);
      return;
    }

    messageApi.error(`${operation}失败`);
  }

  /**
   * 处理标准错误
   */
  private static handleStandardError(error: Error, operation: string): void {
    const { message: messageApi } = this;

    // 网络错误
    if (error.message === 'Network Error') {
      messageApi.error('网络连接失败，请检查网络设置');
      return;
    }

    // 超时错误
    if (error.message.includes('timeout') || error.message.includes('超时')) {
      messageApi.error('请求超时，请稍后重试');
      return;
    }

    // 其他错误
    console.error(`[${operation}]`, error);
    messageApi.error(error.message || `${operation}失败`);
  }

  /**
   * 处理未知错误
   */
  private static handleUnknownError(error: unknown, operation: string): void {
    const { message: messageApi } = this;

    console.error(`[${operation}] Unknown error:`, error);
    messageApi.error(`${operation}失败，发生未知错误`);
  }

  /**
   * 异步操作的包装器，自动处理错误
   *
   * @param fn 异步函数
   * @param context 错误上下文
   * @returns 包装后的函数
   *
   * @example
   * ```tsx
   * const handleClick = withErrorHandling(async () => {
   *   await doctorApi.update(id, data);
   *   message.success('更新成功');
   * }, { operation: '更新医生信息' });
   * ```
   */
  static withErrorHandling<T extends any[], R>(
    fn: (...args: T) => Promise<R>,
    context: ErrorContext = {}
  ): (...args: T) => Promise<R | null> {
    return async (...args: T): Promise<R | null> => {
      try {
        return await fn(...args);
      } catch (error) {
        this.handle(error, context);
        return null;
      }
    };
  }

  /**
   * 获取 message 实例
   */
  private static get message() {
    if (!this.messageInstance) {
      console.warn('ErrorHandler not initialized. Call ErrorHandler.init() first.');
      return {
        error: console.error,
        warning: console.warn,
        info: console.info,
        success: console.log,
      };
    }
    return this.messageInstance;
  }

  /**
   * 获取 modal 实例
   */
  static get modal() {
    return this.modalInstance;
  }

  /**
   * 获取 notification 实例
   */
  static get notification() {
    return this.notificationInstance;
  }
}

/**
 * 错误处理 Hook
 *
 * 在组件中使用，自动初始化 ErrorHandler
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const errorHandler = useErrorHandler();
 *
 *   const handleClick = async () => {
 *     try {
 *       await someApi();
 *     } catch (error) {
 *       errorHandler.handle(error, { operation: '保存数据' });
 *     }
 *   };
 *
 *   return <button onClick={handleClick}>保存</button>;
 * }
 * ```
 */
export function useErrorHandler() {
  const app = App.useApp();

  // 初始化
  if (!ErrorHandler['messageInstance']) {
    ErrorHandler.init(app);
  }

  return {
    /**
     * 处理错误
     */
    handle: (error: unknown, context?: ErrorContext) => {
      ErrorHandler.handle(error, context);
    },

    /**
     * 创建带错误处理的异步函数
     */
    withErrorHandling: <T extends any[], R>(
      fn: (...args: T) => Promise<R>,
      context?: ErrorContext
    ) => {
      return ErrorHandler.withErrorHandling(fn, context);
    },

    /**
     * message 实例
     */
    message: app.message,

    /**
     * modal 实例
     */
    modal: app.modal,

    /**
     * notification 实例
     */
    notification: app.notification,
  };
}

/**
 * 快捷方法：带错误处理的异步操作
 *
 * @example
 * ```tsx
 * await safeAsync(doctorApi.update(id, data), {
 *   operation: '更新医生信息',
 *   onSuccess: () => message.success('更新成功'),
 * });
 * ```
 */
export async function safeAsync<T>(
  fn: () => Promise<T>,
  context: ErrorContext & { onSuccess?: (result: T) => void } = {}
): Promise<T | null> {
  const { operation = '操作', onSuccess, ...errorContext } = context;

  try {
    const result = await fn();
    onSuccess?.(result);
    return result;
  } catch (error) {
    ErrorHandler.handle(error, { ...errorContext, operation });
    return null;
  }
}
