/**
 * Taro 请求适配器
 * 将 Taro.request 封装为类 axios 接口，用于小程序环境
 */

import type { HttpClient } from '../request';

type Awaitable<T> = T | Promise<T>;

/**
 * 将 params 对象序列化为 URL 查询字符串
 */
const serializeParams = (params: Record<string, any>): string => {
  const parts: string[] = [];
  for (const key in params) {
    const value = params[key];
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      value.forEach((v) => {
        if (v !== undefined && v !== null) {
          parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(v))}`);
        }
      });
    } else {
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
    }
  }
  return parts.join('&');
};

export interface TaroRequestOption {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'OPTIONS' | 'HEAD';
  data?: any;
  header?: Record<string, string>;
  timeout?: number;
  _relativeUrl?: string;
  _retry?: boolean;
  _skipAuthRefresh?: boolean;
  _storeIdInjected?: boolean;
}

interface TaroRequestResult<T = any> {
  data: T;
  statusCode: number;
  header: Record<string, string>;
  config?: TaroRequestOption;
}

interface TaroStatic {
  request: <T = any>(option: TaroRequestOption) => Promise<TaroRequestResult<T>>;
  getStorageSync: (key: string) => string;
  setStorageSync: (key: string, value: string) => void;
}

type RequestInterceptor = (config: TaroRequestOption) => Awaitable<TaroRequestOption>;
type ResponseInterceptor<T = any> = (response: TaroRequestResult<T>) => Awaitable<any>;
type ErrorInterceptor = (error: any) => Awaitable<any>;

/**
 * Taro 适配器配置
 */
export interface TaroAdapterConfig {
  /** API 基础 URL（如 https://api.example.com/api/v1） */
  baseURL: string;
  /** 请求超时时间（毫秒），默认 30000 */
  timeout?: number;
  /** 默认请求头 */
  headers?: Record<string, string>;
}

const isAbsoluteUrl = (url: string) => /^https?:\/\//.test(url);

const normalizeUrl = (baseURL: string, url: string) => {
  if (isAbsoluteUrl(url)) {
    return url;
  }

  return `${baseURL}${url}`;
};

/**
 * 创建 Taro 请求适配器
 * @param Taro Taro 实例（需要在调用时传入，避免包依赖）
 * @param config 适配器配置
 */
export const createTaroAdapter = (Taro: TaroStatic, config: TaroAdapterConfig): HttpClient => {
  const { baseURL, timeout = 30000, headers: defaultHeaders = {} } = config;

  const requestInterceptors: { onFulfilled: RequestInterceptor; onRejected?: ErrorInterceptor }[] = [];
  const responseInterceptors: { onFulfilled?: ResponseInterceptor; onRejected?: ErrorInterceptor }[] = [];

  const buildRequestConfig = (requestConfig: TaroRequestOption): TaroRequestOption => {
    const relativeUrl = requestConfig._relativeUrl || requestConfig.url;

    return {
      timeout,
      ...requestConfig,
      _relativeUrl: relativeUrl,
      url: normalizeUrl(adapter.defaults.baseURL || '', requestConfig.url),
      header: {
        'Content-Type': 'application/json',
        ...defaultHeaders,
        ...requestConfig.header,
      },
    };
  };

  const runRequestInterceptors = async (configToRun: TaroRequestOption) => {
    let currentConfig = configToRun;
    for (const interceptor of requestInterceptors) {
      try {
        currentConfig = await interceptor.onFulfilled(currentConfig);
      } catch (error) {
        if (interceptor.onRejected) {
          currentConfig = await interceptor.onRejected(error);
          continue;
        }
        throw error;
      }
    }
    return currentConfig;
  };

  const runResponseInterceptors = async <T = any>(response: TaroRequestResult<T>) => {
    let currentResult: any = response;
    for (const interceptor of responseInterceptors) {
      if (!interceptor.onFulfilled) continue;
      const nextResult = await interceptor.onFulfilled(currentResult);
      if (typeof nextResult !== 'undefined') {
        currentResult = nextResult;
      }
    }
    return currentResult;
  };

  const runErrorInterceptors = async (error: any) => {
    let currentError = error;
    for (const interceptor of responseInterceptors) {
      if (!interceptor.onRejected) continue;

      try {
        return await interceptor.onRejected(currentError);
      } catch (nextError) {
        currentError = nextError;
      }
    }

    throw currentError;
  };

  const execute = async <T = any>(requestConfig: TaroRequestOption): Promise<T> => {
    let preparedConfig = buildRequestConfig(requestConfig);
    preparedConfig = await runRequestInterceptors(preparedConfig);

    try {
      const response = await Taro.request<T>(preparedConfig);
      const responseWithConfig: TaroRequestResult<T> = {
        ...response,
        config: preparedConfig,
      };
      const result = await runResponseInterceptors(responseWithConfig);

      if (result !== responseWithConfig) {
        return result;
      }

      return responseWithConfig.data as T;
    } catch (error) {
      return runErrorInterceptors(error);
    }
  };

  const request = <T = any>(requestConfig: TaroRequestOption): Promise<T> => {
    return execute<T>(requestConfig);
  };

  const adapter: HttpClient = {
    defaults: {
      baseURL,
    },

    request,

    get: <T = any>(url: string, config?: any): Promise<T> => {
      let finalUrl = url;
      if (config?.params && typeof config.params === 'object') {
        const queryString = serializeParams(config.params);
        if (queryString) {
          const separator = url.includes('?') ? '&' : '?';
          finalUrl = `${url}${separator}${queryString}`;
        }
      }

      return execute<T>({
        url: finalUrl,
        method: 'GET',
        header: config?.headers,
      });
    },

    post: <T = any>(url: string, data?: any, config?: any): Promise<T> => {
      return execute<T>({
        url,
        method: 'POST',
        data,
        header: config?.headers,
      });
    },

    put: <T = any>(url: string, data?: any, config?: any): Promise<T> => {
      return execute<T>({
        url,
        method: 'PUT',
        data,
        header: config?.headers,
      });
    },

    delete: <T = any>(url: string, config?: any): Promise<T> => {
      let finalUrl = url;
      if (config?.params && typeof config.params === 'object') {
        const queryString = serializeParams(config.params);
        if (queryString) {
          const separator = url.includes('?') ? '&' : '?';
          finalUrl = `${url}${separator}${queryString}`;
        }
      }

      return execute<T>({
        url: finalUrl,
        method: 'DELETE',
        header: config?.headers,
      });
    },

    patch: <T = any>(url: string, data?: any, config?: any): Promise<T> => {
      return execute<T>({
        url,
        method: 'PATCH',
        data,
        header: config?.headers,
      });
    },

    interceptors: {
      request: {
        use: (onFulfilled: RequestInterceptor, onRejected?: ErrorInterceptor) => {
          requestInterceptors.push({ onFulfilled, onRejected });
          return requestInterceptors.length - 1;
        },
        eject: (id: number) => {
          requestInterceptors.splice(id, 1);
        },
        clear: () => {
          requestInterceptors.length = 0;
        },
      } as any,
      response: {
        use: (onFulfilled?: ResponseInterceptor, onRejected?: ErrorInterceptor) => {
          responseInterceptors.push({ onFulfilled, onRejected });
          return responseInterceptors.length - 1;
        },
        eject: (id: number) => {
          responseInterceptors.splice(id, 1);
        },
        clear: () => {
          responseInterceptors.length = 0;
        },
      } as any,
    },
  };

  return adapter;
};

/**
 * 从 Taro Storage 获取 Token
 */
export const getTaroToken = (Taro: TaroStatic, key: string = 'token'): string | null => {
  try {
    return Taro.getStorageSync(key) || null;
  } catch {
    return null;
  }
};

/**
 * 设置 Taro Storage Token
 */
export const setTaroToken = (Taro: TaroStatic, token: string, key: string = 'token'): void => {
  try {
    Taro.setStorageSync(key, token);
  } catch (error) {
    console.error('[TaroAdapter] Failed to save token:', error);
  }
};
