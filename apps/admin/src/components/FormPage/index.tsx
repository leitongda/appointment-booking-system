/**
 * 表单页面容器组件
 *
 * 功能：
 * - 统一封装 PageContainer、ProForm、Card 布局
 * - 统一处理加载状态
 * - 统一底部按钮布局（FooterToolbar）
 * - 减少表单页面重复代码
 */
import { PageContainer, ProForm, FooterToolbar } from '@ant-design/pro-components';
import { Card, Space, Button, Spin } from 'antd';
import type { ProFormInstance } from '@ant-design/pro-components';
import React, { ReactNode, useRef } from 'react';

/**
 * 表单页面容器组件属性
 */
export interface FormPageProps {
  /** 页面标题 */
  title: string;
  /** 表单实例引用 */
  formRef?: React.RefObject<ProFormInstance>;
  /** 加载状态 */
  loading?: boolean;
  /** 保存按钮文本 */
  saveText?: string;
  /** 取消按钮文本 */
  cancelText?: string;
  /** 取消回调 */
  onCancel: () => void;
  /** 表单提交回调 */
  onFinish: (values: any) => Promise<void> | void;
  /** 表单初始值 */
  initialValues?: any;
  /** 提交按钮加载状态 */
  submitting?: boolean;
  /** 是否显示底部工具栏 */
  showFooter?: boolean;
  /** 子元素 */
  children: ReactNode;
  /** ProForm 的其他属性 */
  formProps?: Partial<React.ComponentProps<typeof ProForm>>;
  /** PageContainer 的其他属性 */
  pageContainerProps?: Partial<React.ComponentProps<typeof PageContainer>>;
}

/**
 * 表单页面容器组件
 *
 * @example
 * ```tsx
 * <FormPage
 *   title="新增用户"
 *   loading={loading}
 *   onFinish={handleSubmit}
 *   onCancel={() => history.back()}
 *   initialValues={{ status: true }}
 * >
 *   <Card title="基础信息">
 *     <ProFormText name="username" label="账号" />
 *   </Card>
 * </FormPage>
 * ```
 */
const FormPage: React.FC<FormPageProps> = ({
  title,
  formRef: externalFormRef,
  loading = false,
  saveText = '保存',
  cancelText = '取消',
  onCancel,
  onFinish,
  initialValues,
  submitting = false,
  showFooter = true,
  children,
  formProps,
  pageContainerProps,
}) => {
  const internalFormRef = useRef<ProFormInstance>();
  const formRef = externalFormRef || internalFormRef;

  // 处理表单提交
  const handleSubmit = async (values: any) => {
    await onFinish(values);
  };

  // 触发表单提交
  const handleSave = () => {
    formRef.current?.submit();
  };

  // 渲染底部工具栏
  const renderSubmitter = () => {
    if (!showFooter) return false;

    return {
      render: () => (
        <FooterToolbar>
          <Space>
            <Button onClick={onCancel} disabled={submitting}>
              {cancelText}
            </Button>
            <Button type="primary" onClick={handleSave} loading={submitting}>
              {saveText}
            </Button>
          </Space>
        </FooterToolbar>
      ),
    };
  };

  // 加载状态渲染
  if (loading && !initialValues) {
    return (
      <PageContainer title={title} {...pageContainerProps}>
        <Card>
          <div style={{ textAlign: 'center', padding: '50px 0' }}>
            <Spin tip="加载中..." />
          </div>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer title={title} {...pageContainerProps}>
      <ProForm
        formRef={formRef}
        onFinish={handleSubmit}
        initialValues={initialValues}
        submitter={renderSubmitter()}
        {...formProps}
      >
        {children}
      </ProForm>
    </PageContainer>
  );
};

export default FormPage;
