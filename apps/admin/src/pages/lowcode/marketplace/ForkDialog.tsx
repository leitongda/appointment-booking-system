/** Fork 模板对话框 - 基于模板创建新页面 */

import React, { useState, useEffect, useCallback } from 'react';
import { history } from '@umijs/max';
import { Modal, Form, Input, Button, message, Spin, Typography, Space } from 'antd';
import { CopyOutlined, EyeOutlined } from '@ant-design/icons';
import { lowcodeApi } from '@hospital/api';
import type { LowCodeTemplate } from '@hospital/api';

const { Text } = Typography;

/** 从名称生成 slug: 转小写, 空格/特殊字符替换为连字符, 去首尾连字符 */
const slugify = (name: string): string => {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9一-鿿]+/g, '-')
    .replace(/^-+|-+$/g, '')
    || 'untitled';
};

export interface ForkDialogProps {
  open: boolean;
  template: LowCodeTemplate | null;
  onClose: () => void;
}

const ForkDialog: React.FC<ForkDialogProps> = ({ open, template, onClose }) => {
  const [form] = Form.useForm();
  const [forking, setForking] = useState(false);

  /** 当对话框打开时, 设置默认值 */
  useEffect(() => {
    if (open && template) {
      const defaultName = `${template.name} - 我的副本`;
      form.setFieldsValue({
        name: defaultName,
        slug: slugify(defaultName),
      });
    }
  }, [open, template, form]);

  /** 名称变化时自动同步 slug (仅当 slug 未被手动修改时) */
  const handleNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const name = e.target.value;
      const currentSlug = form.getFieldValue('slug');
      const defaultSlug = slugify(`${template?.name || ''} - 我的副本`);
      // 仅在 slug 仍为默认值时自动更新
      if (!currentSlug || currentSlug === defaultSlug) {
        form.setFieldValue('slug', slugify(name));
      }
    },
    [form, template],
  );

  /** 提交 fork */
  const handleFork = async () => {
    if (!template) return;
    try {
      const values = await form.validateFields();
      setForking(true);
      const result = await lowcodeApi.forkTemplate(template.id, {
        name: values.name,
        slug: values.slug,
      });
      message.success('模板已复制到我的页面');
      onClose();
      history.push(`/platform/lowcode/editor/${result.pageId}`);
    } catch (err: any) {
      if (err?.errorFields) return; // 表单校验失败, 不显示错误
      message.error('Fork 失败，请稍后重试');
    } finally {
      setForking(false);
    }
  };

  if (!template) return null;

  return (
    <Modal
      title={
        <Space>
          <CopyOutlined />
          <span>使用此模板</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={520}
      destroyOnClose
    >
      <Spin spinning={forking}>
        {/* 模板预览 */}
        <div
          style={{
            height: 200,
            background: 'var(--color-bg-container)',
            borderRadius: 8,
            overflow: 'hidden',
            marginBottom: 20,
            border: '1px solid var(--color-border-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {template.thumbnailUrl ? (
            <img
              src={template.thumbnailUrl}
              alt={template.name}
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          ) : (
            <div style={{ textAlign: 'center', color: 'var(--color-border)' }}>
              <EyeOutlined style={{ fontSize: 36, marginBottom: 8 }} />
              <div>预览图暂未提供</div>
            </div>
          )}
        </div>

        {/* 模板名称提示 */}
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          基于「{template.name}」创建新页面
        </Text>

        {/* 表单 */}
        <Form form={form} layout="vertical" requiredMark="optional">
          <Form.Item
            name="name"
            label="页面名称"
            rules={[
              { required: true, message: '请输入页面名称' },
              { max: 100, message: '页面名称最多 100 个字符' },
            ]}
          >
            <Input
              placeholder="请输入页面名称"
              maxLength={100}
              showCount
              onChange={handleNameChange}
            />
          </Form.Item>

          <Form.Item
            name="slug"
            label="页面路径"
            rules={[
              { required: true, message: '请输入页面路径' },
              {
                pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
                message: '路径只能包含小写字母、数字和连字符',
              },
            ]}
            extra="用于 URL 访问，创建后不可修改"
          >
            <Input
              placeholder="请输入页面路径"
              addonBefore="/"
            />
          </Form.Item>
        </Form>

        {/* 操作按钮 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
          <Button onClick={onClose} disabled={forking}>
            取消
          </Button>
          <Button
            type="primary"
            icon={<CopyOutlined />}
            loading={forking}
            onClick={handleFork}
          >
            确认创建
          </Button>
        </div>
      </Spin>
    </Modal>
  );
};

export default ForkDialog;
