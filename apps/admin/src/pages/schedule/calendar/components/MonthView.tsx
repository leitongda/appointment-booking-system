import { Calendar, Tag } from 'antd';
import type { Dayjs } from 'dayjs';
import type { Schedule, Appointment } from '@hospital/shared';
import { TIME_SLOT_LABEL } from '@hospital/shared';

interface MonthViewProps {
  currentDate: Dayjs;
  schedules: Schedule[];
  appointments: Appointment[];
  onDateClick: (date: Dayjs) => void;
  isRestDay?: (dateStr: string) => boolean;
  isOverridden?: (schedule: Schedule) => boolean;
}


// 时段排序权重
const TIME_SLOT_SORT_ORDER: Record<string, number> = {
  morning: 0,
  afternoon: 1,
  evening: 2,
};

const MonthView: React.FC<MonthViewProps> = ({
  currentDate,
  schedules,
  appointments,
  onDateClick,
  isRestDay,
  isOverridden,
}) => {
  // 获取某天的排班
  const getSchedulesByDate = (date: Dayjs): Schedule[] => {
    const dateStr = date.format('YYYY-MM-DD');
    return schedules.filter(s => s.scheduleDate === dateStr);
  };

  // 获取某天的预约数量
  const _getAppointmentCountByDate = (date: Dayjs): number => {
    const dateStr = date.format('YYYY-MM-DD');
    return appointments.filter(a => a.scheduleDate === dateStr).length;
  };

  // 计算某天的统计数据
  const getDateStats = (date: Dayjs) => {
    const daySchedules = getSchedulesByDate(date);
    const totalSlots = daySchedules.reduce((sum, s) => sum + s.totalSlots, 0);
    const bookedSlots = daySchedules.reduce((sum, s) => sum + s.bookedSlots, 0);
    const availableSlots = totalSlots - bookedSlots;
    const hasSuspended = daySchedules.some(s => s.status === 0);
    
    return {
      totalSlots,
      bookedSlots,
      availableSlots,
      hasSuspended,
      schedules: daySchedules,
    };
  };

  const dateCellRender = (date: Dayjs) => {
    const dateStr = date.format('YYYY-MM-DD');
    const stats = getDateStats(date);
    const isRest = isRestDay?.(dateStr) ?? false;
    
    // 如果是休息日，显示休息日标记
    if (isRest) {
      return (
        <div className="month-cell-content rest-day" aria-label={`${dateStr} 休息日 ${stats.schedules.length}个排班`}>
          <Tag color="orange" className="rest-day-tag">休息日</Tag>
          {stats.schedules.length > 0 && (
            <div className="cell-stats muted">
              <span className="stat-item">
                <span>{stats.schedules.length}个排班</span>
              </span>
            </div>
          )}
        </div>
      );
    }
    
    if (stats.schedules.length === 0) {
      return null;
    }

    // 按时段排序（支持两种格式）
    const sortedSchedules = [...stats.schedules].sort(
      (a, b) => (TIME_SLOT_SORT_ORDER[a.timeSlot ?? ''] ?? 3) - 
                (TIME_SLOT_SORT_ORDER[b.timeSlot ?? ''] ?? 3)
    );

    const ariaLabel = `${dateStr} ${stats.availableSlots > 0 ? `剩余号源${stats.availableSlots}个` : ''} ${stats.bookedSlots > 0 ? `已预约${stats.bookedSlots}个` : ''} ${stats.hasSuspended ? '有停诊排班' : ''}`;

    return (
      <div className="month-cell-content" aria-label={ariaLabel}>
        <div className="cell-stats">
          {stats.availableSlots > 0 && (
            <span className="stat-item">
              <span className="stat-dot available" />
              <span>{stats.availableSlots}</span>
            </span>
          )}
          {stats.bookedSlots > 0 && (
            <span className="stat-item">
              <span className="stat-dot booked" />
              <span>{stats.bookedSlots}</span>
            </span>
          )}
        </div>
        <div className="cell-slots">
          {sortedSchedules.slice(0, 3).map(s => {
            const available = s.totalSlots - s.bookedSlots;
            const overridden = isOverridden?.(s) ?? false;
            let color = 'success';
            if (overridden || s.status === 0) color = 'default';
            else if (available <= 0) color = 'error';
            else if (available <= s.totalSlots * 0.2) color = 'warning';

            return (
              <Tag
                key={s.id}
                color={color}
                className={`slot-tag${overridden ? ' overridden' : ''}`}
                title={overridden ? '已被自定义排班覆盖' : undefined}
              >
                {overridden ? '覆盖' : (TIME_SLOT_LABEL[s.timeSlot ?? ''] || s.timeSlot)}
              </Tag>
            );
          })}
        </div>
      </div>
    );
  };

  const handleSelect = (date: Dayjs) => {
    onDateClick(date);
  };

  return (
    <div className="month-view">
      <Calendar
        value={currentDate}
        onSelect={handleSelect}
        cellRender={(date, info) => {
          if (info.type === 'date') {
            return dateCellRender(date);
          }
          return null;
        }}
      />
    </div>
  );
};

export default MonthView;

