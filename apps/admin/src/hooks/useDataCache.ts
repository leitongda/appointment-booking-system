/**
 * 数据缓存 Hook
 *
 * 用于缓存API请求数据，减少重复请求，提升性能
 */
import { useState, useEffect, useCallback, useRef } from 'react';

interface UseDataCacheOptions<T> {
  /** 缓存键，用于标识不同的数据 */
  key: string;
  /** 数据获取函数 */
  fetcher: () => Promise<T>;
  /** 缓存有效时间（毫秒），默认5分钟 */
  staleTime?: number;
  /** 是否启用缓存，默认true */
  enabled?: boolean;
  /** 初始数据 */
  initialData?: T;
}

interface UseDataCacheResult<T> {
  /** 缓存的数据 */
  data: T | null;
  /** 是否正在加载 */
  loading: boolean;
  /** 错误信息 */
  error: Error | null;
  /** 重新获取数据（忽略缓存） */
  refetch: () => Promise<T | null>;
  /** 使缓存失效，下次访问时会重新获取 */
  invalidate: () => void;
}

/**
 * 全局缓存存储
 */
const globalCache = new Map<string, { data: any; timestamp: number }>();

/**
 * 数据缓存 Hook
 *
 * @example
 * ```tsx
 * const { data, loading, refetch } = useDataCache({
 *   key: 'departments',
 *   fetcher: () => departmentApi.getList({ pageSize: 200 }),
 *   staleTime: 5 * 60 * 1000, // 5分钟
 * });
 * ```
 */
export function useDataCache<T>({
  key,
  fetcher,
  staleTime = 5 * 60 * 1000,
  enabled = true,
  initialData,
}: UseDataCacheOptions<T>): UseDataCacheResult<T> {
  const [data, setData] = useState<T | null>(initialData ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const lastFetchRef = useRef<number>(0);

  /**
   * 检查缓存是否有效
   */
  const isCacheValid = useCallback((): boolean => {
    const cached = globalCache.get(key);
    if (!cached) return false;

    const now = Date.now();
    return (now - cached.timestamp) < staleTime;
  }, [key, staleTime]);

  /**
   * 从缓存获取数据
   */
  const getFromCache = useCallback((): T | null => {
    const cached = globalCache.get(key);
    return cached?.data ?? null;
  }, [key]);

  /**
   * 写入缓存
   */
  const writeToCache = useCallback((value: T) => {
    globalCache.set(key, {
      data: value,
      timestamp: Date.now(),
    });
  }, [key]);

  /**
   * 获取数据
   */
  const fetchData = useCallback(async (options?: { ignoreCache?: boolean }): Promise<T | null> => {
    if (!enabled) {
      return null;
    }

    // 检查缓存
    if (!options?.ignoreCache && isCacheValid()) {
      const cached = getFromCache();
      if (cached) {
        setData(cached);
        lastFetchRef.current = Date.now();
        return cached;
      }
    }

    setLoading(true);
    setError(null);

    try {
      const result = await fetcher();
      setData(result);
      writeToCache(result);
      lastFetchRef.current = Date.now();
      return result;
    } catch (err) {
      const error = err as Error;
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [enabled, fetcher, isCacheValid, getFromCache, writeToCache]);

  /**
   * 重新获取数据（忽略缓存）
   */
  const refetch = useCallback(() => {
    return fetchData({ ignoreCache: true });
  }, [fetchData]);

  /**
   * 使缓存失效
   */
  const invalidate = useCallback(() => {
    globalCache.delete(key);
  }, [key]);

  /**
   * 初始化加载数据
   */
  useEffect(() => {
    fetchData();
  }, [key]);

  return {
    data,
    loading,
    error,
    refetch,
    invalidate,
  };
}

/**
 * 清除所有缓存
 */
export function clearAllCache() {
  globalCache.clear();
}

/**
 * 清除指定键的缓存
 */
export function clearCacheByKey(key: string) {
  globalCache.delete(key);
}

/**
 * 清除匹配模式的缓存
 */
export function clearCacheByPattern(pattern: RegExp) {
  const keys = Array.from(globalCache.keys());
  keys.forEach(key => {
    if (pattern.test(key)) {
      globalCache.delete(key);
    }
  });
}
