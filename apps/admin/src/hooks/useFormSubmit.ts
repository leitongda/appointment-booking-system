import { useState, useCallback } from 'react';
import { App } from 'antd';

/**
 * 表单提交 Hook 配置选项
 */
export interface UseFormSubmitOptions<T> {
  /**
   * 需要转换的开关字段（true/false -> 0/1）
   */
  switchFields?: (keyof T)[];

  /**
   * 提交成功回调
   */
  onSuccess?: () => void;

  /**
   * 成功提示文案
   */
  successMessage?: string;

  /**
   * 失败提示文案
   */
  errorMessage?: string;

  /**
   * 自定义数据转换函数
   * 在开关字段转换之后执行，可以对数据进行任意转换
   */
  transform?: (values: T) => any;
}

/**
 * 表单提交 Hook 返回值
 */
export interface UseFormSubmitReturn<T> {
  /**
   * 提交处理函数
   */
  handleSubmit: (values: T) => Promise<void>;

  /**
   * 是否正在提交
   */
  submitting: boolean;
}

/**
 * 将布尔开关值（true/false）转换为数字（0/1）
 */
function transformSwitchValues<T>(values: any, switchFields?: (keyof T)[]): any {
  if (!switchFields || switchFields.length === 0) {
    return values;
  }

  const result = { ...values };
  switchFields.forEach((field) => {
    if (result[field] !== undefined) {
      result[field] = result[field] ? 1 : 0;
    }
  });
  return result;
}

/**
 * 表单提交 Hook
 * 封装表单提交逻辑，处理开关字段转换、成功/失败提示
 *
 * @param submitFn 提交函数
 * @param options 配置选项
 * @returns 提交处理函数和状态
 *
 * @example
 * // 基础用法
 * const { handleSubmit, submitting } = useFormSubmit(
 *   async (values) => {
 *     await api.create(values);
 *   },
 *   {
 *     successMessage: '创建成功',
 *     onSuccess: () => history.back(),
 *   }
 * );
 *
 * @example
 * // 带开关字段转换
 * const { handleSubmit, submitting } = useFormSubmit(
 *   async (values) => {
 *     await api.create(values);
 *   },
 *   {
 *     switchFields: ['status', 'isDefault'],
 *     successMessage: '保存成功',
 *   }
 * );
 *
 * @example
 * // 使用自定义转换
 * const { handleSubmit, submitting } = useFormSubmit(
 *   async (values) => {
 *     await api.create(values);
 *   },
 *   {
 *     switchFields: ['status'],
 *     transform: (values) => ({
 *       ...values,
 *       publishTime: values.publishTime || undefined,
 *     }),
 *   }
 * );
 *
 * @example
 * // 完整示例
 * const { handleSubmit, submitting } = useFormSubmit(
 *   async (values) => {
 *     if (isEdit && id) {
 *       await api.update(id, values);
 *     } else {
 *       await api.create(values);
 *     }
 *   },
 *   {
 *     switchFields: ['status'],
 *     successMessage: isEdit ? '更新成功' : '创建成功',
 *     errorMessage: '操作失败，请重试',
 *     onSuccess: () => {
 *       history.back();
 *       // 刷新列表
 *       actionRef.current?.reload();
 *     },
 *     transform: (values) => {
 *       const { confirmPassword, ...rest } = values;
 *       return rest;
 *     },
 *   }
 * );
 */
export function useFormSubmit<T extends Record<string, any>, R = void>(
  submitFn: (values: T) => Promise<R>,
  options?: UseFormSubmitOptions<T>
): UseFormSubmitReturn<T> {
  const { message } = App.useApp();
  const [submitting, setSubmitting] = useState(false);

  const {
    switchFields,
    onSuccess,
    successMessage = '操作成功',
    errorMessage = '操作失败',
    transform,
  } = options ?? {};

  const handleSubmit = useCallback(
    async (values: T): Promise<void> => {
      setSubmitting(true);

      try {
        // 转换开关字段（true/false -> 0/1）
        let transformedValues = values;
        if (switchFields && switchFields.length > 0) {
          transformedValues = transformSwitchValues<T>(values, switchFields) as T;
        }

        // 自定义转换
        let finalValues = transformedValues;
        if (transform) {
          finalValues = transform(transformedValues);
        }

        // 执行提交
        await submitFn(finalValues);

        // 成功提示
        if (successMessage) {
          message.success(successMessage);
        }

        // 成功回调
        if (onSuccess) {
          onSuccess();
        }
      } catch (error: any) {
        // 失败提示（不 re-throw，避免 ProForm 触发 error boundary remount）
        message.error(error.message || errorMessage);
      } finally {
        setSubmitting(false);
      }
    },
    [submitFn, switchFields, transform, onSuccess, successMessage, errorMessage, message]
  );

  return {
    handleSubmit,
    submitting,
  };
}

export default useFormSubmit;
