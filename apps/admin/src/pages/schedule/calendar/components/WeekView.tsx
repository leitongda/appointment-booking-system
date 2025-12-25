import { useMemo } from 'react';
import dayjs, { Dayjs } from 'dayjs';
import type { Schedule, Appointment } from '@hospital/shared';
import TimeSlotCell from './TimeSlotCell';

interface WeekViewProps {
  currentDate: Dayjs;
  schedules: Schedule[];
  appointments: Appointment[];
  onAppointmentClick: (appointment: Appointment) => void;
  onCreateClick: (scheduleId: string) => void;
}

// 生成30分钟时间轴 (08:00 - 21:00)
const generateTimeSlots = (): string[] => {
  const slots: string[] = [];
  for (let hour = 8; hour <= 20; hour++) {
    slots.push(`${hour.toString().padStart(2, '0')}:00`);
    slots.push(`${hour.toString().padStart(2, '0')}:30`);
  }
  slots.push('21:00');
  return slots;
};

const TIME_SLOTS = generateTimeSlots();
const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];

const WeekView: React.FC<WeekViewProps> = ({
  currentDate,
  schedules,
  appointments,
  onAppointmentClick,
  onCreateClick,
}) => {
  // 计算本周的7天
  const weekDays = useMemo(() => {
    const startOfWeek = currentDate.startOf('week');
    return Array.from({ length: 7 }, (_, i) => startOfWeek.add(i, 'day'));
  }, [currentDate]);

  // 按日期和时间获取排班
  const getScheduleForSlot = (date: Dayjs, timeSlot: string): Schedule | undefined => {
    const dateStr = date.format('YYYY-MM-DD');
    const [hour, minute] = timeSlot.split(':').map(Number);
    const slotMinutes = hour * 60 + minute;

    return schedules.find(s => {
      if (s.scheduleDate !== dateStr) return false;
      
      // 根据 startTime 和 endTime 判断是否在范围内
      if (s.startTime && s.endTime) {
        const [startH, startM] = s.startTime.split(':').map(Number);
        const [endH, endM] = s.endTime.split(':').map(Number);
        const startMinutes = startH * 60 + startM;
        const endMinutes = endH * 60 + endM;
        return slotMinutes >= startMinutes && slotMinutes < endMinutes;
      }
      
      // 如果没有具体时间，根据 timeSlot 判断
      if (s.timeSlot === 'morning' && hour >= 8 && hour < 12) return true;
      if (s.timeSlot === 'afternoon' && hour >= 14 && hour < 18) return true;
      if (s.timeSlot === 'evening' && hour >= 18 && hour < 21) return true;
      
      return false;
    });
  };

  // 获取某个时间段的预约
  const getAppointmentsForSlot = (date: Dayjs, timeSlotTime: string): Appointment[] => {
    const dateStr = date.format('YYYY-MM-DD');
    const [hour] = timeSlotTime.split(':').map(Number);
    
    return appointments.filter(a => {
      if (a.scheduleDate !== dateStr) return false;
      
      // 根据 timeSlot 类型判断
      if (a.timeSlot === 'morning' && hour >= 8 && hour < 12) return true;
      if (a.timeSlot === 'afternoon' && hour >= 14 && hour < 18) return true;
      if (a.timeSlot === 'evening' && hour >= 18 && hour < 21) return true;
      
      return false;
    });
  };

  const today = dayjs().format('YYYY-MM-DD');

  return (
    <div className="week-view">
      <div className="week-grid">
        {/* 表头 */}
        <div className="week-header">
          <div className="header-cell time-column">时间</div>
          {weekDays.map((day, index) => {
            const isToday = day.format('YYYY-MM-DD') === today;
            const isWeekend = index === 0 || index === 6;
            return (
              <div
                key={day.format('YYYY-MM-DD')}
                className={`header-cell ${isToday ? 'today' : ''} ${isWeekend ? 'weekend' : ''}`}
              >
                <div className="header-date">{day.format('MM/DD')}</div>
                <div className="header-weekday">周{WEEKDAYS[day.day()]}</div>
              </div>
            );
          })}
        </div>

        {/* 时间行 */}
        {TIME_SLOTS.map((timeSlot) => (
          <div key={timeSlot} className="time-row">
            <div className="time-cell">{timeSlot}</div>
            {weekDays.map((day, index) => {
              const isToday = day.format('YYYY-MM-DD') === today;
              const isWeekend = index === 0 || index === 6;
              const schedule = getScheduleForSlot(day, timeSlot);
              const slotAppointments = getAppointmentsForSlot(day, timeSlot);

              return (
                <div
                  key={`${day.format('YYYY-MM-DD')}-${timeSlot}`}
                  className={`slot-cell ${isToday ? 'today' : ''} ${isWeekend ? 'weekend' : ''}`}
                >
                  <TimeSlotCell
                    schedule={schedule}
                    appointments={slotAppointments}
                    onAppointmentClick={onAppointmentClick}
                    onCreateClick={onCreateClick}
                  />
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

export default WeekView;

