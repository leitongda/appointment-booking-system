import { ModalForm, ProFormSelect, ProFormText, ProFormTextArea, ProFormDigit } from '@ant-design/pro-components';
import { Form } from 'antd';
import { useEffect } from 'react';

/** 联系人类型选项 */
const CONTACT_TYPE_OPTIONS = [
  { label: '患者', value: 'patient' },
  { label: '医生', value: 'doctor' },
  { label: '管理员', value: 'admin' },
  { label: '员工', value: 'staff' },
  { label: '外部联系人', value: 'external' },
];

/** 性别选项 */
const GENDER_OPTIONS = [
  { label: '未知', value: 0 },
  { label: '男', value: 1 },
  { label: '女', value: 2 },
];

interface ContactFormProps {
  /** 是否可见 */
  open: boolean;
  /** 关闭回调 */
  onClose: () => void;
  /** 提交成功回调 */
  onSuccess: () => void;
  /** 编辑时的联系人数据 */
  initialValues?: Record<string, any> | null;
}

const ContactForm: React.FC<ContactFormProps> = ({ open, onClose, onSuccess, initialValues }) => {
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
      ? `/api/v1/contacts/${initialValues.id}`
      : '/api/v1/contacts';
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
      title={isEdit ? '编辑联系人' : '新建联系人'}
      open={open}
      onOpenChange={(v) => !v && onClose()}
      onFinish={handleSubmit}
      form={form}
      width={600}
      initialValues={{ gender: 0, contactType: 'external', status: 1 }}
    >
      <ProFormText
        name="name"
        label="联系人姓名"
        placeholder="请输入姓名"
        rules={[{ required: true, message: '请输入联系人姓名' }]}
      />
      <ProFormText name="nickname" label="昵称" placeholder="请输入昵称" />
      <ProFormSelect name="gender" label="性别" options={GENDER_OPTIONS} />
      <ProFormSelect
        name="contactType"
        label="联系人类型"
        options={CONTACT_TYPE_OPTIONS}
        rules={[{ required: true, message: '请选择联系人类型' }]}
      />
      <ProFormText name="phone" label="手机号" placeholder="请输入手机号" />
      <ProFormText name="email" label="邮箱" placeholder="请输入邮箱" />
      <ProFormText name="position" label="职位/职称" placeholder="请输入职位" />
      <ProFormText name="organization" label="所属机构" placeholder="请输入机构名称" />
      <ProFormTextArea name="notes" label="备注" placeholder="请输入备注" />
    </ModalForm>
  );
};

export default ContactForm;
