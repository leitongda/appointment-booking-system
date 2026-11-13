import { TIME_SLOT_LABEL, TIME_SLOT_RANGE } from '@hospital/shared';
import type { Schedule } from '@hospital/shared';
import type { CSSProperties } from 'react';
import { parseHHMM, type CalEvent } from './layout';

/** 参考设计的 6 组事件配色（bg/fg 成对），变量见 styles/kargul.less */
export type KEventColor = 'blue' | 'cyan' | 'green' | 'orange' | 'pink' | 'purple';

/** 事件表面配色：使用设计的成对 bg/fg tokens */
export const eventStyle = (color: KEventColor): CSSProperties => ({
  background: `var(--kg-event-${color}-bg)`,
  color: `var(--kg-event-${color}-fg)`,
});

export const K_EVENT_FG = (color: KEventColor) => `var(--kg-event-${color}-fg)`;

/**
 * 排班 → 事件配色（沿用设计 6 色板）：
 * 停诊 pink / 被覆盖·已撤回 cyan / 待发布 orange / 已满 blue / 正常发布 green
 */
export function scheduleColor(s: Schedule): KEventColor {
  if (s.status === 0 || s.effectiveStatus === 'suspended') return 'pink';
  if (s.effectiveStatus === 'overridden') return 'cyan';
  if (s.scheduleStatus === 'withdrawn' || s.publishStatus === 'withdrawn') return 'cyan';
  if (s.scheduleStatus === 'draft' || s.publishStatus === 'draft') return 'orange';
  if (s.totalSlots > 0 && s.bookedSlots >= s.totalSlots) return 'blue';
  return 'green';
}

export const SCHEDULE_BADGE: Record<KEventColor, { text: string; tone: 'success' | 'warning' | 'danger' | 'neutral' }> = {
  green: { text: '已发布', tone: 'success' },
  orange: { text: '待发布', tone: 'warning' },
  blue: { text: '已满', tone: 'neutral' },
  cyan: { text: '已撤回', tone: 'neutral' },
  pink: { text: '停诊', tone: 'danger' },
  purple: { text: '休息日', tone: 'neutral' },
};

/** timeSlot（morning/afternoon/evening）→ 默认分钟区间 */
export const timeSlotRange = (slot?: string): { start: number; end: number } | null => {
  const range = slot ? TIME_SLOT_RANGE[slot] : undefined;
  if (!range) return null;
  const start = parseHHMM(range.start);
  const end = parseHHMM(range.end);
  if (start == null || end == null) return null;
  return { start, end };
};

/** 起始分钟 → 所属时段（对齐 TIME_SLOT_RANGE 边界：上午 08-12 / 下午 14-17:30 / 晚间 18-21） */
export const inferTimeSlot = (minutes: number): string | undefined => {
  const hour = Math.floor(minutes / 60);
  if (hour >= 8 && hour < 12) return 'morning';
  if (hour >= 14 && hour < 18) return 'afternoon';
  if (hour >= 18 && hour < 21) return 'evening';
  return undefined;
};

/**
 * 排班 → 日历事件。
 * 休息日返回 null（由调用方聚合为全天泳道的紫色 chip）；
 * 无具体起止时间时回退到时段默认区间。
 */
export function scheduleToEvent(s: Schedule): CalEvent | null {
  if (s.isRestDay) return null;

  let start = parseHHMM(s.startTime);
  let end = parseHHMM(s.endTime);
  if (start == null || end == null || end <= start) {
    const range = timeSlotRange(s.timeSlot);
    if (!range) return null;
    start = range.start;
    end = range.end;
  }

  const slotLabel = s.timeSlot ? TIME_SLOT_LABEL[s.timeSlot] || '' : '';
  const title = slotLabel || (s.startTime ? '门诊' : '排班');
  const note = `已约 ${s.bookedSlots}/${s.totalSlots}`;
  const locked = s.status === 0 || s.effectiveStatus === 'overridden';

  return {
    id: s.id,
    date: s.scheduleDate,
    start,
    end,
    color: scheduleColor(s),
    title,
    note,
    locked,
    schedule: s,
  };
}
