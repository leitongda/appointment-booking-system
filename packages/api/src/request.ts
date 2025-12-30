import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type { ApiResponse } from '@hospital/shared';

/**
 * API 业务错误类
 * 用于区分业务错误码和 HTTP 错误
 */
export class ApiError extends Error {
  /** 业务错误码 */
  code: number;
  /** 原始响应数据 */
  data: any;
  /** 请求 URL（用于判断是否是登录接口等） */
  url?: string;
  
  constructor(code: number, message: string, data?: any, url?: string) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.data = data;
    this.url = url;
  }
  
  /** 是否是未授权错误 (401) */
  isUnauthorized(): boolean {
    return this.code === 401;
  }
  
  /** 是否是禁止访问错误 (403) */
  isForbidden(): boolean {
    return this.code === 403;
  }
  
  /** 是否是未找到错误 (404) */
  isNotFound(): boolean {
    return this.code === 404;
  }
  
  /** 是否是服务器错误 (5xx) */
  isServerError(): boolean {
    return this.code >= 500 && this.code < 600;
  }
}

/**
 * HTTP 客户端接口
 * 用于支持自定义 HTTP 客户端（如小程序 Taro 适配器）
 */
export interface HttpClient {
  defaults: { baseURL?: string };
  get: <T = any>(url: string, config?: AxiosRequestConfig) => Promise<T>;
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => Promise<T>;
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => Promise<T>;
  delete: <T = any>(url: string, config?: AxiosRequestConfig) => Promise<T>;
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => Promise<T>;
  interceptors?: AxiosInstance['interceptors'];
}

// HTTP 客户端实例（可被替换为自定义实现）
let httpClient: HttpClient | null = null;

/**
 * 创建默认的 axios 实例
 * 注意：不设置 baseURL，由各端在初始化时通过 setBaseURL 设置
 */
const createDefaultInstance = (): AxiosInstance => {
  return axios.create({
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

// 默认的 axios 实例
const instance: AxiosInstance = createDefaultInstance();

// 请求拦截器
instance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Token 由各端自行设置
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
instance.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const { data } = response;
    
    // 如果 data 不是对象，直接返回
    if (!data || typeof data !== 'object') {
      return data;
    }
    
    // 业务错误 - 抛出 ApiError 以便各端进行精细化处理
    if (data.code && data.code !== 200) {
      const requestUrl = response.config?.url || '';
      return Promise.reject(new ApiError(data.code, data.message || '请求失败', data.data, requestUrl));
    }
    
    // 分页响应：包含 total 字段，返回 ProTable 直接可用的格式
    if ('total' in data && typeof data.total === 'number' && 'data' in data) {
      return {
        data: data.data,
        total: data.total,
        success: true,  // ProTable 需要的字段
        page: data.page ?? 1,
        pageSize: data.pageSize ?? data.page_size ?? 10,
      };
    }
    
    // 统一响应格式：包含 code 和 data 字段
    if ('code' in data && 'data' in data) {
      return data.data;
    }
    
    // 其他情况直接返回
    return data;
  },
  (error) => {
    // HTTP 错误
    // FastAPI HTTPException 格式: { detail: "错误信息" }
    // 统一响应格式: { code: 400, message: "error", data: { detail: "实际错误信息" } }
    const responseData = error.response?.data;
    const status = error.response?.status;
    const message = responseData?.detail || responseData?.data?.detail || responseData?.message || error.message || '网络错误';
    // 保存请求 URL，用于后续判断是否是登录接口等
    const requestUrl = error.config?.url || error.request?.responseURL || '';
    
    // 如果有 HTTP 状态码，使用 ApiError 以便统一处理
    if (status) {
      return Promise.reject(new ApiError(status, message, responseData?.data, requestUrl));
    }
    
    return Promise.reject(new Error(message));
  }
);

/**
 * 获取当前 HTTP 客户端
 * 如果设置了自定义客户端则返回自定义客户端，否则返回默认 axios 实例
 */
export const getHttpClient = (): HttpClient => {
  return httpClient || instance;
};

/**
 * 设置自定义 HTTP 客户端
 * 用于小程序等非浏览器环境，可以传入 Taro 适配器等自定义实现
 */
export const setHttpClient = (client: HttpClient) => {
  httpClient = client;
};

/**
 * 设置基础 URL
 * 必须在应用启动时调用此方法设置 API 前缀
 */
export const setBaseURL = (baseURL: string) => {
  const client = getHttpClient();
  client.defaults.baseURL = baseURL;
};

/**
 * 获取当前基础 URL
 */
export const getBaseURL = (): string => {
  return getHttpClient().defaults.baseURL || '';
};

/**
 * 设置请求拦截器（用于各端设置 Token）
 */
export const setRequestInterceptor = (
  onFulfilled: (config: InternalAxiosRequestConfig) => InternalAxiosRequestConfig,
  onRejected?: (error: any) => any
) => {
  instance.interceptors.request.use(onFulfilled, onRejected);
};

/**
 * 设置响应拦截器（用于各端处理错误）
 */
export const setResponseInterceptor = (
  onFulfilled?: (response: AxiosResponse) => any,
  onRejected?: (error: any) => any
) => {
  instance.interceptors.response.use(onFulfilled, onRejected);
};

/**
 * 封装请求方法
 * 自动使用当前配置的 HTTP 客户端（支持 Taro 适配器等自定义实现）
 */
const request = {
  get: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return getHttpClient().get(url, config);
  },
  
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return getHttpClient().post(url, data, config);
  },
  
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return getHttpClient().put(url, data, config);
  },
  
  delete: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return getHttpClient().delete(url, config);
  },
  
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return getHttpClient().patch(url, data, config);
  },
};

export { request };

// 默认导出 request 对象，确保所有模块使用 getHttpClient() 获取正确的客户端
export default request;

