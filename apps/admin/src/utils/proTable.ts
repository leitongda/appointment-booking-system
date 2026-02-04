import { debounce } from 'lodash-es';

/**
 * 将 API 响应转换为 ProTable 需要的格式
 * @param res API 返回的数据（数组或分页对象）
 * @returns { data, success, total }
 */
export function toProTableResult<T>(
  res: T[] | { items?: T[]; data?: T[]; total?: number }
) {
  if (Array.isArray(res)) {
    return { data: res, success: true, total: res.length };
  }
  const items = res.items || res.data || [];
  const total = res.total ?? items.length;
  return { data: items, success: true, total };
}

/**
 * ProTable 分页请求参数
 */
export interface ProTableParams {
  current?: number;
  pageSize?: number;
  [key: string]: any;
}

/**
 * API 分页请求参数
 */
export interface ApiPaginationParams {
  page?: number;
  pageSize?: number;
  [key: string]: any;
}

/**
 * 列表请求函数类型
 */
type ListFetcher<P, R> = (params: P) => Promise<R>;

/**
 * ProTable 请求结果类型
 */
export interface ProTableRequestResult<T> {
  data: T[];
  success: boolean;
  total: number;
}

/**
 * 列表请求配置选项
 */
export interface ListRequestOptions<P = ApiPaginationParams> {
  /** 参数转换函数，用于自定义参数处理 */
  paramTransform?: (params: ApiPaginationParams) => P;
  /** 错误重试次数，默认 0（不重试） */
  retryCount?: number;
  /** 重试间隔（毫秒），默认 1000 */
  retryDelay?: number;
  /** 防抖等待时间（毫秒），设置后启用防抖 */
  debounceWait?: number;
  /** loading 延迟显示时间（毫秒），避免闪烁，默认 0 */
  loadingDelay?: number;
  /** 错误回调函数 */
  onError?: (error: Error) => void;
  /** 是否在网络错误时才重试（业务错误如 400/403 不重试），默认 true */
  retryOnNetworkErrorOnly?: boolean;
}

/**
 * 延迟函数
 */
const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

/**
 * 判断是否为网络错误（可重试的错误）
 */
const isNetworkError = (error: any): boolean => {
  // 网络错误
  if (error?.message === 'Network Error') return true;
  // 超时错误
  if (error?.message?.includes('timeout')) return true;
  // 服务器错误 (5xx)
  if (error?.code >= 500 && error?.code < 600) return true;
  // 网关错误
  if ([502, 503, 504].includes(error?.code)) return true;
  return false;
};

/**
 * 带重试的请求包装器
 */
async function fetchWithRetry<P, R>(
  fetchFn: ListFetcher<P, R>,
  params: P,
  options: {
    retryCount: number;
    retryDelay: number;
    retryOnNetworkErrorOnly: boolean;
    onError?: (error: Error) => void;
  }
): Promise<R> {
  const { retryCount, retryDelay, retryOnNetworkErrorOnly, onError } = options;
  let lastError: any;

  for (let attempt = 0; attempt <= retryCount; attempt++) {
    try {
      return await fetchFn(params);
    } catch (error: any) {
      lastError = error;

      // 判断是否应该重试
      const shouldRetry =
        attempt < retryCount &&
        (!retryOnNetworkErrorOnly || isNetworkError(error));

      if (shouldRetry) {
        console.warn(
          `[createListRequest] 请求失败，${retryDelay}ms 后重试 (${attempt + 1}/${retryCount})`,
          error?.message
        );
        await sleep(retryDelay);
      } else {
        // 不重试，调用错误回调
        onError?.(error);
        throw error;
      }
    }
  }

  // 所有重试都失败
  onError?.(lastError);
  throw lastError;
}

/**
 * 创建 ProTable 的 request 函数
 * 自动处理 current -> page 的转换以及 toProTableResult 的包装
 * 支持错误重试、防抖、loading 延迟等高级功能
 *
 * @param fetchFn API 请求函数
 * @param optionsOrTransform 配置选项对象，或参数转换函数（向后兼容）
 * @returns ProTable request 函数
 *
 * @example
 * // 基础用法
 * <ProTable request={createListRequest(patientApi.getList)} />
 *
 * @example
 * // 自定义参数转换（向后兼容写法）
 * <ProTable request={createListRequest(
 *   patientApi.getList,
 *   (params) => ({ ...params, keyword: params.name || params.phone })
 * )} />
 *
 * @example
 * // 带重试和防抖
 * <ProTable request={createListRequest(api.getList, {
 *   retryCount: 2,
 *   retryDelay: 1000,
 *   debounceWait: 300,
 *   loadingDelay: 200,
 *   onError: (err) => console.error('请求失败:', err),
 * })} />
 *
 * @example
 * // 带参数转换和高级配置
 * <ProTable request={createListRequest(api.getList, {
 *   paramTransform: (params) => ({ ...params, keyword: params.name }),
 *   retryCount: 3,
 * })} />
 */
export function createListRequest<T, P = ApiPaginationParams>(
  fetchFn: ListFetcher<P, any>,
  optionsOrTransform?: ListRequestOptions<P> | ((params: ApiPaginationParams) => P)
): (params: ProTableParams) => Promise<ProTableRequestResult<T>> {
  // 向后兼容：第二个参数可以是函数或配置对象
  const options: ListRequestOptions<P> =
    typeof optionsOrTransform === 'function'
      ? { paramTransform: optionsOrTransform }
      : optionsOrTransform ?? {};

  const {
    paramTransform,
    retryCount = 0,
    retryDelay = 1000,
    debounceWait,
    loadingDelay = 0,
    onError,
    retryOnNetworkErrorOnly = true,
  } = options;

  // 核心请求逻辑
  const coreFetch = async (params: ProTableParams): Promise<ProTableRequestResult<T>> => {
    const startTime = Date.now();
    const { current, pageSize, ...rest } = params;
    const baseParams: ApiPaginationParams = { ...rest, page: current, pageSize };
    const queryParams = paramTransform ? paramTransform(baseParams) : (baseParams as P);

    try {
      const result = await fetchWithRetry(fetchFn, queryParams, {
        retryCount,
        retryDelay,
        retryOnNetworkErrorOnly,
        onError,
      });

      // Loading delay：确保 loading 至少显示一段时间，避免闪烁
      if (loadingDelay > 0) {
        const elapsed = Date.now() - startTime;
        if (elapsed < loadingDelay) {
          await sleep(loadingDelay - elapsed);
        }
      }

      return toProTableResult<T>(result);
    } catch (error: any) {
      // 请求失败时返回空数据，错误已在 fetchWithRetry 中处理
      return { data: [], success: false, total: 0 };
    }
  };

  // 如果设置了防抖，返回防抖包装的函数
  if (debounceWait && debounceWait > 0) {
    // 使用 Promise 包装 debounce，确保返回 Promise
    let pendingResolve: ((value: ProTableRequestResult<T>) => void) | null = null;
    let pendingReject: ((reason?: any) => void) | null = null;

    const debouncedFetch = debounce(async (params: ProTableParams) => {
      try {
        const result = await coreFetch(params);
        pendingResolve?.(result);
      } catch (error) {
        pendingReject?.(error);
      }
    }, debounceWait);

    return (params: ProTableParams): Promise<ProTableRequestResult<T>> => {
      return new Promise((resolve, reject) => {
        pendingResolve = resolve;
        pendingReject = reject;
        debouncedFetch(params);
      });
    };
  }

  return coreFetch;
}
