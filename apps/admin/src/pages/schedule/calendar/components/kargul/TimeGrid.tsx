import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { Dayjs } from 'dayjs';
import {
  clamp,
  HOUR_HEIGHT,
  layoutDay,
  MIN_EVENT_MINUTES,
  minutesToHHMM,
  minutesToPx,
  nowMinutesOfDay,
  pxToMinutes,
  snap,
  SNAP_MINUTES,
  WEEKDAYS_CN,
  type CalEvent,
} from './layout';
import { eventStyle, type KEventColor } from './colors';

const HOURS = Array.from({ length: 23 }, (_, i) => i + 1);
const DRAG_THRESHOLD = 4;
/** 列的最小宽度，低于则横向滚动 */
const MIN_COLUMN = 96;
/** 初始滚动到 07:00，留出上班前的余量 */
const INITIAL_SCROLL_HOUR = 7;

export interface AllDayChip {
  id: string;
  /** YYYY-MM-DD */
  date: string;
  title: string;
  color?: KEventColor;
}

export interface CreatePayload {
  date: string;
  start: number;
  end: number;
}

export interface MovePayload {
  eventId: string;
  date: string;
  start: number;
  end: number;
}

type Drag =
  | { type: 'create'; dayIndex: number; anchor: number; current: number; moved: boolean }
  | {
      type: 'move' | 'resize';
      eventId: string;
      dayIndex: number;
      start: number;
      end: number;
      grabOffset: number;
      moved: boolean;
      locked: boolean;
    };

interface TimeGridProps {
  days: Dayjs[];
  events: CalEvent[];
  /** 全天泳道 chips（休息日等） */
  allDayChips: AllDayChip[];
  /** YYYY-MM-DD */
  selectedDate: string;
  today: string;
  onSelectDate: (d: Dayjs) => void;
  /** 具备 schedule:create 权限时为 true：空档拖拽/点击直接生成排班 */
  canCreate?: boolean;
  /** 具备 schedule:update 权限时为 true：可拖动排班、拖拽底边缩放 */
  canUpdate?: boolean;
  onCreate?: (p: CreatePayload) => void;
  onMove?: (p: MovePayload) => void;
  onResize?: (p: MovePayload) => void;
  onAllDayChipClick?: (chip: AllDayChip, el: HTMLElement) => void;
  onEventClick?: (eventId: string, el: HTMLElement) => void;
  /** 网格滚动时回调（用于关闭弹层） */
  onScroll?: () => void;
}

/** 星期表头：灰色星期缩写 + 日期徽标（今天紫色文字、选中紫色徽标） */
function DayHeaders({
  days,
  selectedDate,
  today,
  onSelectDate,
}: {
  days: Dayjs[];
  selectedDate: string;
  today: string;
  onSelectDate: (d: Dayjs) => void;
}) {
  return (
    <div className="kg-dayheaders">
      <div className="kg-axis-spacer" />
      {days.map((d) => {
        const key = d.format('YYYY-MM-DD');
        const isSelected = key === selectedDate;
        const isToday = key === today;
        return (
          <button
            key={key}
            type="button"
            onClick={() => onSelectDate(d)}
            aria-pressed={isSelected}
            aria-label={`${d.year()}年${d.month() + 1}月${d.date()}日 周${WEEKDAYS_CN[d.day()]}`}
            className="kg-dayheader"
          >
            <span className="kg-dow kg-t14">{`周${WEEKDAYS_CN[d.day()]}`}</span>
            <span className={`kg-daynum kg-t16 kg-salt ${isSelected ? 'kg-selected' : ''} ${isToday ? 'kg-today' : ''}`}>
              {d.date()}
            </span>
          </button>
        );
      })}
    </div>
  );
}

/** 全天泳道：休息日等全天项，紫色 chip 与设计的 National holiday 一致 */
function AllDayRow({
  days,
  chips,
  onChipClick,
}: {
  days: Dayjs[];
  chips: AllDayChip[];
  onChipClick?: (chip: AllDayChip, el: HTMLElement) => void;
}) {
  const chipsByDay = useMemo(
    () => days.map((d) => chips.filter((c) => c.date === d.format('YYYY-MM-DD'))),
    [days, chips],
  );
  const most = Math.max(1, ...chipsByDay.map((c) => c.length));
  const height = 5.5 * 2 + most * 28 + (most - 1) * 4 + 1;

  return (
    <div className="kg-allday" style={{ height }}>
      <div className="kg-allday-label">
        {most > 1 && <span className="kg-t12">全天</span>}
      </div>
      {days.map((d, i) => (
        <div key={d.format('YYYY-MM-DD')} className="kg-allday-cell" role="group" aria-label="全天">
          {chipsByDay[i].map((chip) => (
            <button
              key={chip.id}
              type="button"
              className="kg-chip kg-press kg-t14 kg-salt"
              style={eventStyle(chip.color ?? 'purple')}
              onClick={(e) => onChipClick?.(chip, e.currentTarget)}
            >
              <span style={{ minWidth: 0, flex: 1, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                {chip.title}
              </span>
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}

function EventBlock({
  event,
  column,
  count,
  draggable,
  dragging,
  onOpen,
  onPointerDownEvent,
}: {
  event: CalEvent;
  column: number;
  count: number;
  draggable: boolean;
  dragging: boolean;
  onOpen: (el: HTMLElement) => void;
  onPointerDownEvent: (e: React.PointerEvent, eventEl: HTMLElement, resizing: boolean) => void;
}) {
  const height = minutesToPx(event.end - event.start) - 2;
  const compact = height < 44;
  const time = `${minutesToHHMM(event.start)} – ${minutesToHHMM(event.end)}`;
  const resizable = draggable && height >= MIN_EVENT_MINUTES;

  return (
    <div
      data-event-id={event.id}
      role="button"
      tabIndex={0}
      aria-label={`${event.title}，${time}${event.note ? `，${event.note}` : ''}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onOpen(e.currentTarget);
        }
      }}
      onPointerDown={(e) => onPointerDownEvent(e, e.currentTarget, false)}
      className={[
        'kg-event',
        draggable ? 'kg-can-drag' : 'kg-locked',
        dragging ? 'kg-dragging' : '',
      ].join(' ')}
      style={{
        ...eventStyle(event.color as KEventColor),
        top: minutesToPx(event.start) + 1,
        height: Math.max(height, 14),
        left: `calc((100% - 5px) * ${column / count} + 2px)`,
        width: `calc((100% - 5px) / ${count} - ${count > 1 ? 2 : 0}px)`,
        zIndex: dragging ? 30 : 10 + column,
      }}
    >
      {compact ? (
        <div className="kg-event-compact">
          <p className="kg-ev-compact-title kg-salt">
            {event.title}
            {height >= 28 && <span className="kg-ev-compact-time kg-t12">{minutesToHHMM(event.start)}</span>}
          </p>
        </div>
      ) : (
        <div className="kg-event-body">
          <p className="kg-ev-title kg-salt">{event.title}</p>
          <p className="kg-ev-time kg-salt">{time}</p>
          {event.note && <p className="kg-ev-note kg-salt">{event.note}</p>}
        </div>
      )}
      {resizable && (
        <span
          data-resize
          aria-hidden
          onPointerDown={(e) => {
            // 阻止冒泡到事件块自身的 pointerdown，否则会被覆盖为整体拖动
            e.stopPropagation();
            onPointerDownEvent(e, e.currentTarget.parentElement as HTMLElement, true);
          }}
          className="kg-resize"
        />
      )}
    </div>
  );
}

/**
 * 时间网格 —— 1:1 复刻 kargulstudio/calender-app-design 的 TimeGrid：
 * 64px/小时、15 分钟吸附、空档拖拽生成（虚线幽灵块）、事件拖动跨天、
 * 底边缩放、重叠并排分列、紫色 now 线。
 */
export function TimeGrid({
  days,
  events,
  allDayChips,
  selectedDate,
  today,
  onSelectDate,
  canCreate = false,
  canUpdate = false,
  onCreate,
  onMove,
  onResize,
  onAllDayChipClick,
  onEventClick,
  onScroll,
}: TimeGridProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const pointerStart = useRef<{ x: number; y: number; target: HTMLElement | null } | null>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  const [nowMin, setNowMin] = useState(nowMinutesOfDay);

  useEffect(() => {
    const t = setInterval(() => setNowMin(nowMinutesOfDay()), 30_000);
    return () => clearInterval(t);
  }, []);

  useLayoutEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = INITIAL_SCROLL_HOUR * HOUR_HEIGHT;
  }, []);

  // 拖拽进行中把位移作为预览应用，布局实时回流
  const columns = useMemo(() => {
    const preview =
      drag && drag.type !== 'create' && drag.moved && !drag.locked
        ? { id: drag.eventId, date: days[drag.dayIndex]?.format('YYYY-MM-DD'), start: drag.start, end: drag.end }
        : null;
    return days.map((day) => {
      const dayKey = day.format('YYYY-MM-DD');
      const dayEvents = events
        .map((e) => (preview && e.id === preview.id ? { ...e, date: preview.date!, start: preview.start, end: preview.end } : e))
        .filter((e) => !e.allDay && e.date === dayKey);
      return layoutDay(dayEvents);
    });
  }, [days, events, drag]);

  function pointToSlot(clientX: number, clientY: number) {
    const rect = bodyRef.current!.getBoundingClientRect();
    const colWidth = rect.width / days.length;
    return {
      dayIndex: clamp(Math.floor((clientX - rect.left) / colWidth), 0, days.length - 1),
      minutes: clamp(pxToMinutes(clientY - rect.top), 0, 1440),
    };
  }

  function startDrag(eventEl: HTMLElement, minutes: number, resizing: boolean) {
    const ev = events.find((x) => x.id === eventEl.dataset.eventId);
    if (!ev) return;
    setDrag({
      type: resizing ? 'resize' : 'move',
      eventId: ev.id,
      dayIndex: days.findIndex((d) => d.format('YYYY-MM-DD') === ev.date),
      start: ev.start,
      end: ev.end,
      grabOffset: minutes - ev.start,
      moved: false,
      locked: Boolean(ev.locked) || !canUpdate,
    });
  }

  function onPointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return;
    const target = e.target as Element;
    const eventEl = target.closest<HTMLElement>('[data-event-id]');
    if (eventEl) return; // 事件块自身的 pointerdown 由 EventBlock 处理
    const { dayIndex, minutes } = pointToSlot(e.clientX, e.clientY);
    pointerStart.current = { x: e.clientX, y: e.clientY, target: null };
    e.currentTarget.setPointerCapture(e.pointerId);

    if (canCreate) {
      const m = snap(minutes - SNAP_MINUTES / 2);
      setDrag({ type: 'create', dayIndex, anchor: m, current: m, moved: false });
    }
  }

  function onPointerDownEvent(e: React.PointerEvent, eventEl: HTMLElement, resizing: boolean) {
    if (e.button !== 0) return;
    const { minutes } = pointToSlot(e.clientX, e.clientY);
    pointerStart.current = { x: e.clientX, y: e.clientY, target: eventEl };
    (eventEl.closest('.kg-daycols') as HTMLElement | null)?.setPointerCapture(e.pointerId);
    startDrag(eventEl, minutes, resizing);
  }

  function onPointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!drag || !pointerStart.current) return;
    const dist = Math.hypot(e.clientX - pointerStart.current.x, e.clientY - pointerStart.current.y);
    const moved = drag.moved || dist > DRAG_THRESHOLD;
    if (!moved) return;
    const { dayIndex, minutes } = pointToSlot(e.clientX, e.clientY);

    if (drag.type === 'create') {
      setDrag({ ...drag, moved, current: snap(minutes) });
    } else if (drag.locked) {
      setDrag({ ...drag, moved });
    } else if (drag.type === 'move') {
      const length = drag.end - drag.start;
      const start = clamp(snap(minutes - drag.grabOffset), 0, 1440 - length);
      setDrag({ ...drag, moved, dayIndex, start, end: start + length });
    } else {
      const end = clamp(snap(minutes), drag.start + MIN_EVENT_MINUTES, 1440);
      setDrag({ ...drag, moved, end });
    }
  }

  function onPointerUp(e: React.PointerEvent<HTMLDivElement>) {
    const d = drag;
    const start = pointerStart.current;
    setDrag(null);
    pointerStart.current = null;
    if (!d) return;

    if (d.type === 'create') {
      const day = days[d.dayIndex];
      const dateStr = day?.format('YYYY-MM-DD');
      if (!dateStr) return;
      if (!d.moved) {
        // 点击空档：默认生成 1 小时排班
        const s = clamp(Math.floor(d.anchor / 30) * 30, 0, 1380);
        onCreate?.({ date: dateStr, start: s, end: s + 60 });
      } else {
        const s = Math.min(d.anchor, d.current);
        const en = Math.max(d.anchor, d.current, s + MIN_EVENT_MINUTES);
        onCreate?.({ date: dateStr, start: s, end: en });
      }
      return;
    }
    if (!d.moved || d.locked) {
      if (start?.target) onEventClick?.(d.eventId, start.target);
      return;
    }
    const dateStr = days[d.dayIndex]?.format('YYYY-MM-DD');
    const ev = events.find((x) => x.id === d.eventId);
    if (!ev || !dateStr) return;
    if (ev.date !== dateStr || ev.start !== d.start || ev.end !== d.end) {
      if (d.type === 'move') onMove?.({ eventId: d.eventId, date: dateStr, start: d.start, end: d.end });
      else onResize?.({ eventId: d.eventId, date: ev.date, start: ev.start, end: d.end });
    }
  }

  const nowMinutes = nowMin;
  const todayIndex = days.findIndex((d) => d.format('YYYY-MM-DD') === today);
  const createGhost =
    drag?.type === 'create'
      ? {
          dayIndex: drag.dayIndex,
          start: drag.moved
            ? Math.min(drag.anchor, drag.current)
            : clamp(Math.floor(drag.anchor / 30) * 30, 0, 1380),
          end: drag.moved
            ? Math.max(drag.anchor, drag.current, Math.min(drag.anchor, drag.current) + MIN_EVENT_MINUTES)
            : clamp(Math.floor(drag.anchor / 30) * 30, 0, 1380) + 60,
        }
      : null;

  return (
    <>
      <div
        ref={scrollRef}
        onScroll={onScroll}
        className="kg-scroller kg-scroll-none"
      >
        <div
          className="kg-gridwrap"
          style={{ width: `max(100%, calc(var(--kg-axis, 70px) + ${days.length * MIN_COLUMN}px))` }}
        >
          <div className="kg-stickyhead">
            <DayHeaders days={days} selectedDate={selectedDate} today={today} onSelectDate={onSelectDate} />
            <AllDayRow days={days} chips={allDayChips} onChipClick={onAllDayChipClick} />
          </div>

          <div className="kg-bodyrow" style={{ height: 24 * HOUR_HEIGHT }}>
            {/* 整点刻度线 */}
            <div className="kg-hourlines" aria-hidden>
              {HOURS.map((h) => (
                <div key={h} className="kg-hourline" style={{ top: h * HOUR_HEIGHT }} />
              ))}
            </div>

            {/* 时间轴 */}
            <div className="kg-axis" aria-hidden>
              {HOURS.map((h) => (
                <span
                  key={h}
                  className="kg-t14"
                  style={{ top: h * HOUR_HEIGHT - 7 }}
                >
                  {`${h.toString().padStart(2, '0')}:00`}
                </span>
              ))}
            </div>

            {/* 日列 */}
            <div
              ref={bodyRef}
              className={`kg-daycols ${drag?.moved && drag.type === 'move' && !drag.locked ? 'kg-grabbing' : ''}`}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerCancel={() => {
                pointerStart.current = null;
                setDrag(null);
              }}
            >
              {days.map((day, i) => {
                const dayKey = day.format('YYYY-MM-DD');
                return (
                  <div key={dayKey} className="kg-daycol" role="group" aria-label={`${dayKey} 排班`}>
                    {columns[i].map(({ event, column, columns: count }) => (
                      <EventBlock
                        key={event.id}
                        event={event}
                        column={column}
                        count={count}
                        draggable={!event.locked && canUpdate}
                        dragging={Boolean(drag && drag.type !== 'create' && drag.eventId === event.id && drag.moved && !drag.locked)}
                        onOpen={(el) => onEventClick?.(event.id, el)}
                        onPointerDownEvent={onPointerDownEvent}
                      />
                    ))}

                    {createGhost?.dayIndex === i && (
                      <div
                        className="kg-ghost"
                        style={{
                          top: minutesToPx(createGhost.start) + 1,
                          height: Math.max(minutesToPx(createGhost.end - createGhost.start) - 2, 14),
                          left: 2,
                          right: 3,
                        }}
                      >
                        <span className="kg-t12 kg-salt">
                          {`${minutesToHHMM(createGhost.start)} – ${minutesToHHMM(createGhost.end)}`}
                        </span>
                      </div>
                    )}

                    {i === todayIndex && nowMinutes >= 0 && nowMinutes <= 1440 && (
                      <div
                        className="kg-nowline"
                        style={{ top: minutesToPx(nowMinutes) - 4 }}
                        aria-label={`当前 ${minutesToHHMM(Math.floor(nowMinutes))}`}
                      >
                        <span className="kg-nowdot" />
                        <span className="kg-nowbar" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
