/**
 * 级联选择编排 Hook
 *
 * 统一管理多级联动选择的状态：父级变化时自动清空下游级。
 * 适用于门店→科室→医生等常见的级联选择场景。
 *
 * @example
 * ```tsx
 * const cascade = useCascadingSelect({
 *   levels: [
 *     { key: 'storeId' },
 *     { key: 'departmentId' },
 *     { key: 'doctorId' },
 *   ],
 * });
 *
 * <Select onChange={cascade.getOnChange('storeId')} />
 * <Select onChange={cascade.getOnChange('departmentId')} />
 * <Select onChange={cascade.getOnChange('doctorId')} />
 *
 * // 读取当前值
 * useDoctors({ departmentId: cascade.values.departmentId });
 * ```
 */
import { useState, useCallback, useMemo } from 'react';

interface CascadeLevel {
  key: string;
  /** 当父级变化时是否清空此级，默认 true */
  clearOnParentChange?: boolean;
}

interface UseCascadingSelectOptions {
  levels: CascadeLevel[];
  /** 某级变化时触发的额外副作用 */
  onLevelChange?: (changedKey: string, value: string | undefined) => void;
}

interface UseCascadingSelectReturn {
  /** 用于各 Select 的 onChange — 自动清空所有下游级 */
  getOnChange: (key: string) => (val: any) => void;
  /** 获取当前所有级的值 */
  values: Record<string, string | undefined>;
  /** 重置所有级为 undefined */
  reset: () => void;
}

export function useCascadingSelect(
  options: UseCascadingSelectOptions
): UseCascadingSelectReturn {
  const { levels, onLevelChange } = options;

  // 为每个 level 维护一个 string | undefined 状态
  const [state, setState] = useState<Record<string, string | undefined>>(() => {
    const initial: Record<string, string | undefined> = {};
    for (const level of levels) {
      initial[level.key] = undefined;
    }
    return initial;
  });

  const getOnChange = useCallback(
    (key: string) => (val: any) => {
      setState((prev) => {
        const next = { ...prev, [key]: val ?? undefined };

        // 找到该级在 levels 数组中的 index，清空下游级
        const idx = levels.findIndex((l) => l.key === key);
        if (idx >= 0) {
          for (let i = idx + 1; i < levels.length; i++) {
            if (levels[i].clearOnParentChange !== false) {
              next[levels[i].key] = undefined;
            }
          }
        }

        return next;
      });

      onLevelChange?.(key, val ?? undefined);
    },
    [levels, onLevelChange]
  );

  const reset = useCallback(() => {
    setState((prev) => {
      const next = { ...prev };
      for (const level of levels) {
        next[level.key] = undefined;
      }
      return next;
    });
  }, [levels]);

  return useMemo(
    () => ({ getOnChange, values: state, reset }),
    [getOnChange, state, reset]
  );
}
