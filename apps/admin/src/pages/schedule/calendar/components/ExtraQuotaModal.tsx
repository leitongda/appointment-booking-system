import { Modal, Form, InputNumber, Radio, Switch, Select, Input, App, Spin, Descriptions, Divider } from 'antd';
import { useState, useEffect } from 'react';
import { scheduleApi, patientApi } from '@hospital/api';
import type { PatientListItem } from '@hospital/api';

interface ExtraQuotaModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  scheduleId: string;
  scheduleInfo?: {
    doctorName?: string;
    scheduleDate?: string;
    timeSlot?: string;
    totalSlots?: number;
    bookedSlots?: number;
  };
}

const TIME_SLOT_LABELS: Record<string, string> = {
  morning: '上午',
  afternoon: '下午',
  evening: '晚上',
};

const QUOTA_TYPE_OPTIONS = [
  { label: '普通加号', value: 'normal' },
  { label: '特批加号', value: 'special' },
  { label: '绿色通道', value: 'green_channel' },
];

const ExtraQuotaModal: React.FC<ExtraQuotaModalProps> = ({
  open,
  onClose,
  onSuccess,
  scheduleId,
  scheduleInfo,
}) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [patients, setPatients] = useState<PatientListItem[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const quotaType = Form.useWatch('quotaType', form);

  // 重置表单
  useEffect(() => {
    if (open) {
      form.resetFields();
      setPatients([]);
    }
  }, [open, form]);

  // 搜索患者
  const handleSearchPatient = async (value: string) => {
    if (!value || value.length < 2) {
      setPatients([]);
      return;
    }

    setSearchLoading(true);
    try {
      const result = await patientApi.getList({
        keyword: value,
        pageSize: 20,
      });
      setPatients(result.data ?? []);
    } catch (error) {
      console.error('搜索患者失败', error);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      await scheduleApi.createExtraQuotaRequest({
        scheduleId,
        quantity: values.quantity,
        quotaType: values.quotaType,
        openToPublic: values.quotaType === 'special' ? false : values.openToPublic,
        patientId: values.quotaType === 'special' ? values.patientId : undefined,
        reason: values.reason,
      });

      message.success('加号申请已提交');
      form.resetFields();
      onSuccess();
      onClose();
    } catch (error: any) {
      if (error.errorFields) {
        return;
      }
      message.error(error.message || '加号申请提交失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setPatients([]);
    onClose();
  };

  return (
    <Modal
      title="申请加号"
      open={open}
      onCancel={handleCancel}
      onOk={handleSubmit}
      confirmLoading={loading}
      okText="提交申请"
      destroyOnHidden
      width={480}
    >
      {scheduleInfo && (
        <>
          <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
            {scheduleInfo.doctorName && (
              <Descriptions.Item label="医生">{scheduleInfo.doctorName}</Descriptions.Item>
            )}
            {scheduleInfo.scheduleDate && (
              <Descriptions.Item label="日期">{scheduleInfo.scheduleDate}</Descriptions.Item>
            )}
            {scheduleInfo.timeSlot && (
              <Descriptions.Item label="时段">
                {TIME_SLOT_LABELS[scheduleInfo.timeSlot] || scheduleInfo.timeSlot}
              </Descriptions.Item>
            )}
            {scheduleInfo.totalSlots !== undefined && scheduleInfo.bookedSlots !== undefined && (
              <Descriptions.Item label="号源">
                已预约 {scheduleInfo.bookedSlots}/{scheduleInfo.totalSlots}
              </Descriptions.Item>
            )}
          </Descriptions>
          <Divider style={{ margin: '0 0 16px' }} />
        </>
      )}

      <Form
        form={form}
        layout="vertical"
        initialValues={{
          quantity: 1,
          quotaType: 'normal',
          openToPublic: true,
        }}
      >
        <Form.Item
          name="quantity"
          label="加号数量"
          rules={[
            { required: true, message: '请输入加号数量' },
            { type: 'number', min: 1, max: 20, message: '数量范围 1-20' },
          ]}
        >
          <InputNumber min={1} max={20} style={{ width: '100%' }} placeholder="请输入加号数量" />
        </Form.Item>

        <Form.Item
          name="quotaType"
          label="加号类型"
          rules={[{ required: true, message: '请选择加号类型' }]}
        >
          <Radio.Group options={QUOTA_TYPE_OPTIONS} />
        </Form.Item>

        {quotaType !== 'special' && (
          <Form.Item
            name="openToPublic"
            label="对外开放"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        )}

        {quotaType === 'special' && (
          <Form.Item
            name="patientId"
            label="指定患者"
            rules={[{ required: true, message: '请选择指定患者' }]}
          >
            <Select
              showSearch
              placeholder="输入患者姓名或手机号搜索"
              filterOption={false}
              onSearch={handleSearchPatient}
              notFoundContent={searchLoading ? <Spin size="small" /> : null}
              options={patients.map(p => ({
                label: `${p.name} - ${p.phone}`,
                value: p.id,
              }))}
            />
          </Form.Item>
        )}

        <Form.Item name="reason" label="加号原因">
          <Input.TextArea rows={3} placeholder="请输入加号原因（可选）" maxLength={200} showCount />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default ExtraQuotaModal;
