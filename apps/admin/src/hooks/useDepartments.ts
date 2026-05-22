/**
 * 科室列表 Hook
 *
 * 封装 departmentApi.getAll() 调用，自动加载科室列表
 * 用于替代各排班页面中重复的 loadDepartments 代码
 *
 * @example
 * ```tsx
 * const { departments, loading, error, refresh } = useDepartments();
 *
 * <Select options={departments.map(d => ({ label: d.name, value: d.id }))} />
 * ```
 */
import { useState, useEffect, useCallback } from 'react';
import { departmentApi } from '@hospital/api';
import type { Department } from '@hospital/shared';

interface UseDepartmentsOptions {
  /** 是否立即加载，默认 true */
  enabled?: boolean;
}

interface UseDepartmentsResult {
  /** 科室列表 */
  departments: Department[];
  /** 是否正在加载 */
  loading: boolean;
  /** 错误信息 */
  error: Error | null;
  /** 重新加载科室列表 */
  refresh: () => Promise<void>;
}

/**
 * 科室列表 Hook
 *
 * 自动加载所有启用的科室，内部缓存避免重复请求。
 * 适用于排班规则、排班详情、甘特图等需要科室列表的场景。
 */
export function useDepartments(
  options: UseDepartmentsOptions = {}
): UseDepartmentsResult {
  const { enabled = true } = options;

  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const loadDepartments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await departmentApi.getAll();
      setDepartments(data ?? []);
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error('加载科室失败', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      loadDepartments();
    }
  }, [enabled, loadDepartments]);

  return {
    departments,
    loading,
    error,
    refresh: loadDepartments,
  };
}
