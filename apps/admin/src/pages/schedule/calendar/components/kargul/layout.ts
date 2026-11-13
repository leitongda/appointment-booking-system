import type { Schedule } from '@hospital/shared';

/**
 * 时间网格几何 —— 复刻 kargulstudio/calender-app-design (MIT) src/components/calendar/layout.ts
 * 一小时 = 64px（与 Figma 一致：每小时一条刻度线），15 分钟吸附。
 */
export const HOUR_HEIGHT = 64;
export const SNAP_MINUTES = 15;
export const MIN_EVENT_MINUTES = 15;

export const minutesToPx = (m: number) => (m / 60) * HOUR_HEIGHT;
export const pxToMinutes = (px: number) => (px / HOUR_HEIGHT) * 60;
export const snap = (m: number, step: number = SNAP_MINUTES) => Math.round(m / step) * step;
export const clamp = (n: number, min: number, max: number) => Math.min(max, Math.max(min, n));

export const minutesToHHMM = (m: number) =>
  `${Math.floor(m / 60).toString().padStart(2, '0')}:${(m % 60).toString().padStart(2, '0')}`;

export const parseHHMM = (t?: string): number | null => {
  if (!t) return null;
  const [h, m] = t.split(':').map(Number);
  if (Number.isNaN(h) || Number.isNaN(m)) return null;
  return h * 60 + m;
};

/** 日历事件抽象：由排班（或休息日标记）映射而来 */
export interface CalEvent {
  id: string;
  /** YYYY-MM-DD */
  date: string;
  /** 距 0 点的分钟数 */
  start: number;
  end: number;
  allDay?: boolean;
  color: string;
  title: string;
  note?: string;
  /** 停诊/被覆盖等：仅可点击，不可拖动/缩放 */
  locked?: boolean;
  schedule: Schedule;
}

export type PositionedEvent = { event: CalEvent; column: number; columns: number };

/**
 * 重叠事件并排分列布局：把互相重叠（传递闭包）的事件聚成一簇，
 * 每簇用最少的列保证互不碰撞。
 */
export function layoutDay(events: CalEvent[]): PositionedEvent[] {
  const sorted = [...events].sort((a, b) => a.start - b.start || b.end - a.end);
  const out: PositionedEvent[] = [];
  let cluster: { event: CalEvent; column: number }[] = [];
  let clusterEnd = -1;
  let columnEnds: number[] = [];

  const flush = () => {
    const columns = columnEnds.length;
    for (const c of cluster) out.push({ ...c, columns });
    cluster = [];
    columnEnds = [];
  };

  for (const event of sorted) {
    if (event.start >= clusterEnd && cluster.length) flush();
    let column = columnEnds.findIndex((end) => end <= event.start);
    if (column === -1) {
      column = columnEnds.length;
      columnEnds.push(event.end);
    } else {
      columnEnds[column] = event.end;
    }
    cluster.push({ event, column });
    clusterEnd = Math.max(clusterEnd, event.end);
  }
  if (cluster.length) flush();
  return out;
}

/** ISO 周序号（周一为一周开始） */
export function isoWeek(d: Date): number {
  const target = new Date(d.valueOf());
  const dayNr = (d.getDay() + 6) % 7;
  target.setDate(target.getDate() - dayNr + 3);
  const firstThursday = new Date(target.getFullYear(), 0, 4);
  const diff = target.valueOf() - firstThursday.valueOf();
  return 1 + Math.round(diff / (7 * 24 * 3600 * 1000));
}

export const WEEKDAYS_CN = ['日', '一', '二', '三', '四', '五', '六'];

/** 当前时刻距 0 点的分钟数 */
export const nowMinutesOfDay = () => {
  const n = new Date();
  return n.getHours() * 60 + n.getMinutes() + n.getSeconds() / 60;
};
