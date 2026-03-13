import { useState, useCallback, useRef, useMemo } from 'react';

/**
 * 唯一性验证 Hook 配置选项
 */
export interface UseUniqueValidationOptions {
  /**
   * 防抖延迟时间（毫秒），默认 300ms
   */
  debounceMs?: number;
}

/**
 * 唯一性验证 Hook 返回值
 */
export interface UseUniqueValidationReturn {
  /**
   * 验证函数
   * @param field 字段名
   * @param value 字段值
   * @param excludeId 排除的 ID（编辑时使用，排除当前项）
   */
  validate: (field: string, value: string, excludeId?: number) => Promise<void>;

  /**
   * 是否正在验证
   */
  checking: boolean;
}

/**
 * 唯一性验证函数类型
 * @param field 字段名
 * @param value 字段值
 * @param excludeId 排除的 ID
 * @returns 是否唯一（true 表示唯一，false 表示已存在）
 */
export type UniqueCheckFn = (
  field: string,
  value: string,
  excludeId?: number
) => Promise<boolean>;

/**
 * 防抖函数
 */
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}

/**
 * 唯一性验证 Hook
 * 提供带防抖的唯一性验证功能，用于表单字段的异步验证
 *
 * @param checkFn 唯一性检查函数，返回 true 表示唯一，false 表示已存在
 * @param options 配置选项
 * @returns 验证函数和状态
 *
 * @example
 * // 基础用法
 * const { validate, checking } = useUniqueValidation(
 *   async (field, value) => {
 *     const { data } = await api.checkUnique({ field, value });
 *     return data.isUnique;
 *   }
 * );
 *
 * // 在表单中使用
 * <ProFormText
 *   name="username"
 *   label="用户名"
 *   rules={[
 *     { required: true, message: '请输入用户名' },
 *     {
 *       validator: (_, value) => validate('username', value),
 *     },
 *   ]}
 *   validateStatus={checking ? 'validating' : undefined}
 * />
 *
 * @example
 * // 编辑模式 - 排除当前项
 * const { validate, checking } = useUniqueValidation(
 *   async (field, value, excludeId) => {
 *     const { data } = await api.checkUnique({ field, value, excludeId });
 *     return data.isUnique;
 *   }
 * );
 *
 * // 验证时排除当前编辑项
 * await validate('username', 'admin', currentUserId);
 *
 * @example
 * // 自定义防抖时间
 * const { validate, checking } = useUniqueValidation(
 *   checkFn,
 *   { debounceMs: 500 }
 * );
 */
export function useUniqueValidation(
  checkFn: UniqueCheckFn,
  options?: UseUniqueValidationOptions
): UseUniqueValidationReturn {
  const { debounceMs = 300 } = options ?? {};
  const [checking, setChecking] = useState(false);
  const checkingRef = useRef(false);

  // 原始验证函数
  const validateInternal = useCallback(
    async (field: string, value: string, excludeId?: number): Promise<void> => {
      // 空值不验证
      if (!value || value.trim() === '') {
        return;
      }

      checkingRef.current = true;
      setChecking(true);

      try {
        const isUnique = await checkFn(field, value, excludeId);
        if (!isUnique) {
          throw new Error(`该${field}已存在`);
        }
      } finally {
        checkingRef.current = false;
        setChecking(false);
      }
    },
    [checkFn]
  );

  // 防抖验证函数
  const validate = useMemo(
    () => debounce(validateInternal, debounceMs),
    [validateInternal, debounceMs]
  );

  return {
    validate: validate as (field: string, value: string, excludeId?: number) => Promise<void>,
    checking,
  };
}

export default useUniqueValidation;
