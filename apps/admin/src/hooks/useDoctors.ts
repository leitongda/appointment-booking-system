/**
 * 医生列表 Hook
 *
 * 封装 doctorApi.getByDepartment / doctorApi.getList 调用
 * 根据筛选条件（科室/门店）自动加载医生列表
 * 用于替代各排班页面中重复的 loadDoctors / loadDoctorsByDept / loadDoctorsByStore 代码
 *
 * @example
 * ```tsx
 * // 按科室加载
 * const { doctors } = useDoctors({ departmentId: selectedDept });
 *
 * // 按门店加载
 * const { doctors } = useDoctors({ storeId: selectedStore });
 *
 * // 加载全部医生
 * const { doctors } = useDoctors();
 * ```
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { doctorApi } from '@hospital/api';
import { fetchAllData } from '@/utils/fetchAllData';
import type { Doctor } from '@hospital/shared';

interface UseDoctorsOptions {
  /** 科室ID，设置后按科室加载医生 */
  departmentId?: string;
  /** 门店ID，设置后按门店加载医生（departmentId 优先） */
  storeId?: string;
  /** 是否立即加载，默认 true */
  enabled?: boolean;
}

interface UseDoctorsResult {
  /** 医生列表 */
  doctors: Doctor[];
  /** 是否正在加载 */
  loading: boolean;
  /** 错误信息 */
  error: Error | null;
  /** 重新加载医生列表 */
  refresh: () => Promise<void>;
}

/**
 * 医生列表 Hook
 *
 * 根据筛选条件自动加载医生列表：
 * - 有 departmentId 时，调用 doctorApi.getByDepartment(deptId)
 * - 有 storeId 时（无 departmentId），调用 doctorApi.getList({storeId}) 分页加载全部
 * - 都没有时，调用 doctorApi.getList() 分页加载全部
 *
 * 筛选条件变化时自动重新加载。
 */
export function useDoctors(
  options: UseDoctorsOptions = {}
): UseDoctorsResult {
  const { departmentId, storeId, enabled = true } = options;

  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // 使用 ref 追踪最新的筛选条件，避免闭包过期
  const filtersRef = useRef({ departmentId, storeId });
  filtersRef.current = { departmentId, storeId };

  const loadDoctors = useCallback(async () => {
    const { departmentId: deptId, storeId: sId } = filtersRef.current;

    setLoading(true);
    setError(null);
    try {
      let data: Doctor[] = [];

      if (deptId) {
        // 按科室加载
        data = await doctorApi.getByDepartment(deptId);
        data = data ?? [];
      } else if (sId) {
        // 按门店加载（分页获取全部）
        data = await fetchAllData((page, pageSize) =>
          doctorApi.getList({ storeId: sId, page, pageSize, status: 1 })
        );
      } else {
        // 加载全部医生（分页获取）
        data = await fetchAllData((page, pageSize) =>
          doctorApi.getList({ page, pageSize })
        );
      }

      setDoctors(data);
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error('加载医生失败', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      loadDoctors();
    } else {
      // 当 enabled 变为 false 时清空数据
      setDoctors([]);
      setError(null);
    }
  }, [enabled, departmentId, storeId, loadDoctors]);

  return {
    doctors,
    loading,
    error,
    refresh: loadDoctors,
  };
}
