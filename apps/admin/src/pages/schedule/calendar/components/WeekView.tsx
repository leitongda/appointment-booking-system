import { useMemo, useState, useCallback } from 'react';
import dayjs, { Dayjs } from 'dayjs';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  DragOverlay,
} from '@dnd-kit/core';
import type { Schedule, Appointment } from '@hospital/shared';
import TimeSlotCell from './TimeSlotCell';
import DraggableScheduleCell from './DraggableScheduleCell';
import DroppableTimeSlot from './DroppableTimeSlot';

interface WeekViewProps {
  currentDate: Dayjs;
  schedules: Schedule[];
  appointments: Appointment[];
  onAppointmentClick: (appointment: Appointment) => void;
  onCreateClick: (scheduleId: string) => void;
  isRestDay?: (dateStr: string) => boolean;
  isOverridden?: (schedule: Schedule) => boolean;
  onDragAdjust?: (params: {
    scheduleId: string;
    targetDate: string;
    targetStartTime?: string;
    targetEndTime?: string;
    targetTimeSlot?: string;
  }) => void;
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

/** 从时间槽字符串解析小时数 */
const parseTimeSlotHour = (timeSlot: string): number => {
  const [hour] = timeSlot.split(':').map(Number);
  return hour;
};

/**
 * 根据小时数推断 timeSlot 类型
 * 边界对齐 TIME_SLOT_RANGE (packages/shared/src/constants/schedule.ts):
 *   morning 08:00-12:00, afternoon 14:00-17:30, evening 18:00-21:00
 * 使用整数小时判断，hour < 18 覆盖 17:30 边界 (14:00-17:59)
 */
const inferTimeSlotType = (hour: number): string => {
  if (hour >= 8 && hour < 12) return 'morning';
  if (hour >= 14 && hour < 18) return 'afternoon';
  if (hour >= 18 && hour < 21) return 'evening';
  return 'morning'; // fallback
};

const WeekView: React.FC<WeekViewProps> = ({
  currentDate,
  schedules,
  appointments,
  onAppointmentClick,
  onCreateClick,
  isRestDay,
  isOverridden,
  onDragAdjust,
}) => {
  const [activeSchedule, setActiveSchedule] = useState<Schedule | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor)
  );

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

      // 如果没有具体时间，根据 timeSlot 判断（小写格式）
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

      // 根据 timeSlot 类型判断（小写格式）
      if (a.timeSlot === 'morning' && hour >= 8 && hour < 12) return true;
      if (a.timeSlot === 'afternoon' && hour >= 14 && hour < 18) return true;
      if (a.timeSlot === 'evening' && hour >= 18 && hour < 21) return true;

      return false;
    });
  };

  const handleDragStart = useCallback((event: DragStartEvent) => {
    const { active } = event;
    const scheduleId = String(active.id).replace('draggable-', '');
    const schedule = schedules.find(s => s.id === scheduleId);
    if (schedule) {
      setActiveSchedule(schedule);
    }
  }, [schedules]);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;
    setActiveSchedule(null);

    if (!over) return;

    const scheduleId = String(active.id).replace('draggable-', '');
    const overId = String(over.id);

    // 解析 droppable id: droppable-{date}-{timeSlot}
    const overParts = overId.replace('droppable-', '').split('-');
    if (overParts.length < 3) return;

    // 日期部分: YYYY-MM-DD (3段), 时间部分: HH:MM
    const targetDate = `${overParts[0]}-${overParts[1]}-${overParts[2]}`;
    const targetTimeSlot = overParts.length > 3 ? overParts.slice(3).join('-') : undefined;

    // 检查是否拖到了同一个位置
    const sourceSchedule = schedules.find(s => s.id === scheduleId);
    if (!sourceSchedule) return;

    const sourceDate = sourceSchedule.scheduleDate;
    const sourceTimeSlot = sourceSchedule.startTime || sourceSchedule.timeSlot || '';

    // 目标时间槽解析
    let targetStartTime: string | undefined;
    let targetEndTime: string | undefined;
    let resolvedTimeSlot: string | undefined;

    if (targetTimeSlot) {
      // 从时间槽推断时间段
      const hour = parseTimeSlotHour(targetTimeSlot);
      resolvedTimeSlot = inferTimeSlotType(hour);

      // 保持原有时间段长度，计算新的起止时间
      if (sourceSchedule.startTime && sourceSchedule.endTime) {
        const [startH, startM] = sourceSchedule.startTime.split(':').map(Number);
        const [endH, endM] = sourceSchedule.endTime.split(':').map(Number);
        const durationMinutes = (endH * 60 + endM) - (startH * 60 + startM);

        targetStartTime = targetTimeSlot;
        const targetStartMinutes = hour * 60 + parseInt(targetTimeSlot.split(':')[1], 10);
        const targetEndMinutes = targetStartMinutes + durationMinutes;
        const targetEndH = Math.floor(targetEndMinutes / 60);
        const targetEndM = targetEndMinutes % 60;
        targetEndTime = `${targetEndH.toString().padStart(2, '0')}:${targetEndM.toString().padStart(2, '0')}`;
      }
    }

    // 如果日期和时间段都相同，忽略
    if (sourceDate === targetDate && sourceTimeSlot === (targetStartTime || resolvedTimeSlot || '')) {
      return;
    }

    onDragAdjust?.({
      scheduleId,
      targetDate,
      targetStartTime,
      targetEndTime,
      targetTimeSlot: resolvedTimeSlot,
    });
  }, [schedules, onDragAdjust]);

  const today = dayjs().format('YYYY-MM-DD');

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="week-view">
        <div className="week-grid" role="grid" aria-label="排班周视图">
          {/* 表头 */}
          <div className="week-header" role="row">
            <div className="header-cell time-column" role="columnheader">时间</div>
            {weekDays.map((day, index) => {
              const dateStr = day.format('YYYY-MM-DD');
              const isToday = dateStr === today;
              const isWeekend = index === 0 || index === 6;
              const isRest = isRestDay?.(dateStr) ?? false;
              return (
                <div
                  key={dateStr}
                  className={`header-cell ${isToday ? 'today' : ''} ${isWeekend ? 'weekend' : ''} ${isRest ? 'rest-day' : ''}`}
                  role="columnheader"
                  aria-label={`${day.format('YYYY年MM月DD日')} 周${WEEKDAYS[day.day()]}${isToday ? ' 今天' : ''}${isRest ? ' 休息日' : ''}`}
                >
                  <div className="header-date">{day.format('MM/DD')}</div>
                  <div className="header-weekday">周{WEEKDAYS[day.day()]}</div>
                  {isRest && <div className="rest-day-badge">休息日</div>}
                </div>
              );
            })}
          </div>

          {/* 时间行 */}
          {TIME_SLOTS.map((timeSlot) => (
            <div key={timeSlot} className="time-row" role="row">
              <div className="time-cell" role="rowheader">{timeSlot}</div>
              {weekDays.map((day, index) => {
                const dateStr = day.format('YYYY-MM-DD');
                const isToday = dateStr === today;
                const isWeekend = index === 0 || index === 6;
                const schedule = getScheduleForSlot(day, timeSlot);
                const slotAppointments = getAppointmentsForSlot(day, timeSlot);
                const overridden = schedule ? isOverridden?.(schedule) : false;

                return (
                  <div
                    key={`${dateStr}-${timeSlot}`}
                    className={`slot-cell ${isToday ? 'today' : ''} ${isWeekend ? 'weekend' : ''}`}
                    aria-label={`${day.format('MM月DD日')} ${timeSlot} ${schedule ? '有排班' : '无排班'}`}
                    role="gridcell"
                  >
                    <DroppableTimeSlot dateStr={dateStr} timeSlot={timeSlot}>
                      {schedule ? (
                        <DraggableScheduleCell
                          schedule={schedule}
                          appointments={slotAppointments}
                          onAppointmentClick={onAppointmentClick}
                          onCreateClick={onCreateClick}
                          isOverridden={overridden}
                        />
                      ) : (
                        <TimeSlotCell
                          schedule={undefined}
                          appointments={slotAppointments}
                          onAppointmentClick={onAppointmentClick}
                          onCreateClick={onCreateClick}
                          isOverridden={false}
                        />
                      )}
                    </DroppableTimeSlot>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* 拖拽预览覆盖层 */}
      <DragOverlay>
        {activeSchedule ? (
          <div className="drag-overlay-card">
            <div className="drag-overlay-doctor">{activeSchedule.doctorName || '排班'}</div>
            <div className="drag-overlay-time">
              {activeSchedule.startTime && activeSchedule.endTime
                ? `${activeSchedule.startTime} - ${activeSchedule.endTime}`
                : activeSchedule.timeSlot || '-'}
            </div>
            <div className="drag-overlay-slots">
              {activeSchedule.bookedSlots}/{activeSchedule.totalSlots}
            </div>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
};

export default WeekView;
