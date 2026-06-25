import { useEffect, useCallback, useRef, useState, useMemo } from 'react';
import type { RefObject } from 'react';
import type { ProFormInstance } from '@ant-design/pro-components';
import { App } from 'antd';
import { debounce } from 'lodash-es';

/**
 * 表单草稿 Hook 配置选项
 */
export interface UseFormDraftOptions {
  /**
   * 草稿存储键，用于标识不同的表单
   */
  key: string;

  /**
   * 防抖延迟时间（毫秒），默认 500ms
   */
  debounceMs?: number;

  /**
   * 排除的字段（这些字段不会被保存到草稿）
   */
  excludeFields?: string[];
}

/**
 * 表单草稿 Hook 返回值
 */
export interface UseFormDraftReturn {
  /**
   * 清除草稿
   */
  clearDraft: () => void;

  /**
   * 是否存在草稿
   */
  hasDraft: boolean;

  /**
   * 恢复草稿到表单
   */
  restoreDraft: () => void;

  /**
   * 表单值变化处理器，传递给 ProForm 的 onValuesChange
   */
  handleValuesChange: (changedValues: any, allValues: any) => void;
}

/**
 * 获取草稿数据
 */
function getDraft(key: string): any {
  try {
    const data = localStorage.getItem(`form-draft-${key}`);
    return data ? JSON.parse(data) : null;
  } catch (error) {
    console.error('[useFormDraft] 读取草稿失败', error);
    return null;
  }
}

/**
 * 保存草稿数据
 */
function saveDraft(key: string, data: any): void {
  try {
    localStorage.setItem(`form-draft-${key}`, JSON.stringify(data));
  } catch (error) {
    console.error('[useFormDraft] 保存草稿失败', error);
  }
}

/**
 * 清除草稿数据
 */
function clearDraftData(key: string): void {
  try {
    localStorage.removeItem(`form-draft-${key}`);
  } catch (error) {
    console.error('[useFormDraft] 清除草稿失败', error);
  }
}

/**
 * 过滤排除的字段
 */
function filterExcludeFields(data: any, excludeFields?: string[]): any {
  if (!excludeFields || excludeFields.length === 0) {
    return data;
  }

  const result = { ...data };
  excludeFields.forEach((field) => {
    delete result[field];
  });
  return result;
}

/**
 * 表单草稿 Hook
 * 自动保存表单草稿到 localStorage，支持防抖、恢复、清理
 *
 * @param formRef ProForm 表单引用
 * @param options 配置选项
 * @returns 草稿操作方法和值变化处理器
 *
 * @example
 * // 基础用法
 * const formRef = useRef<ProFormInstance>();
 * const { clearDraft, hasDraft, restoreDraft, handleValuesChange } = useFormDraft(formRef, {
 *   key: 'user-form',
 * });
 *
 * // 在 ProForm 中使用
 * <ProForm
 *   formRef={formRef}
 *   onValuesChange={handleValuesChange}
 * >
 *   {/* 表单字段 *\/}
 * </ProForm>
 *
 * // 恢复草稿按钮
 * {hasDraft && (
 *   <Button onClick={restoreDraft}>恢复草稿</Button>
 * )}
 *
 * @example
 * // 排除敏感字段
 * const { clearDraft, hasDraft, restoreDraft, handleValuesChange } = useFormDraft(formRef, {
 *   key: 'user-form',
 *   excludeFields: ['password', 'confirmPassword'],
 * });
 *
 * @example
 * // 自定义防抖时间
 * const { clearDraft, hasDraft, restoreDraft, handleValuesChange } = useFormDraft(formRef, {
 *   key: 'user-form',
 *   debounceMs: 1000, // 1秒后保存
 * });
 *
 * @example
 * // 完整使用流程
 * const [showDraftRestore, setShowDraftRestore] = useState(false);
 * const formRef = useRef<ProFormInstance>();
 *
 * const { clearDraft, hasDraft, restoreDraft, handleValuesChange } = useFormDraft(formRef, {
 *   key: 'user-form',
 *   excludeFields: ['password', 'confirmPassword'],
 * });
 *
 * // 检查草稿
 * useEffect(() => {
 *   if (hasDraft) {
 *     setShowDraftRestore(true);
 *   }
 * }, [hasDraft]);
 *
 * // 恢复草稿
 * const handleRestoreDraft = () => {
 *   restoreDraft();
 *   setShowDraftRestore(false);
 *   message.success('草稿已恢复');
 * };
 *
 * // 提交成功后清除草稿
 * const handleSubmit = async (values) => {
 *   await api.create(values);
 *   clearDraft();
 *   message.success('创建成功');
 * };
 *
 * // 渲染
 * {showDraftRestore && (
 *   <Alert
 *     message="检测到未完成的表单草稿"
 *     description={
 *       <Space>
 *         <Button size="small" onClick={handleRestoreDraft}>
 *           恢复草稿
 *         </Button>
 *         <Button size="small" type="link" onClick={clearDraft}>
 *           放弃
 *         </Button>
 *       </Space>
 *     }
 *     type="info"
 *     style={{ marginBottom: 16 }}
 *   />
 * )}
 */
export function useFormDraft(
  formRef: RefObject<ProFormInstance>,
  options: UseFormDraftOptions
): UseFormDraftReturn {
  const { key, debounceMs = 500, excludeFields } = options;
  const { message } = App.useApp();
  const [hasDraft, setHasDraft] = useState(false);
  const isInitializedRef = useRef(false);

  // 检查是否存在草稿
  const checkDraft = useCallback(() => {
    const draft = getDraft(key);
    setHasDraft(!!draft && Object.keys(draft).length > 0);
    return draft;
  }, [key]);

  // 初始化时检查草稿
  useEffect(() => {
    if (!isInitializedRef.current) {
      isInitializedRef.current = true;
      checkDraft();
    }
  }, [checkDraft]);

  // 稳定 excludeFields 引用，避免每次渲染重建 debounce
  const excludeFieldsRef = useRef(excludeFields);
  excludeFieldsRef.current = excludeFields;

  // 保存草稿（防抖）
  const saveDraftInternal = useMemo(
    () =>
      debounce((values: any) => {
        const filtered = filterExcludeFields(values, excludeFieldsRef.current);
        saveDraft(key, filtered);
        setHasDraft(true);
      }, debounceMs),
    [key, debounceMs]
  );

  // 组件卸载时取消 debounce，防止更新已卸载组件的 state
  useEffect(() => {
    return () => {
      saveDraftInternal.cancel();
    };
  }, [saveDraftInternal]);

  // 处理表单值变化
  const handleValuesChange = useCallback(
    (_changedValues: any, allValues: any) => {
      saveDraftInternal(allValues);
    },
    [saveDraftInternal]
  );

  /**
   * 清除草稿
   */
  const clearDraft = useCallback(() => {
    clearDraftData(key);
    setHasDraft(false);
  }, [key]);

  /**
   * 恢复草稿到表单
   */
  const restoreDraft = useCallback(() => {
    const draft = getDraft(key);
    if (!draft) {
      message.warning('未找到草稿数据');
      return;
    }

    const form = formRef.current;
    if (!form) {
      message.error('表单未初始化');
      return;
    }

    try {
      form.setFieldsValue(draft);
      message.success('草稿已恢复');
    } catch (error) {
      console.error('[useFormDraft] 恢复草稿失败', error);
      message.error('恢复草稿失败');
    }
  }, [key, formRef, message]);

  return {
    clearDraft,
    hasDraft,
    restoreDraft,
    handleValuesChange,
  };
}

export default useFormDraft;
