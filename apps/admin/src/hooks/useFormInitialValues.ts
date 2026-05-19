import { useState, useEffect, useMemo, useRef } from 'react';

/**
 * 表单初始值 Hook 配置选项
 */
export interface UseFormInitialValuesOptions<T> {
  /**
   * 需要转换的开关字段（0/1 ↔ true/false）
   */
  switchFields?: (keyof T)[];

  /**
   * 自定义默认值（新增模式使用）
   */
  defaults?: Partial<T>;

  /**
   * 自定义数据转换函数
   * 可以对原始数据进行任意转换后再作为初始值
   */
  transform?: (data: T) => Partial<T>;
}

/**
 * 表单初始值 Hook 返回值
 */
export interface UseFormInitialValuesReturn<T> {
  /**
   * 表单初始值
   */
  initialValues: Partial<T>;

  /**
   * 是否正在加载数据
   */
  loading: boolean;
}

/**
 * 将数字开关值（0/1）转换为布尔值（true/false）
 */
function transformSwitchValues<T>(data: any, switchFields?: (keyof T)[]): any {
  if (!switchFields || switchFields.length === 0) {
    return data;
  }

  const result = { ...data };
  switchFields.forEach((field) => {
    if (result[field] !== undefined) {
      result[field] = result[field] === 1;
    }
  });
  return result;
}

/**
 * 表单初始值 Hook
 * 用于处理编辑模式的数据加载，支持开关字段转换和自定义数据转换
 *
 * @param data 原始数据（编辑模式下传入，新增模式传 null）
 * @param options 配置选项
 * @returns 初始值和加载状态
 *
 * @example
 * // 基础用法 - 新增模式
 * const { initialValues, loading } = useFormInitialValues(null, {
 *   defaults: { status: true, sort: 0 },
 * });
 *
 * @example
 * // 基础用法 - 编辑模式
 * const { initialValues, loading } = useFormInitialValues(data, {
 *   switchFields: ['status', 'isDefault'],
 * });
 *
 * @example
 * // 使用自定义转换
 * const { initialValues, loading } = useFormInitialValues(data, {
 *   switchFields: ['status'],
 *   transform: (data) => ({
 *     ...data,
 *     customField: data.field1 + '-' + data.field2,
 *   }),
 * });
 *
 * @example
 * // 完整示例
 * const { initialValues, loading } = useFormInitialValues<Role | null>(
 *   role,
 *   {
 *     switchFields: ['status'],
 *     defaults: { status: true },
 *     transform: (data) => ({
 *       ...data,
 *       displayName: `${data.name} (${data.code})`,
 *     }),
 *   }
 * );
 */
export function useFormInitialValues<T extends Record<string, any>>(
  data: T | null,
  options?: UseFormInitialValuesOptions<T>
): UseFormInitialValuesReturn<T> {
  const { switchFields, defaults, transform } = options ?? {};
  const [loading, setLoading] = useState(false);

  // 用 ref 持有可能内联的引用，避免 useMemo 因引用变化重算
  const transformRef = useRef(transform);
  transformRef.current = transform;
  const switchFieldsRef = useRef(switchFields);
  switchFieldsRef.current = switchFields;
  const defaultsRef = useRef(defaults);
  defaultsRef.current = defaults;

  // 计算初始值（仅 data 变化时重算）
  const initialValues = useMemo<Partial<T>>(() => {
    const sf = switchFieldsRef.current;
    const df = defaultsRef.current;

    // 新增模式：使用默认值
    if (!data) {
      const defaultsWithSwitches = transformSwitchValues<T>(df ?? {}, sf);
      return defaultsWithSwitches as Partial<T>;
    }

    // 编辑模式：转换数据
    let transformed = { ...data };

    // 开关字段转换（0/1 -> true/false）
    if (sf && sf.length > 0) {
      transformed = transformSwitchValues<T>(transformed, sf);
    }

    // 自定义转换
    if (transformRef.current) {
      transformed = { ...transformed, ...transformRef.current(data as T) };
    }

    return transformed as Partial<T>;
  }, [data]);

  // 监听数据变化，更新加载状态
  useEffect(() => {
    if (data) {
      setLoading(true);
      // 数据已准备好，立即结束加载状态
      setLoading(false);
    } else {
      setLoading(false);
    }
  }, [data]);

  return {
    initialValues,
    loading,
  };
}

export default useFormInitialValues;
