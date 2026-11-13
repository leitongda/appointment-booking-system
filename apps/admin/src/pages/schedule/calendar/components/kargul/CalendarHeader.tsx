import { useMemo } from 'react';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import { isoWeek, WEEKDAYS_CN } from './layout';

export type CalendarView = 'day' | 'week' | 'month';

interface CalendarHeaderProps {
  view: CalendarView;
  /** 当前聚焦日期 */
  date: Dayjs;
  /** 当前视图可见的日期（用于范围副标题） */
  days: Dayjs[];
  onViewChange: (view: CalendarView) => void;
  onToday: () => void;
  onStep: (dir: -1 | 1) => void;
}

const VIEWS: { id: CalendarView; label: string }[] = [
  { id: 'day', label: '日' },
  { id: 'week', label: '周' },
  { id: 'month', label: '月' },
];

/** M月D日；同月范围缩写为「M月D日 – D日」 */
const fmtDay = (d: Dayjs) => `${d.month() + 1}月${d.date()}日`;
const fmtRange = (a: Dayjs, b: Dayjs) =>
  a.month() === b.month() ? `${a.month() + 1}月${a.date()}日 – ${b.date()}日` : `${fmtDay(a)} – ${fmtDay(b)}`;

/**
 * 日历头部 —— 1:1 复刻 kargulstudio/calender-app-design 的 CalendarHeader：
 * 左侧「月份 + 周序号·范围」双行标题，右侧 今天 / 箭头组 / 滑动分段切换器。
 */
export function CalendarHeader({ view, date, days, onViewChange, onToday, onStep }: CalendarHeaderProps) {
  const subtitle = useMemo(() => {
    const week = isoWeek(date.toDate());
    if (view === 'month') {
      const first = date.startOf('month');
      const last = first.endOf('month');
      return `${fmtRange(first, last)} · 共 ${first.daysInMonth()} 天`;
    }
    if (view === 'day') return `第${week}周 · ${fmtDay(date)} 周${WEEKDAYS_CN[date.day()]}`;
    if (days.length > 0) return `第${week}周 · ${fmtRange(days[0], days[days.length - 1])}`;
    return `第${week}周`;
  }, [view, date, days]);

  const activeIndex = VIEWS.findIndex((v) => v.id === view);
  const unit = view === 'day' ? '日' : view === 'week' ? '周' : '月';

  return (
    <div className="kg-header">
      <div className="kg-header-titles">
        <h2 className="kg-t16">{`${date.year()}年${date.month() + 1}月`}</h2>
        <p className="kg-t14 kg-salt">{subtitle}</p>
      </div>

      <button type="button" className="kg-btn kg-press" onClick={onToday}>
        今天
      </button>

      <div className="kg-arrows">
        <button type="button" onClick={() => onStep(-1)} aria-label={`上一个${unit}`}>
          <LeftOutlined style={{ fontSize: 12 }} />
        </button>
        <span className="kg-arrows-divider" aria-hidden />
        <button type="button" onClick={() => onStep(1)} aria-label={`下一个${unit}`}>
          <RightOutlined style={{ fontSize: 12 }} />
        </button>
      </div>

      <div className="kg-seg" role="tablist" aria-label="日历视图" style={{ ['--kg-seg-i' as string]: activeIndex }}>
        <span className="kg-seg-pill" aria-hidden />
        {VIEWS.map((v) => (
          <button
            key={v.id}
            type="button"
            role="tab"
            aria-selected={view === v.id}
            className={`kg-salt ${view === v.id ? 'kg-seg-active' : ''}`}
            onClick={() => onViewChange(v.id)}
          >
            {v.label}
          </button>
        ))}
      </div>
    </div>
  );
}
