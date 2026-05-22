import { useState, useEffect, useCallback, useRef } from 'react';
import { dictApi } from '@hospital/api';
import type { DictOptionItem } from '@hospital/api';

// localStorage 缓存 TTL（30 分钟）
const CACHE_TTL = 30 * 60 * 1000;
const CACHE_PREFIX = 'dict_cache_';

interface CacheEntry {
  items: DictOptionItem[];
  timestamp: number;
}

function getCacheKey(code: string): string {
  return `${CACHE_PREFIX}${code}`;
}

function readCache(code: string): DictOptionItem[] | null {
  try {
    const raw = localStorage.getItem(getCacheKey(code));
    if (!raw) return null;
    const entry: CacheEntry = JSON.parse(raw);
    if (Date.now() - entry.timestamp > CACHE_TTL) {
      localStorage.removeItem(getCacheKey(code));
      return null;
    }
    return entry.items;
  } catch {
    return null;
  }
}

function writeCache(code: string, items: DictOptionItem[]): void {
  try {
    const entry: CacheEntry = { items, timestamp: Date.now() };
    localStorage.setItem(getCacheKey(code), JSON.stringify(entry));
  } catch {
    // localStorage 满或不可用，静默忽略
  }
}

/**
 * 清除指定字典类型的缓存
 */
export function clearDictCache(code: string): void {
  try {
    localStorage.removeItem(getCacheKey(code));
  } catch {
    // ignore
  }
}

/**
 * 清除所有字典缓存
 */
export function clearAllDictCache(): void {
  try {
    const keys = Object.keys(localStorage);
    keys.forEach((key) => {
      if (key.startsWith(CACHE_PREFIX)) {
        localStorage.removeItem(key);
      }
    });
  } catch {
    // ignore
  }
}

/**
 * 字典数据 Hook
 *
 * 使用方式：
 * ```tsx
 * const { options, loading, refresh } = useDict('doctor_title');
 * ```
 *
 * 返回的 options 格式：`{ label, value, extra? }[]`
 * 适合直接作为 Select/Checkbox.Group 等组件的 options 数据源
 */
export function useDict(typeCode: string) {
  const [options, setOptions] = useState<DictOptionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const mountedRef = useRef(true);

  const fetchOptions = useCallback(
    async (forceRefresh = false) => {
      if (!typeCode) return;

      // 先尝试读缓存
      if (!forceRefresh) {
        const cached = readCache(typeCode);
        if (cached) {
          setOptions(cached);
          // 后台静默刷新
          dictApi.getOptions(typeCode).then((res) => {
            if (mountedRef.current) {
              setOptions(res.items);
              writeCache(typeCode, res.items);
            }
          }).catch(() => {/* 静默失败 */});
          return;
        }
      }

      setLoading(true);
      try {
        const res = await dictApi.getOptions(typeCode);
        if (mountedRef.current) {
          setOptions(res.items);
          writeCache(typeCode, res.items);
        }
      } catch {
        // 失败时保持空数组
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    },
    [typeCode]
  );

  useEffect(() => {
    mountedRef.current = true;
    fetchOptions();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchOptions]);

  const refresh = useCallback(() => {
    clearDictCache(typeCode);
    fetchOptions(true);
  }, [typeCode, fetchOptions]);

  return { options, dictItems: options, loading, refresh };
}

/**
 * 批量获取多个字典类型
 *
 * 使用方式：
 * ```tsx
 * const { dicts, loading } = useDictBatch(['doctor_title', 'education']);
 * // dicts.doctor_title -> DictOptionItem[]
 * // dicts.education -> DictOptionItem[]
 * ```
 */
export function useDictBatch(typeCodes: string[]) {
  const [dicts, setDicts] = useState<Record<string, DictOptionItem[]>>({});
  const [loading, setLoading] = useState(false);
  const mountedRef = useRef(true);
  const codesKey = typeCodes.join(',');

  const fetchBatch = useCallback(async () => {
    if (typeCodes.length === 0) return;

    // 检查是否所有都有缓存
    const result: Record<string, DictOptionItem[]> = {};
    const uncachedCodes: string[] = [];

    for (const code of typeCodes) {
      const cached = readCache(code);
      if (cached) {
        result[code] = cached;
      } else {
        uncachedCodes.push(code);
      }
    }

    if (uncachedCodes.length === 0) {
      setDicts(result);
      return;
    }

    setLoading(true);
    try {
      const res = await dictApi.batchGetOptions(uncachedCodes);
      for (const dict of res.dicts) {
        result[dict.code] = dict.items;
        writeCache(dict.code, dict.items);
      }
      if (mountedRef.current) {
        setDicts(result);
      }
    } catch {
      // 失败时返回已有缓存
      if (mountedRef.current) {
        setDicts(result);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [codesKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    mountedRef.current = true;
    fetchBatch();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchBatch]);

  return { dicts, loading };
}
