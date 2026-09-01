/** 分享到模板市场弹窗 — 将当前页面发布为市场模板 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Upload,
  Button,
  message,
  Space,
  Tag,
  Result,
  Spin,
} from 'antd';
import { UploadOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { request, uploadApi } from '@hospital/api';
import { useEditorStore } from '../store';

const { TextArea } = Input;

/** 模板分类选项 */
const CATEGORY_OPTIONS = [
  { value: 'appointment', label: '预约挂号' },
  { value: 'registration', label: '临时挂号' },
  { value: 'inquiry', label: '问诊' },
  { value: 'report', label: '报告查询' },
  { value: 'notice', label: '公告通知' },
  { value: 'form', label: '表单收集' },
  { value: 'landing', label: '落地页' },
  { value: 'other', label: '其他' },
];

/** 预设标签 */
const PRESET_TAGS = [
  '多科室',
  '预约挂号',
  '临时挂号',
  '在线问诊',
  '报告查询',
  '公告通知',
  '表单',
  '落地页',
  '移动端',
  'PC端',
  '响应式',
  '推荐',
];

interface ShareDialogProps {
  open: boolean;
  onClose: () => void;
}

/** 上传缩略图列表项 */
interface ThumbnailFile {
  uid: string;
  url?: string;
  key?: string;
  uploading?: boolean;
}

const ShareDialog: React.FC<ShareDialogProps> = ({ open, onClose }) => {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [thumbnail, setThumbnail] = useState<ThumbnailFile | null>(null);
  const [uploading, setUploading] = useState(false);
  const [tags, setTags] = useState<string[]>([]);
  const [tagInputVisible, setTagInputVisible] = useState(false);
  const [tagInputValue, setTagInputValue] = useState('');

  const pageId = useEditorStore((s) => s.pageId);
  const schema = useEditorStore((s) => s.schema);

  /** 页面标题 */
  const pageTitle = (schema.props?.navigationBarTitleText as string) || '新页面';

  /** 打开时用页面名填充表单 */
  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        name: pageTitle,
        shortDescription: '',
        description: '',
        category: undefined,
      });
      setThumbnail(null);
      setTags([]);
      setTagInputVisible(false);
      setTagInputValue('');
      setSubmitSuccess(false);
    }
  }, [open, pageTitle, form]);

  /** 处理缩略图上传 */
  const handleUpload = useCallback(async (file: File) => {
    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
      message.error('图片大小不能超过 5MB');
      return false;
    }

    setUploading(true);
    try {
      const result = await uploadApi.upload(file, 'lowcode/thumbnails');
      setThumbnail({
        uid: `thumb-${Date.now()}`,
        url: result.url,
        key: result.key,
      });
      message.success('缩略图上传成功');
    } catch (err) {
      message.error('缩略图上传失败');
      console.error(err);
    } finally {
      setUploading(false);
    }
    return false; // 阻止 antd Upload 自动上传
  }, []);

  /** 移除缩略图 */
  const handleRemoveThumbnail = useCallback(() => {
    setThumbnail(null);
  }, []);

  /** 标签输入 */
  const handleTagClose = useCallback(
    (removedTag: string) => {
      setTags((prev) => prev.filter((t) => t !== removedTag));
    },
    [],
  );

  const handleTagInputConfirm = useCallback(() => {
    const val = tagInputValue.trim();
    if (val && !tags.includes(val)) {
      setTags((prev) => [...prev, val]);
    }
    setTagInputVisible(false);
    setTagInputValue('');
  }, [tagInputValue, tags]);

  /** 提交分享 */
  const handleSubmit = useCallback(async () => {
    if (!pageId) {
      message.warning('请先保存页面');
      return;
    }

    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const payload = {
        pageId,
        name: values.name,
        shortDescription: values.shortDescription,
        description: values.description || values.shortDescription,
        category: values.category,
        tags,
        thumbnailUrl: thumbnail?.url || null,
        thumbnailKey: thumbnail?.key || null,
        isPublic: true,
      };

      await request.post(`/lowcode/pages/${pageId}/publish-to-marketplace`, payload);
      setSubmitSuccess(true);
      message.success('已提交到模板市场');
    } catch (err: any) {
      if (err?.errorFields) return; // 表单校验失败，不显示错误
      message.error('提交失败，请重试');
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  }, [pageId, form, tags, thumbnail]);

  /** 关闭弹窗 */
  const handleClose = useCallback(() => {
    form.resetFields();
    setThumbnail(null);
    setTags([]);
    setSubmitSuccess(false);
    onClose();
  }, [form, onClose]);

  /** 提交成功后的结果页 */
  if (submitSuccess) {
    return (
      <Modal
        title="分享到模板市场"
        open={open}
        onCancel={handleClose}
        footer={
          <Button type="primary" onClick={handleClose}>
            完成
          </Button>
        }
        width={480}
        destroyOnClose
      >
        <Result
          status="success"
          title="提交成功"
          subTitle="您的页面已提交到模板市场，审核通过后将展示给所有用户。"
          extra={[
            <Button key="close" type="primary" onClick={handleClose}>
              完成
            </Button>,
          ]}
        />
      </Modal>
    );
  }

  return (
    <Modal
      title="分享到模板市场"
      open={open}
      onCancel={handleClose}
      onOk={handleSubmit}
      okText="提交审核"
      cancelText="取消"
      confirmLoading={submitting}
      width={560}
      destroyOnClose
      maskClosable={!submitting}
    >
      <Spin spinning={submitting}>
        <Form
          form={form}
          layout="vertical"
          requiredMark="optional"
          initialValues={{
            name: pageTitle,
          }}
        >
          {/* 模板名称 */}
          <Form.Item
            name="name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入模板名称" maxLength={50} showCount />
          </Form.Item>

          {/* 简短描述 */}
          <Form.Item
            name="shortDescription"
            label="简短描述"
            rules={[{ required: true, message: '请输入简短描述' }]}
          >
            <Input placeholder="一句话描述模板用途（50字以内）" maxLength={50} showCount />
          </Form.Item>

          {/* 详细描述 */}
          <Form.Item
            name="description"
            label="详细描述"
            rules={[{ required: true, message: '请输入详细描述' }]}
          >
            <TextArea
              placeholder="详细描述模板的功能、适用场景等（可包含 Markdown 格式）"
              rows={4}
              maxLength={500}
              showCount
            />
          </Form.Item>

          {/* 分类 */}
          <Form.Item
            name="category"
            label="模板分类"
            rules={[{ required: true, message: '请选择模板分类' }]}
          >
            <Select placeholder="请选择分类" options={CATEGORY_OPTIONS} />
          </Form.Item>

          {/* 标签 */}
          <Form.Item label="标签">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
              {tags.map((tag) => (
                <Tag
                  key={tag}
                  closable
                  onClose={() => handleTagClose(tag)}
                  style={{ margin: 0 }}
                >
                  {tag}
                </Tag>
              ))}
              {tagInputVisible ? (
                <Input
                  type="text"
                  size="small"
                  style={{ width: 100 }}
                  value={tagInputValue}
                  onChange={(e) => setTagInputValue(e.target.value)}
                  onBlur={handleTagInputConfirm}
                  onPressEnter={handleTagInputConfirm}
                  autoFocus
                />
              ) : (
                <Tag
                  onClick={() => setTagInputVisible(true)}
                  style={{ borderStyle: 'dashed', cursor: 'pointer' }}
                >
                  <PlusOutlined /> 自定义标签
                </Tag>
              )}
            </div>
            <div>
              <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>预设标签：</span>
              {PRESET_TAGS.filter((t) => !tags.includes(t)).map((tag) => (
                <Tag
                  key={tag}
                  style={{ cursor: 'pointer', margin: '2px 0' }}
                  onClick={() => {
                    if (!tags.includes(tag)) {
                      setTags((prev) => [...prev, tag]);
                    }
                  }}
                >
                  + {tag}
                </Tag>
              ))}
            </div>
          </Form.Item>

          {/* 缩略图上传 */}
          <Form.Item label="预览缩略图">
            <Space direction="vertical" size={8}>
              <Upload
                accept="image/*"
                showUploadList={false}
                beforeUpload={handleUpload}
                disabled={uploading}
              >
                {thumbnail?.url ? (
                  <div
                    style={{
                      width: 160,
                      height: 90,
                      border: '1px solid var(--color-border)',
                      borderRadius: 6,
                      overflow: 'hidden',
                      position: 'relative',
                      cursor: 'pointer',
                    }}
                  >
                    <img
                      src={thumbnail.url}
                      alt="缩略图"
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                    <div
                      style={{
                        position: 'absolute',
                        top: 4,
                        right: 4,
                      }}
                    >
                      <Button
                        type="text"
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveThumbnail();
                        }}
                        style={{ color: 'var(--color-error)', background: 'rgba(255,255,255,0.8)' }}
                      />
                    </div>
                  </div>
                ) : (
                  <div
                    style={{
                      width: 160,
                      height: 90,
                      border: '1px dashed var(--color-border)',
                      borderRadius: 6,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: uploading ? 'not-allowed' : 'pointer',
                      background: 'var(--color-bg-container)',
                    }}
                  >
                    <UploadOutlined style={{ fontSize: 20, color: 'var(--color-text-tertiary)', marginBottom: 4 }} />
                    <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>
                      {uploading ? '上传中...' : '上传缩略图'}
                    </span>
                  </div>
                )}
              </Upload>
              <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>
                建议尺寸 800x450，支持 JPG/PNG，最大 5MB
              </span>
            </Space>
          </Form.Item>
        </Form>
      </Spin>
    </Modal>
  );
};

export default ShareDialog;
