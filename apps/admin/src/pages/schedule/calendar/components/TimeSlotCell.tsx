import { Tooltip } from 'antd';
import type { Schedule, Appointment } from '@hospital/shared';

export type SlotStatus = 'available' | 'booked' | 'full' | 'suspended' | 'overridden' | 'empty';

interface TimeSlotCellProps {
  schedule?: Schedule;
  appointments: Appointment[];
  onAppointmentClick?: (appointment: Appointment) => void;
  onCreateClick?: (scheduleId: string) => void;
  isOverridden?: boolean;
}

const TimeSlotCell: React.FC<TimeSlotCellProps> = ({
  schedule,
  appointments,
  onAppointmentClick,
  onCreateClick,
  isOverridden,
}) => {
  // 没有排班
  if (!schedule) {
    return <div className="time-slot-cell empty" />;
  }

  // 计算状态
  const getStatus = (): SlotStatus => {
    if (isOverridden) {
      return 'overridden';
    }
    if (schedule.status === 0) {
      return 'suspended';
    }
    const available = schedule.totalSlots - schedule.bookedSlots;
    if (available <= 0) {
      return 'full';
    }
    if (schedule.bookedSlots > 0) {
      return 'booked';
    }
    return 'available';
  };

  const status = getStatus();
  const available = schedule.totalSlots - schedule.bookedSlots;

  const handleClick = () => {
    if (status === 'suspended' || status === 'full' || status === 'overridden') {
      return;
    }
    // 有剩余号源，可以创建预约
    if (available > 0) {
      onCreateClick?.(schedule.id);
    } else if (appointments.length > 0) {
      // 已满但有预约记录，点击显示预约详情
      onAppointmentClick?.(appointments[0]);
    }
  };

  const getTooltipContent = () => {
    const timeRange = schedule.startTime && schedule.endTime
      ? `${schedule.startTime} - ${schedule.endTime}`
      : '-';

    return (
      <div>
        <div>时间: {timeRange}</div>
        <div>号源: {schedule.bookedSlots}/{schedule.totalSlots}</div>
        <div>剩余: {available}</div>
        {status === 'suspended' && <div style={{ color: '#ff4d4f' }}>已停诊</div>}
        {status === 'overridden' && <div style={{ color: '#999' }}>已被自定义排班覆盖</div>}
        {appointments.length > 0 && (
          <div style={{ marginTop: 4 }}>
            已预约患者: {appointments.length}人
          </div>
        )}
      </div>
    );
  };

  const getAriaLabel = () => {
    if (!schedule) return '无排班';
    const timeRange = schedule.startTime && schedule.endTime
      ? `${schedule.startTime}至${schedule.endTime}`
      : '';
    const capacity = `${schedule.bookedSlots}人预约，共${schedule.totalSlots}个号源，剩余${available}个`;
    const statusText = status === 'suspended' ? '已停诊' : status === 'overridden' ? '已被覆盖' : status === 'full' ? '已满' : status === 'booked' ? '已预约' : '可预约';
    return `${timeRange} ${capacity} ${statusText}`;
  };

  return (
    <Tooltip title={getTooltipContent()} placement="top">
      <div
        className={`time-slot-cell ${status}`}
        onClick={handleClick}
        aria-label={getAriaLabel()}
        role="button"
        aria-disabled={status === 'suspended' || status === 'full' || status === 'overridden'}
      >
        <div className="slot-content">
          <span className="slot-indicator" aria-hidden="true" />
          <span className="slot-count">
            {status === 'suspended' ? '停' : status === 'overridden' ? '覆' : `${schedule.bookedSlots}/${schedule.totalSlots}`}
          </span>
        </div>
      </div>
    </Tooltip>
  );
};

export default TimeSlotCell;

