import { Tooltip } from 'antd';
import type { Schedule, Appointment } from '@hospital/shared';

export type SlotStatus = 'available' | 'booked' | 'full' | 'suspended' | 'empty';

interface TimeSlotCellProps {
  schedule?: Schedule;
  appointments: Appointment[];
  onAppointmentClick?: (appointment: Appointment) => void;
  onCreateClick?: (scheduleId: string) => void;
}

const TimeSlotCell: React.FC<TimeSlotCellProps> = ({
  schedule,
  appointments,
  onAppointmentClick,
  onCreateClick,
}) => {
  // 没有排班
  if (!schedule) {
    return <div className="time-slot-cell empty" />;
  }

  // 计算状态
  const getStatus = (): SlotStatus => {
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
    if (status === 'suspended' || status === 'full') {
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
        {appointments.length > 0 && (
          <div style={{ marginTop: 4 }}>
            已预约患者: {appointments.length}人
          </div>
        )}
      </div>
    );
  };

  return (
    <Tooltip title={getTooltipContent()} placement="top">
      <div className={`time-slot-cell ${status}`} onClick={handleClick}>
        <div className="slot-content">
          <span className="slot-indicator" />
          <span className="slot-count">
            {status === 'suspended' ? '停' : `${schedule.bookedSlots}/${schedule.totalSlots}`}
          </span>
        </div>
      </div>
    </Tooltip>
  );
};

export default TimeSlotCell;

