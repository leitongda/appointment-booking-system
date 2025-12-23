/**
 * Taro 请求适配器
 * 将 Taro.request 封装为类 axios 接口，用于小程序环境
 */

import type { HttpClient } from '../request';

// Taro 类型声明（避免直接依赖 @tarojs/taro）
interface TaroRequestOption {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'OPTIONS' | 'HEAD';
  data?: any;
  header?: Record<string, string>;
  timeout?: number;
}

interface TaroRequestResult<T = any> {
  data: T;
  statusCode: number;
  header: Record<string, string>;
}

interface TaroStatic {
  request: <T = any>(option: TaroRequestOption) => Promise<TaroRequestResult<T>>;
  getStorageSync: (key: string) => string;
  setStorageSync: (key: string, value: string) => void;
}

// 拦截器类型
type RequestInterceptor = (config: TaroRequestOption) => TaroRequestOption;
type ResponseInterceptor<T = any> = (response: TaroRequestResult<T>) => any;
type ErrorInterceptor = (error: any) => any;

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

/**
 * 创建 Taro 请求适配器
 * @param Taro Taro 实例（需要在调用时传入，避免包依赖）
 * @param config 适配器配置
 */
export const createTaroAdapter = (Taro: TaroStatic, config: TaroAdapterConfig): HttpClient => {
  const { baseURL, timeout = 30000, headers: defaultHeaders = {} } = config;
  
  // 请求拦截器列表
  const requestInterceptors: { onFulfilled: RequestInterceptor; onRejected?: ErrorInterceptor }[] = [];
  // 响应拦截器列表
  const responseInterceptors: { onFulfilled?: ResponseInterceptor; onRejected?: ErrorInterceptor }[] = [];
  
  /**
   * 执行请求
   */
  const doRequest = async <T = any>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
    url: string,
    data?: any,
    customHeaders?: Record<string, string>
  ): Promise<T> => {
    // 构建请求配置
    let requestConfig: TaroRequestOption = {
      url: `${adapter.defaults.baseURL}${url}`,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        ...defaultHeaders,
        ...customHeaders,
      },
      timeout,
    };
    
    // 执行请求拦截器
    for (const interceptor of requestInterceptors) {
      try {
        requestConfig = interceptor.onFulfilled(requestConfig);
      } catch (error) {
        if (interceptor.onRejected) {
          return Promise.reject(interceptor.onRejected(error));
        }
        throw error;
      }
    }
    
    try {
      const response = await Taro.request<T>(requestConfig);
      
      // 执行响应拦截器
      let result: any = response;
      for (const interceptor of responseInterceptors) {
        if (interceptor.onFulfilled) {
          result = interceptor.onFulfilled(result);
        }
      }
      
      // 如果响应拦截器返回了处理后的数据，直接返回
      if (result !== response) {
        return result;
      }
      
      // 默认返回 data
      return response.data;
    } catch (error) {
      // 执行错误拦截器
      for (const interceptor of responseInterceptors) {
        if (interceptor.onRejected) {
          return Promise.reject(interceptor.onRejected(error));
        }
      }
      throw error;
    }
  };
  
  const adapter: HttpClient = {
    defaults: {
      baseURL,
    },
    
    get: <T = any>(url: string, config?: any): Promise<T> => {
      return doRequest<T>('GET', url, undefined, config?.headers);
    },
    
    post: <T = any>(url: string, data?: any, config?: any): Promise<T> => {
      return doRequest<T>('POST', url, data, config?.headers);
    },
    
    put: <T = any>(url: string, data?: any, config?: any): Promise<T> => {
      return doRequest<T>('PUT', url, data, config?.headers);
    },
    
    delete: <T = any>(url: string, config?: any): Promise<T> => {
      return doRequest<T>('DELETE', url, undefined, config?.headers);
    },
    
    patch: <T = any>(url: string, data?: any, config?: any): Promise<T> => {
      return doRequest<T>('PATCH', url, data, config?.headers);
    },
    
    // 拦截器（模拟 axios 接口）
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

