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
  0: { text: '待支付', color: 'warning' },
  1: { text: '已预约', color: 'processing' },
  2: { text: '已签到', color: 'cyan' },
  3: { text: '历史候诊', color: 'default' },
  4: { text: '就诊中', color: 'processing' },
  5: { text: '已完成', color: 'success' },
  6: { text: '已取消', color: 'default' },
  7: { text: '已过期', color: 'default' },
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
    history.push(`/medical-services/appointment/${appointment.id}`);
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
      <Descriptions column={1} bordered size="small" items={[
        { key: '0', label: '患者姓名', children: <span data-rrweb-mask-text>{maskName(appointment.patientName || '')}</span> },
        { key: '1', label: '手机号', children: <span data-rrweb-mask-text>{maskPhone(appointment.patientPhone || '')}</span> },
        { key: '2', label: '预约日期', children: appointment.scheduleDate || '-' },
        { key: '3', label: '预约时段', children: (
          appointment.timeSlot === 'morning' ? '上午' :
           appointment.timeSlot === 'afternoon' ? '下午' :
           appointment.timeSlot === 'evening' ? '晚上' : '-'
        ) },
        { key: '4', label: '状态', children: <Tag color={statusInfo.color}>{statusInfo.text}</Tag> },
        { key: '5', label: '医生', children: appointment.doctorName || '-' },
        { key: '6', label: '科室', children: appointment.departmentName || '-' },
        ...(appointment.queueNumber ? [{ key: '7', label: '排队号', children: appointment.queueNumber }] : []),
        { key: '8', label: '创建时间', children: appointment.createdAt
          ? dayjs(appointment.createdAt).format('YYYY-MM-DD HH:mm')
          : '-' },
      ]} />
    </Modal>
  );
};

export default AppointmentDetailModal;
