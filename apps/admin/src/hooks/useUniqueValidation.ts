import {useState} from 'react';

/**
 * useFieldUnique 配置选项
 */
export interface UseFieldUniqueConfig<T = void> {
  /** 唯一性检查函数 */
  checkFn: (value: string, excludeId?: string | number) => Promise<{ isUnique: boolean; extra?: T }>;
  /** 错误消息，默认 '该值已存在' */
  message?: string;
  /** 不唯一时的回调（如 suggestions） */
  onNotUnique?: (extra: T) => void;
  /** 排除的 ID（编辑时排除自身） */
  excludeId?: string | number;
}

/**
 * useFieldUnique 返回值
 */
export interface UseFieldUniqueReturn<_T = void> {
  /** Ant Design Form rule，可直接放入 rules 数组 */
  rule: Record<string, any>;
  /** 该字段是否正在校验 */
  checking: boolean;
}

/**
 * 单字段唯一性校验 Hook
 *
 * 返回一个 Ant Design Form rule 对象，可直接放入 rules 数组。
 * 空值直接通过，不调用 API。API 失败时不阻止提交。
 *
 * @example
 * // 基础用法（门店名称）
 * const { rule: nameRule } = useFieldUnique({
 *   checkFn: (value, excludeId) =>
 *     storeApi.checkUnique('name', value, excludeId).then(r => ({ isUnique: !r.exists })),
 *   message: '该门店名称已存在',
 *   excludeId: isEdit ? id : undefined,
 * });
 *
 * // 带 suggestions 回调（医生账号）
 * const [suggestions, setSuggestions] = useState<string[]>([]);
 * const { rule: usernameRule, checking } = useFieldUnique<{ suggestions: string[] }>({
 *   checkFn: async (value, excludeId) => {
 *     const res = await doctorApi.checkUsername(value, excludeId);
 *     return { isUnique: !res.exists, extra: { suggestions: res.suggestions } };
 *   },
 *   message: '该账号已存在',
 *   onNotUnique: (extra) => setSuggestions(extra.suggestions),
 * });
 */
export function useFieldUnique<T = void>(config: UseFieldUniqueConfig<T>): UseFieldUniqueReturn<T> {
  const { checkFn, message = '该值已存在', onNotUnique, excludeId } = config;
  const [checking, setChecking] = useState(false);

  const rule = {
    validator: async (_: any, value: any) => {
      if (!value) return;
      setChecking(true);
      try {
        const result = await checkFn(String(value), excludeId);
        if (!result.isUnique) {
          onNotUnique?.(result.extra as T);
          throw new Error(message);
        }
      } catch (e: any) {
        if (e.message === message) throw e; // 重新抛出业务错误
        // API 错误不阻止提交
      } finally {
        setChecking(false);
      }
    },
  };

  return { rule, checking };
}

export default useFieldUnique;
