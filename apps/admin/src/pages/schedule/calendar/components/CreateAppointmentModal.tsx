import { Modal, Form, Select, App, Spin } from 'antd';
import { useState, useEffect } from 'react';
import { scheduleApi, appointmentApi, patientApi } from '@hospital/api';
import type { PatientListItem } from '@hospital/api';
import type { Schedule } from '@hospital/shared';
import { TIME_SLOT_LABEL } from '@hospital/shared';
import { ScheduleMessages } from '../../utils/message';
import { COLOR_SUCCESS } from '@/themes/scheduleColors';

interface CreateAppointmentModalProps {
  open: boolean;
  onClose: () => void;
  scheduleId: string | null;
  onSuccess: () => void;
}


const CreateAppointmentModal: React.FC<CreateAppointmentModalProps> = ({
  open,
  onClose,
  scheduleId,
  onSuccess,
}) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [patients, setPatients] = useState<PatientListItem[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const loadScheduleDetail = async () => {
    if (!scheduleId) return;
    try {
      const data = await scheduleApi.getDetail(scheduleId);
      setSchedule(data);
    } catch (error) {
      console.error('加载排班详情失败', error);
    }
  };

  useEffect(() => {
    if (open && scheduleId) {
      loadScheduleDetail();
    }
  }, [open, scheduleId]);

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
    if (!scheduleId) return;
    
    try {
      const values = await form.validateFields();
      setLoading(true);
      
      await appointmentApi.create({
        scheduleId,
        patientId: values.patientId,
      });

      message.success(ScheduleMessages.appointmentCreatedSuccess);
      form.resetFields();
      onSuccess();
      onClose();
    } catch (error: any) {
      if (error.errorFields) {
        // 表单验证错误
        return;
      }
      message.error(error.message || ScheduleMessages.appointmentCreateFailed);
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
      title="创建预约"
      open={open}
      onCancel={handleCancel}
      onOk={handleSubmit}
      confirmLoading={loading}
      okText="确认预约"
      className="create-appointment-modal"
      destroyOnHidden
    >
      {schedule && (
        <div className="schedule-info">
          <div className="info-item">
            <span className="info-label">日期：</span>
            <span>{schedule.scheduleDate}</span>
          </div>
          <div className="info-item">
            <span className="info-label">时段：</span>
            <span>{TIME_SLOT_LABEL[schedule.timeSlot ?? ''] || schedule.timeSlot}</span>
          </div>
          <div className="info-item">
            <span className="info-label">时间：</span>
            <span>{schedule.startTime} - {schedule.endTime}</span>
          </div>
          <div className="info-item">
            <span className="info-label">医生：</span>
            <span>{schedule.doctorName || '-'}</span>
          </div>
          <div className="info-item">
            <span className="info-label">剩余号源：</span>
            <span style={{ color: COLOR_SUCCESS }}>
              {schedule.totalSlots - schedule.bookedSlots}
            </span>
          </div>
        </div>
      )}

      <Form form={form} layout="vertical">
        <Form.Item
          name="patientId"
          label="选择患者"
          rules={[{ required: true, message: '请选择患者' }]}
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
      </Form>
    </Modal>
  );
};

export default CreateAppointmentModal;

