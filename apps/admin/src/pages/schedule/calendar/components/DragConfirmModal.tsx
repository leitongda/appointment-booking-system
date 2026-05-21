import { Modal, Descriptions, Alert, Space, Typography } from 'antd';
import type { Schedule } from '@hospital/shared';

const { Text } = Typography;

export interface DragConflictItem {
  type: string;
  severity: string;
  message: string;
  details: Record<string, unknown>;
}

interface DragConfirmModalProps {
  open: boolean;
  schedule: Schedule | null;
  targetDate: string;
  targetStartTime?: string;
  targetEndTime?: string;
  targetTimeSlot?: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
  conflicts?: DragConflictItem[];
}

const TIME_SLOT_LABEL: Record<string, string> = {
  morning: '上午',
  afternoon: '下午',
  evening: '晚上',
};

const formatTimeRange = (schedule: Schedule): string => {
  if (schedule.startTime && schedule.endTime) {
    return `${schedule.startTime} - ${schedule.endTime}`;
  }
  if (schedule.timeSlot) {
    return TIME_SLOT_LABEL[schedule.timeSlot] || schedule.timeSlot;
  }
  return '-';
};

const DragConfirmModal: React.FC<DragConfirmModalProps> = ({
  open,
  schedule,
  targetDate,
  targetStartTime,
  targetEndTime,
  targetTimeSlot,
  onConfirm,
  onCancel,
  loading,
  conflicts,
}) => {
  if (!schedule) return null;

  const targetTimeDisplay = targetStartTime && targetEndTime
    ? `${targetStartTime} - ${targetEndTime}`
    : targetTimeSlot
      ? TIME_SLOT_LABEL[targetTimeSlot] || targetTimeSlot
      : '-';

  const hasBlocking = conflicts?.some(c => c.severity === 'blocking' || c.severity === 'error');

  return (
    <Modal
      title="确认调整排班"
      open={open}
      onOk={onConfirm}
      onCancel={onCancel}
      confirmLoading={loading}
      okButtonProps={{ disabled: hasBlocking }}
      okText="确认调整"
      cancelText="取消"
      destroyOnClose
    >
      <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
        <Descriptions.Item label="医生">
          {schedule.doctorName || schedule.doctorId}
        </Descriptions.Item>
        <Descriptions.Item label="原日期">
          {schedule.scheduleDate}
        </Descriptions.Item>
        <Descriptions.Item label="原时间">
          {formatTimeRange(schedule)}
        </Descriptions.Item>
        <Descriptions.Item label="号源">
          {schedule.bookedSlots}/{schedule.totalSlots}
        </Descriptions.Item>
      </Descriptions>

      <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
        <Descriptions.Item label="目标日期">
          <Text strong>{targetDate}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="目标时间">
          <Text strong>{targetTimeDisplay}</Text>
        </Descriptions.Item>
      </Descriptions>

      {conflicts && conflicts.length > 0 && (
        <Space direction="vertical" style={{ width: '100%' }}>
          {conflicts.map((conflict, index) => (
            <Alert
              key={index}
              type={conflict.severity === 'blocking' || conflict.severity === 'error' ? 'error' : 'warning'}
              message={conflict.message}
              showIcon
            />
          ))}
        </Space>
      )}
    </Modal>
  );
};

export default DragConfirmModal;
