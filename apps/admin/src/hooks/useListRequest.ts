import { useRequest } from '@umijs/max';
import type { DependencyList } from 'react';

/** useRequest 内部选项类型（自包含，不依赖 ahooks 内部路径） */
interface RequestOptions<TData, TParams extends any[]> {
  manual?: boolean;
  onBefore?: (params: TParams) => void;
  onSuccess?: (data: TData, params: TParams) => void;
  onError?: (e: Error, params: TParams) => void;
  onFinally?: (params: TParams, data?: TData, e?: Error) => void;
  defaultParams?: TParams;
  refreshDeps?: DependencyList;
  loadingDelay?: number;
  pollingInterval?: number;
  pollingWhenHidden?: boolean;
  pollingErrorRetryCount?: number;
  refreshOnWindowFocus?: boolean;
  focusTimespan?: number;
  debounceWait?: number;
  debounceLeading?: boolean;
  debounceTrailing?: boolean;
  debounceMaxWait?: number;
  throttleWait?: number;
  throttleLeading?: boolean;
  throttleTrailing?: boolean;
  cacheKey?: string;
  cacheTime?: number;
  staleTime?: number;
  retryCount?: number;
  retryInterval?: number;
  ready?: boolean;
  [key: string]: any;
}

/** useRequest 返回值类型 */
interface RequestResult<TData, TParams extends any[]> {
  loading: boolean;
  data?: TData;
  error?: Error;
  params: TParams | [];
  cancel: () => void;
  refresh: () => void;
  refreshAsync: () => Promise<TData>;
  run: (...params: TParams) => void;
  runAsync: (...params: TParams) => Promise<TData>;
  mutate: (data?: TData | ((oldData?: TData) => TData | undefined)) => void;
  [key: string]: any;
}

/**
 * 列表请求 Hook 配置选项
 * 基于 @umijs/max 的 useRequest，提供 SWR/缓存/屏幕聚焦刷新等功能
 */
export interface UseListRequestOptions<TData, TParams extends any[]>
  extends Omit<RequestOptions<TData, TParams>, 'cacheKey' | 'staleTime'> {
  /**
   * 缓存 key，设置后启用缓存功能
   * 相同 cacheKey 的请求会共享缓存数据
   */
  cacheKey?: string;

  /**
   * 数据新鲜时间（毫秒），默认 5000（5秒）
   * 在此时间内，相同 cacheKey 的请求会直接返回缓存数据
   * 设置为 -1 表示永不过期
   */
  staleTime?: number;

  /**
   * 窗口聚焦时是否重新请求，默认 false
   * 适用于数据可能在后台发生变化的场景
   */
  refreshOnWindowFocus?: boolean;

  /**
   * 窗口聚焦重新请求的间隔时间（毫秒），默认 5000
   * 防止频繁切换窗口导致的过多请求
   */
  focusTimespan?: number;

  /**
   * 是否手动触发请求，默认 false
   * 设为 true 时需要调用 run/runAsync 手动触发
   */
  manual?: boolean;

  /**
   * 错误重试次数，默认 0
   */
  retryCount?: number;

  /**
   * 错误重试间隔（毫秒），默认 1000
   */
  retryInterval?: number;

  /**
   * Loading 延迟时间（毫秒），默认 0
   * 避免 loading 状态闪烁
   */
  loadingDelay?: number;

  /**
   * 轮询间隔（毫秒），设置后启用轮询
   * 设为 0 或不设置则不轮询
   */
  pollingInterval?: number;

  /**
   * 轮询时是否在页面隐藏时暂停，默认 true
   */
  pollingWhenHidden?: boolean;

  /**
   * 轮询错误重试次数，默认 -1（无限重试）
   */
  pollingErrorRetryCount?: number;

  /**
   * 防抖等待时间（毫秒），设置后启用防抖
   */
  debounceWait?: number;

  /**
   * 节流等待时间（毫秒），设置后启用节流
   */
  throttleWait?: number;

  /**
   * 请求成功回调
   */
  onSuccess?: (data: TData, params: TParams) => void;

  /**
   * 请求失败回调
   */
  onError?: (e: Error, params: TParams) => void;

  /**
   * 请求完成回调（无论成功或失败）
   */
  onFinally?: (params: TParams, data?: TData, e?: Error) => void;
}

/**
 * 列表请求 Hook 返回值
 */
export interface UseListRequestResult<TData, TParams extends any[]>
  extends Omit<RequestResult<TData, TParams>, 'run' | 'runAsync'> {
  /** 当前数据 */
  data: TData | undefined;
  /** 是否正在加载 */
  loading: boolean;
  /** 错误信息 */
  error: Error | undefined;
  /** 手动触发请求 */
  run: (...params: TParams) => void;
  /** 手动触发请求（返回 Promise） */
  runAsync: (...params: TParams) => Promise<TData>;
  /** 刷新请求（使用上一次的参数） */
  refresh: () => void;
  /** 刷新请求（返回 Promise） */
  refreshAsync: () => Promise<TData>;
  /** 取消请求 */
  cancel: () => void;
  /** 修改数据 */
  mutate: (data?: TData | ((oldData?: TData) => TData | undefined)) => void;
}

/**
 * 列表数据请求 Hook
 * 基于 @umijs/max 的 useRequest，专门用于列表数据请求场景
 * 提供 SWR 缓存、屏幕聚焦刷新、轮询、防抖节流等功能
 *
 * @param service 请求函数
 * @param options 配置选项
 * @returns 请求状态和方法
 *
 * @example
 * // 基础用法
 * const { data, loading, refresh } = useListRequest(
 *   () => api.getDepartments()
 * );
 *
 * @example
 * // 带缓存和窗口聚焦刷新
 * const { data, loading } = useListRequest(
 *   () => api.getDepartments(),
 *   {
 *     cacheKey: 'department-list',
 *     staleTime: 60000,  // 1分钟
 *     refreshOnWindowFocus: true,
 *   }
 * );
 *
 * @example
 * // 带轮询（实时数据）
 * const { data, loading } = useListRequest(
 *   () => api.getQueue(),
 *   {
 *     pollingInterval: 5000,  // 5秒轮询
 *     pollingWhenHidden: false,  // 页面隐藏时暂停
 *   }
 * );
 *
 * @example
 * // 手动触发请求
 * const { data, loading, run } = useListRequest(
 *   (params) => api.search(params),
 *   { manual: true }
 * );
 * // 调用 run({ keyword: 'test' }) 触发请求
 *
 * @example
 * // 带防抖的搜索
 * const { data, loading, run } = useListRequest(
 *   (keyword) => api.search({ keyword }),
 *   {
 *     manual: true,
 *     debounceWait: 300,
 *   }
 * );
 *
 * @example
 * // 与 ProTable 配合使用（dataSource 模式）
 * const { data, loading, refresh } = useListRequest(
 *   () => api.getList(),
 *   { cacheKey: 'my-list' }
 * );
 *
 * <ProTable
 *   dataSource={data?.items || data}
 *   loading={loading}
 *   search={false}  // dataSource 模式下需要禁用搜索或手动处理
 *   toolBarRender={() => [
 *     <Button onClick={refresh}>刷新</Button>
 *   ]}
 * />
 */
export function useListRequest<TData = any, TParams extends any[] = any[]>(
  service: (...args: TParams) => Promise<TData>,
  options?: UseListRequestOptions<TData, TParams>
): UseListRequestResult<TData, TParams> {
  const {
    cacheKey,
    staleTime = 5000,
    refreshOnWindowFocus = false,
    focusTimespan = 5000,
    manual = false,
    retryCount = 0,
    retryInterval = 1000,
    loadingDelay = 0,
    pollingInterval,
    pollingWhenHidden = true,
    pollingErrorRetryCount = -1,
    debounceWait,
    throttleWait,
    onSuccess,
    onError,
    onFinally,
    ...restOptions
  } = options ?? {};

  const result = useRequest(service, {
    // 缓存配置
    cacheKey,
    staleTime,
    // 窗口聚焦刷新
    refreshOnWindowFocus,
    focusTimespan,
    // 手动触发
    manual,
    // 重试配置
    retryCount,
    retryInterval,
    // Loading 延迟
    loadingDelay,
    // 轮询配置
    pollingInterval,
    pollingWhenHidden,
    pollingErrorRetryCount,
    // 防抖节流
    debounceWait,
    throttleWait,
    // 回调
    onSuccess,
    onError,
    onFinally,
    // 其他选项
    ...restOptions,
  } as RequestOptions<TData, TParams>);

  return result as UseListRequestResult<TData, TParams>;
}

/**
 * 分页列表请求 Hook
 * 专门用于分页列表场景，自动处理分页参数
 *
 * @param service 请求函数，接收分页参数
 * @param options 配置选项
 * @returns 请求状态、方法和分页信息
 *
 * @example
 * const { data, loading, pagination, run } = usePaginatedRequest(
 *   ({ page, pageSize }) => api.getList({ page, pageSize }),
 *   { defaultPageSize: 10 }
 * );
 *
 * <ProTable
 *   dataSource={data?.items}
 *   loading={loading}
 *   pagination={{
 *     current: pagination.current,
 *     pageSize: pagination.pageSize,
 *     total: pagination.total,
 *     onChange: pagination.onChange,
 *   }}
 * />
 */
export interface PaginatedRequestOptions<TData, TParams extends any[]>
  extends UseListRequestOptions<TData, TParams> {
  /** 默认当前页，默认 1 */
  defaultCurrent?: number;
  /** 默认每页条数，默认 10 */
  defaultPageSize?: number;
}

export interface PaginatedResult<TData, TParams extends any[]>
  extends UseListRequestResult<TData, TParams> {
  pagination: {
    current: number;
    pageSize: number;
    total: number;
    totalPage: number;
    onChange: (current: number, pageSize: number) => void;
    changeCurrent: (current: number) => void;
    changePageSize: (pageSize: number) => void;
  };
}

export function usePaginatedRequest<
  TData extends { total?: number; items?: any[]; data?: any[] } = any,
  TParams extends [{ page: number; pageSize: number; [key: string]: any }] = [
    { page: number; pageSize: number }
  ]
>(
  service: (...args: TParams) => Promise<TData>,
  options?: PaginatedRequestOptions<TData, TParams>
): PaginatedResult<TData, TParams> {
  const { defaultCurrent = 1, defaultPageSize = 10, ...restOptions } = options ?? {};

  const result = useRequest(service, {
    ...restOptions,
    defaultParams: [{ page: defaultCurrent, pageSize: defaultPageSize }] as TParams,
  } as RequestOptions<TData, TParams>);

  const { data, run } = result;

  // 计算分页信息
  const total = data?.total ?? 0;
  const params = (result as any).params?.[0] ?? { page: defaultCurrent, pageSize: defaultPageSize };
  const current = params.page ?? defaultCurrent;
  const pageSize = params.pageSize ?? defaultPageSize;
  const totalPage = Math.ceil(total / pageSize);

  const pagination = {
    current,
    pageSize,
    total,
    totalPage,
    onChange: (newCurrent: number, newPageSize: number) => {
      run({ ...params, page: newCurrent, pageSize: newPageSize } as TParams[0]);
    },
    changeCurrent: (newCurrent: number) => {
      run({ ...params, page: newCurrent } as TParams[0]);
    },
    changePageSize: (newPageSize: number) => {
      run({ ...params, page: 1, pageSize: newPageSize } as TParams[0]);
    },
  };

  return {
    ...result,
    pagination,
  } as PaginatedResult<TData, TParams>;
}

export default useListRequest;
