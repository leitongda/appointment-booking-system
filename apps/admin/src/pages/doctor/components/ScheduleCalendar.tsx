import { Calendar, Badge, Tooltip, Spin } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { useEffect, useState, useCallback } from 'react';
import { scheduleApi } from '@hospital/api';
import type { Schedule } from '@hospital/shared';
import { TIME_SLOT_LABEL } from '@hospital/shared';

interface ScheduleCalendarProps {
  doctorId: string;
  onDateClick?: (date: Dayjs, schedules: Schedule[]) => void;
}

interface DaySchedules {
  [date: string]: Schedule[];
}

// 时段标签映射 - 扩展 shared TIME_SLOT_LABEL，兼容大写格式
const TIME_SLOT_LABELS: Record<string, string> = {
  ...TIME_SLOT_LABEL,
  AM: '上午',
  PM: '下午',
  NIGHT: '晚上',
};

// 时段排序权重 - 支持两种格式
const TIME_SLOT_SORT_ORDER: Record<string, number> = {
  morning: 0,
  AM: 0,
  afternoon: 1,
  PM: 1,
  evening: 2,
  NIGHT: 2,
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
      
      const baseParams = {
        doctorId,
        startDate,
        endDate,
        pageSize: 100,
      };
      
      // 第一次请求获取总数
      const firstResult = await scheduleApi.getList({ ...baseParams, page: 1 });
      const total = firstResult.total || 0;
      let allSchedules = firstResult.data || [];

      // 如果有更多数据，继续请求
      if (total > 100) {
        const totalPages = Math.ceil(total / 100);
        const promises = [];
        for (let page = 2; page <= totalPages; page++) {
          promises.push(scheduleApi.getList({ ...baseParams, page }));
        }
        const results = await Promise.all(promises);
        for (const result of results) {
          allSchedules = allSchedules.concat(result.data || []);
        }
      }
      
      // 按日期分组
      const grouped: DaySchedules = {};
      allSchedules.forEach((schedule) => {
        const scheduleDate = schedule.scheduleDate;
        if (!grouped[scheduleDate]) {
          grouped[scheduleDate] = [];
        }
        grouped[scheduleDate].push(schedule);
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
    const slotLabel = TIME_SLOT_LABELS[schedule.timeSlot ?? ''] || schedule.timeSlot;

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

    // 按时段排序（支持两种格式）
    const sortedSchedules = [...schedules].sort(
      (a, b) => (TIME_SLOT_SORT_ORDER[a.timeSlot ?? ''] ?? 3) - (TIME_SLOT_SORT_ORDER[b.timeSlot ?? ''] ?? 3)
    );

    return (
      <div style={{ fontSize: 12 }}>
        {sortedSchedules.map((schedule) => (
          <Tooltip
            key={schedule.id}
            title={
              <div>
                <div>{TIME_SLOT_LABELS[schedule.timeSlot ?? ''] || schedule.timeSlot}</div>
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

