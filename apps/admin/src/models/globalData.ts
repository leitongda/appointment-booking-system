/**
 * 全局数据 Model
 *
 * 统一管理全局共享数据，如科室列表、门店列表等
 * 避免在各个组件中重复请求和管理相同的数据
 */
import { useState, useCallback } from 'react';
import { departmentApi, storeApi } from '@hospital/api';
import { PAGINATION_CONFIG } from '@/constants/pagination';
import type { Department, Store } from '@hospital/shared';

/**
 * 全局数据状态接口
 */
interface GlobalDataState {
  /** 科室列表 */
  departments: Department[];
  /** 门店列表 */
  stores: Store[];
  /** 加载状态 */
  loading: boolean;
  /** 错误信息 */
  error: Error | null;
}

/**
 * 全局数据 Model
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { departments, loadDepartments } = useModel('globalData');
 *
 *   useEffect(() => {
 *     loadDepartments();
 *   }, []);
 *
 *   return <div>{departments.length} 个科室</div>;
 * }
 * ```
 */
export default function useGlobalData() {
  const [state, setState] = useState<GlobalDataState>({
    departments: [],
    stores: [],
    loading: false,
    error: null,
  });

  /**
   * 加载科室列表
   *
   * @param options 加载选项
   * @returns 科室列表
   */
  const loadDepartments = useCallback(async (options?: {
    status?: number;
    forceReload?: boolean;
  }) => {
    const { status = 1, forceReload = false } = options || {};

    // 如果已有数据且不强制重新加载，直接返回
    if (!forceReload && state.departments.length > 0) {
      return state.departments;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const result = await departmentApi.getList({
        pageSize: PAGINATION_CONFIG.SELECT_MAX_SIZE,
        status,
      });

      const departments = result.data ?? [];

      setState((prev) => ({
        ...prev,
        departments,
        loading: false,
      }));

      return departments;
    } catch (error) {
      const err = error as Error;
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err,
      }));
      throw err;
    }
  }, [state.departments.length]);

  /**
   * 加载门店列表
   *
   * @param options 加载选项
   * @returns 门店列表
   */
  const loadStores = useCallback(async (options?: {
    status?: number;
    forceReload?: boolean;
  }) => {
    const { status = 1, forceReload = false } = options || {};

    // 如果已有数据且不强制重新加载，直接返回
    if (!forceReload && state.stores.length > 0) {
      return state.stores;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const result = await storeApi.getList({
        pageSize: PAGINATION_CONFIG.SELECT_MAX_SIZE,
        status,
      });

      const stores = result.data ?? [];

      setState((prev) => ({
        ...prev,
        stores,
        loading: false,
      }));

      return stores;
    } catch (error) {
      const err = error as Error;
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err,
      }));
      throw err;
    }
  }, [state.stores.length]);

  /**
   * 刷新所有数据
   */
  const refreshAll = useCallback(async () => {
    await Promise.all([
      loadDepartments({ forceReload: true }),
      loadStores({ forceReload: true }),
    ]);
  }, [loadDepartments, loadStores]);

  /**
   * 清空所有数据
   */
  const clearAll = useCallback(() => {
    setState({
      departments: [],
      stores: [],
      loading: false,
      error: null,
    });
  }, []);

  /**
   * 更新科室列表（用于增删改后更新缓存）
   */
  const updateDepartments = useCallback((departments: Department[]) => {
    setState((prev) => ({
      ...prev,
      departments,
    }));
  }, []);

  /**
   * 更新门店列表（用于增删改后更新缓存）
   */
  const updateStores = useCallback((stores: Store[]) => {
    setState((prev) => ({
      ...prev,
      stores,
    }));
  }, []);

  /**
   * 添加科室到列表
   */
  const addDepartment = useCallback((department: Department) => {
    setState((prev) => ({
      ...prev,
      departments: [...prev.departments, department],
    }));
  }, []);

  /**
   * 更新单个科室
   */
  const updateDepartment = useCallback((id: string, updates: Partial<Department>) => {
    setState((prev) => ({
      ...prev,
      departments: prev.departments.map((item) =>
        item.id === id ? { ...item, ...updates } : item
      ),
    }));
  }, []);

  /**
   * 删除科室
   */
  const removeDepartment = useCallback((id: string) => {
    setState((prev) => ({
      ...prev,
      departments: prev.departments.filter((item) => item.id !== id),
    }));
  }, []);

  /**
   * 添加门店到列表
   */
  const addStore = useCallback((store: Store) => {
    setState((prev) => ({
      ...prev,
      stores: [...prev.stores, store],
    }));
  }, []);

  /**
   * 更新单个门店
   */
  const updateStore = useCallback((id: string, updates: Partial<Store>) => {
    setState((prev) => ({
      ...prev,
      stores: prev.stores.map((item) =>
        item.id === id ? { ...item, ...updates } : item
      ),
    }));
  }, []);

  /**
   * 删除门店
   */
  const removeStore = useCallback((id: string) => {
    setState((prev) => ({
      ...prev,
      stores: prev.stores.filter((item) => item.id !== id),
    }));
  }, []);

  return {
    // 状态
    departments: state.departments,
    stores: state.stores,
    loading: state.loading,
    error: state.error,

    // 数据加载
    loadDepartments,
    loadStores,
    refreshAll,
    clearAll,

    // 数据更新
    updateDepartments,
    updateStores,
    addDepartment,
    updateDepartment,
    removeDepartment,
    addStore,
    updateStore,
    removeStore,
  };
}
