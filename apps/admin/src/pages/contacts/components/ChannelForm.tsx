import { ModalForm, ProFormSelect, ProFormSwitch, ProFormText, ProFormTextArea } from '@ant-design/pro-components';
import { Form } from 'antd';
import { useEffect } from 'react';

/** 渠道类型选项 */
const CHANNEL_TYPE_OPTIONS = [
  { label: '微信', value: 'wechat' },
  { label: '短信', value: 'sms' },
  { label: '邮件', value: 'email' },
  { label: 'Webhook', value: 'webhook' },
];

interface ChannelFormProps {
  /** 是否可见 */
  open: boolean;
  /** 关闭回调 */
  onClose: () => void;
  /** 提交成功回调 */
  onSuccess: () => void;
  /** 编辑时的数据 */
  initialValues?: Record<string, any> | null;
}

const ChannelForm: React.FC<ChannelFormProps> = ({ open, onClose, onSuccess, initialValues }) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  useEffect(() => {
    if (open && initialValues) {
      form.setFieldsValue(initialValues);
    } else if (open) {
      form.resetFields();
    }
  }, [open, initialValues, form]);

  const handleSubmit = async (values: any) => {
    const url = isEdit
      ? `/api/v1/channel-accounts/${initialValues.id}`
      : '/api/v1/channel-accounts';
    const method = isEdit ? 'PUT' : 'POST';

    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(values),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || '操作失败');
    }

    onSuccess();
  };

  return (
    <ModalForm
      title={isEdit ? '编辑渠道账号' : '新建渠道账号'}
      open={open}
      onOpenChange={(v) => !v && onClose()}
      onFinish={handleSubmit}
      form={form}
      width={600}
      initialValues={{ status: 1, isDefault: 0 }}
    >
      <ProFormText
        name="name"
        label="账号名称"
        placeholder="如：阿里云短信-主账号"
        rules={[{ required: true, message: '请输入账号名称' }]}
      />
      <ProFormSelect
        name="channelType"
        label="渠道类型"
        options={CHANNEL_TYPE_OPTIONS}
        rules={[{ required: true, message: '请选择渠道类型' }]}
        disabled={isEdit}
      />
      <ProFormSelect
        name="status"
        label="状态"
        options={[
          { label: '正常', value: 1 },
          { label: '禁用', value: 0 },
        ]}
      />
      <ProFormSwitch
        name="isDefault"
        label="默认账号"
        fieldProps={{
          checkedChildren: '是',
          unCheckedChildren: '否',
        }}
      />
      <ProFormTextArea
        name="config"
        label="渠道配置 (JSON)"
        placeholder={'{\n  "app_id": "xxx",\n  "app_secret": "xxx"\n}'}
        fieldProps={{ rows: 6 }}
        rules={[{ required: true, message: '请输入渠道配置' }]}
        tooltip="敏感字段（如 app_secret、access_key_secret）会自动加密存储"
      />
    </ModalForm>
  );
};

export default ChannelForm;
