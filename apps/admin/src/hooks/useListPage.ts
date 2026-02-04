import { useRef, useCallback } from 'react';
import type { ActionType } from '@ant-design/pro-components';
import { App } from 'antd';
import { useAccess } from '@umijs/max';

/**
 * 列表页通用 Hook 配置选项
 */
export interface UseListPageOptions {
  /** 删除 API 函数（返回值类型可以是 void 或其他任意类型） */
  deleteFn?: (id: string) => Promise<any>;
  /** 删除成功提示文案 */
  deleteSuccessText?: string;
  /** 删除失败提示文案 */
  deleteErrorText?: string;
}

/**
 * 列表页通用 Hook 返回值
 */
export interface UseListPageReturn {
  /** ProTable actionRef */
  actionRef: React.RefObject<ActionType | undefined>;
  /** Ant Design message API */
  message: ReturnType<typeof App.useApp>['message'];
  /** 权限对象 */
  access: ReturnType<typeof useAccess>;
  /** 通用删除处理函数 */
  handleDelete: (id: string) => Promise<void>;
  /** 刷新表格 */
  reload: () => void;
  /** 通用操作处理函数（带成功/失败提示） */
  handleAction: <T>(
    action: () => Promise<T>,
    options?: { successText?: string; errorText?: string; reloadOnSuccess?: boolean }
  ) => Promise<T | undefined>;
}

/**
 * 列表页通用 Hook
 * 封装 actionRef、message、access、handleDelete 等通用逻辑
 *
 * @example
 * ```tsx
 * const { actionRef, access, handleDelete, reload } = useListPage({
 *   deleteFn: contentApi.deleteNews,
 * });
 * ```
 */
export function useListPage(options?: UseListPageOptions): UseListPageReturn {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();

  const {
    deleteFn,
    deleteSuccessText = '删除成功',
    deleteErrorText = '删除失败',
  } = options ?? {};

  /**
   * 刷新表格
   */
  const reload = useCallback(() => {
    actionRef.current?.reload();
  }, []);

  /**
   * 通用操作处理函数
   */
  const handleAction = useCallback(
    async <T>(
      action: () => Promise<T>,
      actionOptions?: { successText?: string; errorText?: string; reloadOnSuccess?: boolean }
    ): Promise<T | undefined> => {
      const { successText, errorText = '操作失败', reloadOnSuccess = false } = actionOptions ?? {};
      try {
        const result = await action();
        if (successText) {
          message.success(successText);
        }
        if (reloadOnSuccess) {
          reload();
        }
        return result;
      } catch (error: any) {
        message.error(error.message || errorText);
        return undefined;
      }
    },
    [message, reload]
  );

  /**
   * 通用删除处理函数
   */
  const handleDelete = useCallback(
    async (id: string): Promise<void> => {
      if (!deleteFn) {
        console.warn('[useListPage] deleteFn is not provided');
        return;
      }
      try {
        await deleteFn(id);
        message.success(deleteSuccessText);
        reload();
      } catch (error: any) {
        message.error(error.message || deleteErrorText);
      }
    },
    [deleteFn, deleteSuccessText, deleteErrorText, message, reload]
  );

  return {
    actionRef,
    message,
    access,
    handleDelete,
    reload,
    handleAction,
  };
}

export default useListPage;
