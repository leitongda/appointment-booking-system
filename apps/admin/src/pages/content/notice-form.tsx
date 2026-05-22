/**
 * 公告表单页面
 *
 * 公告类型通过 useDict('notice_type') 从字典 API 获取
 */
import { ProFormText, ProFormSelect } from '@ant-design/pro-components';
import { Card, Form } from 'antd';
import { useEffect, useState, useMemo } from 'react';
import { useParams, history } from '@umijs/max';
import { contentApi } from '@hospital/api';
import type { Notice } from '@hospital/api';

// 基础设施导入
import FormPage from '@/components/FormPage';
import { SwitchGroup } from '@/components/formFields';
import RichTextEditor from '@/components/RichTextEditor';
import { useDict } from '@/hooks/useDict';
import { useFormInitialValues } from '@/hooks/useFormInitialValues';
import { useFormSubmit } from '@/hooks/useFormSubmit';

const NoticeFormPage: React.FC = () => {
  const { id } = useParams();
  const isEdit = !!id;
  const [notice, setNotice] = useState<Notice | null>(null);
  const [loading, setLoading] = useState(false);

  // 字典数据
  const { options: noticeTypeDict } = useDict('notice_type');
  const noticeTypeOptions = useMemo(() => noticeTypeDict.map(o => ({ label: o.label, value: Number(o.value) })), [noticeTypeDict]);

  // 加载公告数据
  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      contentApi
        .getNoticeDetail(id)
        .then((data) => {
          setNotice(data);
        })
        .catch(() => {
          // 错误在 useFormSubmit 中处理
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [id, isEdit]);

  // 使用 useFormInitialValues hook 处理初始值
  const { initialValues } = useFormInitialValues<Notice>(
    notice,
    {
      switchFields: ['isTop', 'status'],
      defaults: {
        type: 1,
        isTop: false,
        status: true,
      } as unknown as Partial<Notice>,
    }
  );

  // 使用 useFormSubmit hook 处理提交
  const { handleSubmit, submitting } = useFormSubmit<Notice>(
    async (values) => {
      if (isEdit && id) {
        await contentApi.updateNotice(id, values as any);
      } else {
        await contentApi.createNotice(values as any);
      }
    },
    {
      switchFields: ['isTop', 'status'],
      successMessage: isEdit ? '更新成功' : '发布成功',
      onSuccess: () => {
        history.push('/content-center/content/notice');
      },
    }
  );

  return (
    <FormPage
      title={isEdit ? '编辑公告' : '发布公告'}
      loading={loading}
      submitting={submitting}
      initialValues={initialValues}
      onFinish={handleSubmit}
      onCancel={() => history.back()}
      saveText={isEdit ? '保存' : '发布'}
    >
      {/* 公告信息 */}
      <Card title="公告信息" style={{ marginBottom: 16 }}>
        <ProFormText
          name="title"
          label="标题"
          width="lg"
          rules={[{ required: true, message: '请输入标题' }]}
        />
        <ProFormSelect
          name="type"
          label="类型"
          width="md"
          options={noticeTypeOptions}
          rules={[{ required: true, message: '请选择类型' }]}
        />
      </Card>

      {/* 公告内容 */}
      <Card title="公告内容" style={{ marginBottom: 16 }}>
        <Form.Item
          name="content"
          label="内容"
          rules={[{ required: true, message: '请输入内容' }]}
        >
          <RichTextEditor height={400} placeholder="请输入公告内容..." />
        </Form.Item>
      </Card>

      {/* 发布设置 */}
      <Card title="发布设置">
        <SwitchGroup
          items={[
            { name: 'isTop', label: '置顶' },
            { name: 'status', label: '立即发布' },
          ]}
        />
      </Card>
    </FormPage>
  );
};

export default NoticeFormPage;
