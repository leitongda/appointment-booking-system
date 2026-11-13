import { useMemo } from 'react';
import type { Dayjs } from 'dayjs';
import { WEEKDAYS_CN, type CalEvent } from './layout';
import { eventStyle, type KEventColor } from './colors';
import type { AllDayChip } from './TimeGrid';

const MAX_CHIPS = 3;

interface MonthViewProps {
  /** 聚焦月份内的任一日期 */
  date: Dayjs;
  events: CalEvent[];
  /** 休息日等全天项 */
  allDayChips: AllDayChip[];
  /** YYYY-MM-DD */
  selectedDate: string;
  today: string;
  onSelectDate: (d: Dayjs) => void;
  onEventClick?: (eventId: string, el: HTMLElement) => void;
  onChipClick?: (chip: AllDayChip, el: HTMLElement) => void;
  /** 双击空白格创建排班（需 schedule:create 权限，由父级把关） */
  onCreate?: (p: { date: string; start: number; end: number }) => void;
  /** 「+N 更多」跳转日视图 */
  onOpenDay?: (d: Dayjs) => void;
}

const fmtHHMM = (m: number) => `${Math.floor(m / 60).toString().padStart(2, '0')}:${(m % 60).toString().padStart(2, '0')}`;

/**
 * 月视图 —— 1:1 复刻 kargulstudio/calender-app-design 的 MonthView：
 * 40px 星期表头、6 行网格、日期徽标（今天紫字/选中紫底）、
 * 每天最多 3 个 22px 彩色 chip（休息日排最前），其余折叠为「+N 更多」。
 */
export function MonthView({
  date,
  events,
  allDayChips,
  selectedDate,
  today,
  onSelectDate,
  onEventClick,
  onChipClick,
  onCreate,
  onOpenDay,
}: MonthViewProps) {
  // 从当月第一天所在周的开始铺满 6×7
  const grid = useMemo(() => {
    const start = date.startOf('month').startOf('week');
    return Array.from({ length: 42 }, (_, i) => start.add(i, 'day'));
  }, [date]);

  const month = date.format('YYYY-MM');

  const byDay = useMemo(() => {
    const map = new Map<
      string,
      { key: string; label: string; color: KEventColor; sort: number; kind: 'event' | 'chip'; id: string }[]
    >();
    for (const chip of allDayChips) {
      const list = map.get(chip.date) ?? [];
      list.push({ key: chip.id, label: chip.title, color: chip.color ?? 'purple', sort: -2, kind: 'chip', id: chip.id });
      map.set(chip.date, list);
    }
    for (const e of events) {
      const list = map.get(e.date) ?? [];
      list.push({
        key: e.id,
        label: `${fmtHHMM(e.start)} ${e.title}`,
        color: e.color as KEventColor,
        sort: e.start,
        kind: 'event',
        id: e.id,
      });
      map.set(e.date, list);
    }
    for (const list of map.values()) list.sort((a, b) => a.sort - b.sort);
    return map;
  }, [events, allDayChips]);

  const headers = grid.slice(0, 7).map((d) => `周${WEEKDAYS_CN[d.day()]}`);

  return (
    <div className="kg-month">
      <div className="kg-month-weekdays" style={{ gridTemplateColumns: 'repeat(7, minmax(0, 1fr))' }}>
        {headers.map((h) => (
          <div key={h} className="kg-month-dow kg-t14">
            {h}
          </div>
        ))}
      </div>
      <div
        className="kg-month-grid"
        style={{ gridTemplateColumns: 'repeat(7, minmax(0, 1fr))', gridTemplateRows: 'repeat(6, minmax(0, 1fr))' }}
      >
        {grid.map((d, i) => {
          const dayKey = d.format('YYYY-MM-DD');
          const items = byDay.get(dayKey) ?? [];
          const inMonth = dayKey.startsWith(month);
          const selected = dayKey === selectedDate;
          const isToday = dayKey === today;
          const hidden = items.length - MAX_CHIPS;
          return (
            <div
              key={dayKey}
              onClick={(e) => {
                if (e.target === e.currentTarget) onSelectDate(d);
              }}
              onDoubleClick={(e) => {
                if (e.target === e.currentTarget) onCreate?.({ date: dayKey, start: 540, end: 600 });
              }}
              className={`kg-month-cell ${i % 7 > 0 ? '' : 'kg-no-left-border'} ${inMonth ? '' : 'kg-outside'}`}
            >
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectDate(d);
                }}
                aria-label={dayKey}
                className={[
                  'kg-month-daynum',
                  'kg-t14',
                  selected ? 'kg-selected' : '',
                  isToday ? 'kg-today' : '',
                  inMonth ? '' : 'kg-outside-num',
                ].join(' ')}
              >
                {d.date()}
              </button>
              {items.slice(0, MAX_CHIPS).map((it) => (
                <button
                  key={it.key}
                  type="button"
                  onClick={(e) => {
                    if (it.kind === 'event') onEventClick?.(it.id, e.currentTarget);
                    else onChipClick?.({ id: it.id, date: dayKey, title: it.label, color: it.color }, e.currentTarget);
                  }}
                  className={`kg-month-chip kg-salt ${inMonth ? '' : 'kg-dim'}`}
                  style={eventStyle(it.color)}
                >
                  <span style={{ overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{it.label}</span>
                </button>
              ))}
              {hidden > 0 && (
                <button
                  type="button"
                  onClick={() => onOpenDay?.(d)}
                  className="kg-month-more kg-t12"
                >
                  +{hidden} 更多
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
