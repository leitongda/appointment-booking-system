/**
 * Axios 空模块 - 用于在小程序环境中替代 axios
 *
 * 小程序环境不支持 axios 的 xhr/http/fetch 适配器，
 * 需要使用 Taro.request 代替。
 * @hospital/api 包中的 request.ts 会通过 setHttpClient 使用 Taro 适配器，
 * 但 axios 的顶层代码仍会在模块导入时执行，可能导致错误。
 * 我们用这个空模块替代 axios，避免其在小程序环境中执行。
 */

// 模拟 AxiosInstance 接口
const createMockInstance = () => {
  const mockRequest = () => {
    console.warn('[小程序] 不应直接使用 axios，请确保 setHttpClient 已设置 Taro 适配器');
    return Promise.reject(new Error('axios 在小程序环境中不可用，请使用 Taro 适配器'));
  };

  return {
    defaults: {
      baseURL: '',
      headers: {
        common: {},
      },
    },
    interceptors: {
      request: {
        use: () => 0,
        eject: () => {},
        clear: () => {},
      },
      response: {
        use: () => 0,
        eject: () => {},
        clear: () => {},
      },
    },
    get: mockRequest,
    post: mockRequest,
    put: mockRequest,
    delete: mockRequest,
    patch: mockRequest,
    head: mockRequest,
    options: mockRequest,
    request: mockRequest,
  };
};

// 模拟 axios.create
const create = () => createMockInstance();

// 模拟默认导出
const axios = {
  ...createMockInstance(),
  create,
  isAxiosError: () => false,
  isCancel: () => false,
  CancelToken: {
    source: () => ({
      token: {},
      cancel: () => {},
    }),
  },
  Cancel: class Cancel {},
  Axios: class Axios {},
};

export default axios;
export { axios, create };

// 导出类型占位符（用于 TypeScript 类型检查）
export type AxiosInstance = ReturnType<typeof createMockInstance>;
export type AxiosRequestConfig = Record<string, any>;
export type AxiosResponse<T = any> = { data: T; status: number; statusText: string };
export type InternalAxiosRequestConfig = AxiosRequestConfig;
