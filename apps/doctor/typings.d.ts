declare module '*.css';
declare module '*.less';
declare module '*.scss';
declare module '*.svg';
declare module '*.png';
declare module '*.jpg';
declare module '*.jpeg';
declare module '*.gif';

// UmiJS 类型声明（修复类型检查问题）
declare module '@umijs/max' {
  export function defineConfig(config: any): any;
  export const history: any;
  export function useModel(namespace: string): any;
  export function useAccess(): any;
  export function useLocation(): any;
  export function useParams(): any;
  export function useSearchParams(): any;
  export function useRequest<TData, TParams extends any[]>(
    service: any,
    options?: any
  ): any;
  export const request: any;
  export type RequestConfig = any;
  export type RunTimeLayoutConfig = any;
  export const Outlet: any;
}

// umi 模块声明（兼容旧导入路径）
declare module 'umi' {
  export * from '@umijs/max';
}

// axios 模块声明（pnpm 严格模式下可能找不到类型）
declare module 'axios' {
  export interface AxiosRequestConfig {
    url?: string;
    method?: string;
    baseURL?: string;
    headers?: Record<string, any>;
    params?: any;
    data?: any;
    timeout?: number;
    [key: string]: any;
  }
  export interface AxiosResponse<T = any> {
    data: T;
    status: number;
    statusText: string;
    headers: Record<string, any>;
    config: AxiosRequestConfig;
  }
  export interface InternalAxiosRequestConfig extends AxiosRequestConfig {
    headers: Record<string, any>;
  }
  export interface AxiosInstance {
    (config: AxiosRequestConfig): Promise<any>;
    get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>;
    post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>;
    put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>;
    delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>;
    patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>;
    interceptors: {
      request: { use: (...args: any[]) => any };
      response: { use: (...args: any[]) => any };
    };
    defaults: AxiosRequestConfig;
  }
  export interface AxiosStatic extends AxiosInstance {
    create(config?: AxiosRequestConfig): AxiosInstance;
  }
  declare const axios: AxiosStatic;
  export default axios;
}
