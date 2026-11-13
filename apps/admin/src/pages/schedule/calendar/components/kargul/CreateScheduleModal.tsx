import { useEffect } from 'react';
import { Form, Input, InputNumber, Modal, TimePicker, Select, message } from 'antd';
import dayjs from 'dayjs';
import { APPOINTMENT_TYPE_MAP } from '@hospital/shared';
import { scheduleApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { clamp, minutesToHHMM, parseHHMM } from './layout';

export interface CreateScheduleInitial {
  /** YYYY-MM-DD */
  date: string;
  /** 距 0 点分钟数 */
  start: number;
  end: number;
}

interface CreateScheduleModalProps {
  open: boolean;
  initial: CreateScheduleInitial | null;
  doctor: Doctor | null;
  onClose: () => void;
  onSuccess: () => void;
}

interface FormValues {
  startTime: dayjs.Dayjs;
  endTime: dayjs.Dayjs;
  totalSlots: number;
  appointmentType: string;
}

/**
 * 拖拽/点击空档后直接生成排班的轻量弹窗：
 * 预填拖拽出的日期与时间段，提交走 scheduleApi.create（status=1 与既有创建流程一致）。
 */
const CreateScheduleModal: React.FC<CreateScheduleModalProps> = ({ open, initial, doctor, onClose, onSuccess }) => {
  const [form] = Form.useForm<FormValues>();

  useEffect(() => {
    if (open && initial) {
      const duration = Math.max(initial.end - initial.start, 30);
      form.setFieldsValue({
        startTime: dayjs(`${initial.date}T${minutesToHHMM(initial.start)}`),
        endTime: dayjs(`${initial.date}T${minutesToHHMM(initial.end)}`),
        totalSlots: clamp(Math.round(duration / 30), 1, 100),
        appointmentType: 'normal',
      });
    }
  }, [open, initial, form]);

  const handleSubmit = async (values: FormValues) => {
    if (!doctor || !initial) return;
    const startHHMM = values.startTime?.format('HH:mm');
    const endHHMM = values.endTime?.format('HH:mm');
    if (!startHHMM || !endHHMM) {
      message.error('请选择起止时间');
      return;
    }
    const s = parseHHMM(startHHMM);
    const e = parseHHMM(endHHMM);
    if (s == null || e == null || e <= s) {
      message.error('结束时间必须晚于开始时间');
      return;
    }
    try {
      await scheduleApi.create({
        doctorId: doctor.id,
        scheduleDate: initial.date,
        totalSlots: values.totalSlots,
        appointmentType: values.appointmentType || 'normal',
        startTime: startHHMM,
        endTime: endHHMM,
        status: 1,
      });
      message.success('排班创建成功');
      onClose();
      onSuccess();
    } catch (error: any) {
      message.error(error?.message || '排班创建失败');
    }
  };

  return (
    <Modal
      title="创建排班"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      okText="创建"
      destroyOnHidden
      mask={{ closable: false }}
    >
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item label="日期">
          <Input value={initial ? `${initial.date}（${doctor?.name ?? ''}）` : ''} disabled />
        </Form.Item>
        <Form.Item
          name="startTime"
          label="开始时间"
          rules={[{ required: true, message: '请选择开始时间' }]}
        >
          <TimePicker format="HH:mm" minuteStep={15} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item
          name="endTime"
          label="结束时间"
          rules={[
            { required: true, message: '请选择结束时间' },
            ({ getFieldValue }) => ({
              validator: (_, value) => {
                const start = getFieldValue('startTime');
                if (!value || !start || value.isAfter(start)) return Promise.resolve();
                return Promise.reject(new Error('结束时间必须晚于开始时间'));
              },
            }),
          ]}
        >
          <TimePicker format="HH:mm" minuteStep={15} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item
          name="totalSlots"
          label="号源数量"
          rules={[{ required: true, message: '请输入号源数量' }]}
        >
          <InputNumber min={1} max={100} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item
          name="appointmentType"
          label="预约类型"
          rules={[{ required: true, message: '请选择预约类型' }]}
        >
          <Select
            options={Object.entries(APPOINTMENT_TYPE_MAP).map(([value, label]) => ({ value, label }))}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default CreateScheduleModal;
