import { Modal, Descriptions, Tag, Button, Space } from 'antd';
import { history } from '@umijs/max';
import dayjs from 'dayjs';
import type { Appointment } from '@hospital/shared';

interface AppointmentDetailModalProps {
  open: boolean;
  onClose: () => void;
  appointment: Appointment | null;
}

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '待就诊', color: 'processing' },
  1: { text: '已签到', color: 'warning' },
  2: { text: '就诊中', color: 'processing' },
  3: { text: '已完成', color: 'success' },
  4: { text: '已取消', color: 'default' },
  5: { text: '爽约', color: 'error' },
};

const AppointmentDetailModal: React.FC<AppointmentDetailModalProps> = ({
  open,
  onClose,
  appointment,
}) => {
  if (!appointment) return null;

  const statusInfo = STATUS_MAP[appointment.status] || { text: '-', color: 'default' };

  // 脱敏姓名
  const maskName = (name: string): string => {
    if (!name) return '-';
    if (name.length <= 1) return name;
    if (name.length === 2) return name[0] + '*';
    return name[0] + '*'.repeat(name.length - 2) + name[name.length - 1];
  };

  // 脱敏手机号
  const maskPhone = (phone: string): string => {
    if (!phone) return '-';
    if (phone.length <= 7) return phone;
    return phone.substring(0, 3) + '****' + phone.substring(phone.length - 4);
  };

  const handleViewDetail = () => {
    history.push(`/appointment/${appointment.id}`);
    onClose();
  };

  return (
    <Modal
      title="预约详情"
      open={open}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={onClose}>关闭</Button>
          <Button type="primary" onClick={handleViewDetail}>
            查看完整详情
          </Button>
        </Space>
      }
      className="appointment-detail-modal"
    >
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="患者姓名">
          {maskName(appointment.patientName || '')}
        </Descriptions.Item>
        <Descriptions.Item label="手机号">
          {maskPhone(appointment.patientPhone || '')}
        </Descriptions.Item>
        <Descriptions.Item label="预约日期">
          {appointment.scheduleDate || '-'}
        </Descriptions.Item>
        <Descriptions.Item label="预约时段">
          {appointment.timeSlot === 'morning' ? '上午' : 
           appointment.timeSlot === 'afternoon' ? '下午' : 
           appointment.timeSlot === 'evening' ? '晚上' : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="医生">
          {appointment.doctorName || '-'}
        </Descriptions.Item>
        <Descriptions.Item label="科室">
          {appointment.departmentName || '-'}
        </Descriptions.Item>
        {appointment.queueNumber && (
          <Descriptions.Item label="排队号">
            {appointment.queueNumber}
          </Descriptions.Item>
        )}
        <Descriptions.Item label="创建时间">
          {appointment.createdAt 
            ? dayjs(appointment.createdAt).format('YYYY-MM-DD HH:mm')
            : '-'}
        </Descriptions.Item>
      </Descriptions>
    </Modal>
  );
};

export default AppointmentDetailModal;

