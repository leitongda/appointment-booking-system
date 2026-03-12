import { Modal, Input, Alert, Space } from 'antd';
import { useState, useCallback } from 'react';

const CONFIRM_TEXT = 'CONFIRM';

interface ConfirmDeleteOptions {
  title?: string;
  content?: React.ReactNode;
  alertMessage?: string;
  onOk: () => void | Promise<void>;
}

/**
 * 强制确认删除的 Modal
 * 用户需要输入 "CONFIRM" 才能启用删除按钮
 */
export const confirmDelete = (options: ConfirmDeleteOptions) => {
  const { title = '确认删除', content, alertMessage, onOk } = options;

  let inputValue = '';
  let modalInstance: ReturnType<typeof Modal.confirm>;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    inputValue = e.target.value;
    // 通过更新按钮状态来反映输入变化
    modalInstance.update({
      okButtonProps: {
        disabled: inputValue !== CONFIRM_TEXT,
      },
    });
  };

  modalInstance = Modal.confirm({
    title,
    width: 480,
    icon: null,
    content: (
      <div style={{ marginTop: 16 }}>
        {content}
        {alertMessage && (
          <Alert
            message={alertMessage}
            type="warning"
            showIcon
            style={{ marginTop: 12 }}
          />
        )}
        <Space direction="vertical" style={{ width: '100%', marginTop: 16 }}>
          <div>
            请输入 <strong style={{ color: '#ff4d4f' }}>{CONFIRM_TEXT}</strong> 以确认删除操作：
          </div>
          <Input
            placeholder={`请输入 ${CONFIRM_TEXT}`}
            onChange={handleInputChange}
            onPressEnter={() => {
              if (inputValue === CONFIRM_TEXT) {
                modalInstance.destroy();
                onOk();
              }
            }}
            autoFocus
          />
        </Space>
        <Alert
          message="此操作不可撤销！"
          type="error"
          showIcon
          style={{ marginTop: 12 }}
        />
      </div>
    ),
    okText: '确认删除',
    okType: 'danger',
    okButtonProps: {
      disabled: true, // 初始禁用
    },
    cancelText: '取消',
    onOk: async () => {
      if (inputValue === CONFIRM_TEXT) {
        await onOk();
      }
    },
  });

  return modalInstance;
};

/**
 * useConfirmDelete hook
 * 提供一个可复用的删除确认方法
 */
export const useConfirmDelete = () => {
  return useCallback((options: ConfirmDeleteOptions) => {
    return confirmDelete(options);
  }, []);
};

export default confirmDelete;
