import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import dayjs, { Dayjs } from 'dayjs';
import { CalendarOutlined, PlusOutlined } from '@ant-design/icons';
import { WEEKDAYS_CN, type CalEvent } from './layout';
import { K_EVENT_FG, SCHEDULE_BADGE, type KEventColor } from './colors';

export interface PopoverTarget {
  event: CalEvent;
  anchor: DOMRect;
}

interface SchedulePopoverProps {
  target: PopoverTarget | null;
  onClose: () => void;
  /** 有剩余号源且具备预约创建能力时展示 */
  onCreateAppointment?: (schedule: CalEvent['schedule']) => void;
  onOpenDay?: (date: Dayjs) => void;
}

const POP_WIDTH = 300;
const POP_EST_HEIGHT = 240;
const EDGE = 12;

const fmtDuration = (minutes: number) => {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h && m) return `${h}小时${m}分钟`;
  if (h) return `${h}小时`;
  return `${m}分钟`;
};

/**
 * 排班详情弹层 —— 复刻设计的 origin-aware EventPopover：
 * 固定定位卡片锚在被点元素旁（默认右侧、溢出翻转），点外部/Esc/滚动关闭。
 */
export function SchedulePopover({ target, onClose, onCreateAppointment, onOpenDay }: SchedulePopoverProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  const event = target?.event;
  const anchor = target?.anchor;

  // 计算位置：优先右侧对齐锚点顶部，右溢出翻到左侧，上下夹取
  useLayoutEffect(() => {
    if (!anchor) {
      setPos(null);
      return;
    }
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let left = anchor.right + 8;
    if (left + POP_WIDTH > vw - EDGE) left = anchor.left - POP_WIDTH - 8;
    if (left < EDGE) left = Math.min(vw - POP_WIDTH - EDGE, Math.max(EDGE, anchor.left));
    let top = anchor.top;
    if (top + POP_EST_HEIGHT > vh - EDGE) top = vh - POP_EST_HEIGHT - EDGE;
    if (top < EDGE) top = EDGE;
    setPos({ left, top });
  }, [anchor]);

  useEffect(() => {
    if (!target) return;
    const onPointerDown = (e: PointerEvent) => {
      if (ref.current && e.target instanceof Node && ref.current.contains(e.target)) return;
      onClose();
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('pointerdown', onPointerDown, true);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown, true);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [target, onClose]);

  const date = useMemo(() => (event ? dayjs(event.date) : null), [event]);
  if (!event || !date) return null;

  const remaining = event.schedule.totalSlots - event.schedule.bookedSlots;
  const badge = SCHEDULE_BADGE[event.color as KEventColor] ?? SCHEDULE_BADGE.green;
  const timeRange = `${fmtHHMM(event.start)} – ${fmtHHMM(event.end)} · ${fmtDuration(event.end - event.start)}`;

  return createPortal(
    <div ref={ref} className="kg-root" role="dialog" aria-label="排班详情">
      <div className="kg-pop" style={{ left: pos?.left ?? -9999, top: pos?.top ?? -9999, visibility: pos ? 'visible' : 'hidden' }}>
        <div className="kg-pop-head">
          <span className="kg-pop-swatch" style={{ background: K_EVENT_FG(event.color as KEventColor) }} />
          <div className="kg-pop-body">
            <h3 className="kg-t16">{event.schedule.doctorName ? `${event.schedule.doctorName} · ${event.title}` : event.title}</h3>
            <p className="kg-t14 kg-salt">
              {`周${WEEKDAYS_CN[date.day()]}，${date.month() + 1}月${date.date()}日`}
            </p>
            <p className="kg-t14 kg-salt">{event.schedule.isRestDay ? '全天' : timeRange}</p>
            <div className="kg-pop-meta">
              <span className={`kg-badge kg-badge-${badge.tone} kg-t12`}>{badge.text}</span>
              <span className="kg-t12" style={{ color: 'var(--kg-text-secondary)' }}>
                {event.note}
                {remaining > 0 ? ` · 剩余 ${remaining}` : ''}
              </span>
            </div>
          </div>
        </div>
        <div className="kg-pop-foot">
          {onCreateAppointment && remaining > 0 && (
            <button
              type="button"
              className="kg-btn kg-press"
              onClick={() => {
                onClose();
                onCreateAppointment(event.schedule);
              }}
            >
              <PlusOutlined style={{ fontSize: 11 }} />
              创建预约
            </button>
          )}
          {onOpenDay && (
            <button
              type="button"
              className="kg-btn kg-press"
              onClick={() => {
                onClose();
                onOpenDay(date);
              }}
            >
              <CalendarOutlined style={{ fontSize: 12, color: 'var(--kg-text-secondary)' }} />
              当天详情
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}

const fmtHHMM = (m: number) => `${Math.floor(m / 60).toString().padStart(2, '0')}:${(m % 60).toString().padStart(2, '0')}`;
