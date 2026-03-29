/**
 * 门店权限过滤 Hook
 *
 * 封装门店列表加载和基于用户权限的过滤逻辑
 * 用于替代各组件中重复的门店加载代码
 */
import { useState, useEffect, useCallback } from 'react';
import { useModel } from '@umijs/max';
import { storeApi } from '@hospital/api';
import type { Store } from '@hospital/shared';

interface UseStoreWithPermissionOptions {
  /** 是否只返回启用的门店，默认 true */
  enabledOnly?: boolean;
  /** 是否立即加载，默认 true */
  immediate?: boolean;
}

interface UseStoreWithPermissionResult {
  /** 门店列表 */
  stores: Store[];
  /** 是否正在加载 */
  loading: boolean;
  /** 错误信息 */
  error: Error | null;
  /** 重新加载门店列表 */
  reload: () => Promise<void>;
}

/**
 * 门店权限过滤 Hook
 *
 * 根据用户权限自动过滤门店列表：
 * - 超级管理员：显示所有门店
 * - 普通管理员：只显示其关联的门店（currentUser.storeIds）
 *
 * @example
 * ```tsx
 * const { stores, loading } = useStoreWithPermission();
 *
 * <Select options={stores.map(s => ({ label: s.name, value: s.id }))} />
 * ```
 */
export function useStoreWithPermission(
  options: UseStoreWithPermissionOptions = {}
): UseStoreWithPermissionResult {
  const { enabledOnly = true, immediate = true } = options;

  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = currentUser?.isSuperAdmin ?? false;

  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadStores = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await storeApi.getAll();
      let storeList = data ?? [];

      // 根据状态过滤
      if (enabledOnly) {
        storeList = storeList.filter((s) => s.status === 1);
      }

      // 非超管只显示其关联的门店
      if (!isSuperAdmin && currentUser?.storeIds?.length) {
        storeList = storeList.filter((s) => currentUser.storeIds?.includes(s.id));
      }

      setStores(storeList);
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error('加载门店失败', error);
    } finally {
      setLoading(false);
    }
  }, [enabledOnly, isSuperAdmin, currentUser?.storeIds]);

  useEffect(() => {
    if (immediate) {
      loadStores();
    }
  }, [loadStores, immediate]);

  return {
    stores,
    loading,
    error,
    reload: loadStores,
  };
}
