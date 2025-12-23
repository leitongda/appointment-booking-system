import { Calendar, Badge, Tooltip, Spin } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { useEffect, useState, useCallback } from 'react';
import { scheduleApi } from '@hospital/api';
import type { Schedule } from '@hospital/shared';

interface ScheduleCalendarProps {
  doctorId: string;
  onDateClick?: (date: Dayjs, schedules: Schedule[]) => void;
}

interface DaySchedules {
  [date: string]: Schedule[];
}

const TIME_SLOT_LABELS: Record<string, string> = {
  morning: '上午',
  afternoon: '下午',
  evening: '晚上',
};

const ScheduleCalendar: React.FC<ScheduleCalendarProps> = ({ doctorId, onDateClick }) => {
  const [loading, setLoading] = useState(false);
  const [scheduleData, setScheduleData] = useState<DaySchedules>({});
  const [currentMonth, setCurrentMonth] = useState<Dayjs>(dayjs());

  const loadSchedules = useCallback(async (month: Dayjs) => {
    if (!doctorId) return;
    
    setLoading(true);
    try {
      const startDate = month.startOf('month').format('YYYY-MM-DD');
      const endDate = month.endOf('month').format('YYYY-MM-DD');
      
      const result = await scheduleApi.getList({
        doctorId,
        startDate,
        endDate,
        pageSize: 100,
      });
      
      // 按日期分组
      const grouped: DaySchedules = {};
      (result.data ?? []).forEach((schedule) => {
        const date = schedule.scheduleDate;
        if (!grouped[date]) {
          grouped[date] = [];
        }
        grouped[date].push(schedule);
      });
      
      setScheduleData(grouped);
    } catch (error) {
      console.error('加载排班失败', error);
    } finally {
      setLoading(false);
    }
  }, [doctorId]);

  useEffect(() => {
    loadSchedules(currentMonth);
  }, [loadSchedules, currentMonth]);

  const handlePanelChange = (date: Dayjs) => {
    setCurrentMonth(date);
  };

  const handleDateClick = (date: Dayjs) => {
    const dateStr = date.format('YYYY-MM-DD');
    const schedules = scheduleData[dateStr] || [];
    onDateClick?.(date, schedules);
  };

  const getStatusBadge = (schedule: Schedule) => {
    if (schedule.status === 0) {
      return 'default'; // 停诊
    }
    const available = schedule.totalSlots - schedule.bookedSlots;
    if (available <= 0) {
      return 'error'; // 已满
    }
    if (available <= schedule.totalSlots * 0.2) {
      return 'warning'; // 即将满
    }
    return 'success'; // 正常
  };

  const getScheduleText = (schedule: Schedule) => {
    const slotLabel = TIME_SLOT_LABELS[schedule.timeSlot] || schedule.timeSlot;
    const available = schedule.totalSlots - schedule.bookedSlots;
    
    if (schedule.status === 0) {
      return `${slotLabel} 停诊`;
    }
    return `${slotLabel} ${schedule.bookedSlots}/${schedule.totalSlots}`;
  };

  const dateCellRender = (date: Dayjs) => {
    const dateStr = date.format('YYYY-MM-DD');
    const schedules = scheduleData[dateStr] || [];
    
    if (schedules.length === 0) {
      return null;
    }

    // 按时段排序
    const sortOrder = { morning: 0, afternoon: 1, evening: 2 };
    const sortedSchedules = [...schedules].sort(
      (a, b) => (sortOrder[a.timeSlot as keyof typeof sortOrder] ?? 3) - (sortOrder[b.timeSlot as keyof typeof sortOrder] ?? 3)
    );

    return (
      <div style={{ fontSize: 12 }}>
        {sortedSchedules.map((schedule) => (
          <Tooltip
            key={schedule.id}
            title={
              <div>
                <div>{TIME_SLOT_LABELS[schedule.timeSlot] || schedule.timeSlot}</div>
                <div>时间: {schedule.startTime || '-'} - {schedule.endTime || '-'}</div>
                <div>号源: {schedule.bookedSlots}/{schedule.totalSlots}</div>
                <div>状态: {schedule.status === 1 ? '正常' : '停诊'}</div>
              </div>
            }
          >
            <div style={{ marginBottom: 2 }}>
              <Badge
                status={getStatusBadge(schedule)}
                text={getScheduleText(schedule)}
                style={{ 
                  fontSize: 11,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              />
            </div>
          </Tooltip>
        ))}
      </div>
    );
  };

  return (
    <Spin spinning={loading}>
      <Calendar
        onPanelChange={handlePanelChange}
        onSelect={handleDateClick}
        cellRender={(date, info) => {
          if (info.type === 'date') {
            return dateCellRender(date);
          }
          return null;
        }}
        style={{ 
          background: '#fff',
          borderRadius: 8,
          padding: 16,
        }}
      />
    </Spin>
  );
};

export default ScheduleCalendar;

