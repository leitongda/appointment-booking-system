/**
 * 会话录制器（rrweb）
 *
 * 启动 rrweb record，将原始事件入队，按批量 + 定时上报到后端
 * /session-events/batch 接口（无需认证，后端用 get_optional_account 提取 actor）。
 *
 * 上报机制完全复刻 packages/shared/src/analytics/tracker.ts：
 *   - batchSize 阈值 / batchInterval 定时 双触发
 *   - beforeunload + visibilitychange(hidden) 兜底 flush
 *   - sendBeacon(blob) 优先，fetch(keepalive) 兜底
 *   - 失败回插队列，上限 500 条防内存泄漏
 *
 * 与 behavior_log / tracker 共用同一个 session_id（通过 getTracker().getSessionId()），
 * 拿不到则用 sessionStorage 自行生成一份，保证 rrweb 数据可被同一会话串联。
 */
import { record } from 'rrweb';
import { getTracker } from '@hospital/shared';

/**
 * rrweb 单个事件类型。
 *
 * rrweb 2.x alpha 将共享类型拆到了 @rrweb/types 子包，主包是否再导出
 * recordOptions 在不同 alpha 版本间不稳定；这里仅声明实际使用到的字段，
 * 并通过 record<RRWebEvent>() 将该类型注入 record 的泛型 T，使 emit 回调
 * 与队列元素的类型保持一致，避免对子包路径的硬依赖。
 */
interface RRWebEvent {
  timestamp: number;
  [key: string]: unknown;
}

/** 上报请求体（camelCase，与后端 session_events batch 契约一致） */
interface SessionBatchPayload {
  sessionId: string;
  viewportW: number;
  viewportH: number;
  pagePath: string | null;
  sequence: number;
  startedAt: string | null;
  endedAt: string | null;
  events: RRWebEvent[];
}

/** 批量上报阈值：达到该条数立即 flush */
const BATCH_SIZE = 100;
/** 定时 flush 间隔（ms） */
const BATCH_INTERVAL = 30_000;
/** 失败回插队列上限，防止内存泄漏 */
const MAX_QUEUE_SIZE = 500;
/** sessionStorage 中 session_id 的 key */
const SESSION_KEY = '__rrweb_session_id__';

let eventQueue: RRWebEvent[] = [];
let flushTimer: ReturnType<typeof setInterval> | null = null;
let stopFn: (() => void) | null = null;
let sessionId = '';
let sequence = 0;
let recording = false;
let flushing = false;
/** 上次 flush 时的视口/路径快照（用于在 batch 维度记录主要页面） */
let lastPagePath: string | null = null;

const debug = process.env.NODE_ENV === 'development';
const API_BASE = process.env.API_BASE_URL || '/api/v1';
const BATCH_URL = `${API_BASE}/session-events/batch`;

/** 生成兜底 session_id（与 tracker 同款算法，但 key 独立避免覆盖） */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

/** 获取或生成 session_id：优先复用 tracker 的会话 */
function resolveSessionId(): string {
  const tracker = getTracker();
  if (tracker) {
    const sid = tracker.getSessionId();
    if (sid) return sid;
  }
  // 兜底：sessionStorage（tracker 的 key 是 __tracker_session_id__，这里用独立 key 但可读到同一个值更好；
  // 为避免相互覆盖，读 tracker key 优先复用）
  if (typeof window !== 'undefined' && window.sessionStorage) {
    const fromTracker = window.sessionStorage.getItem('__tracker_session_id__');
    if (fromTracker) return fromTracker;
    let sid = window.sessionStorage.getItem(SESSION_KEY);
    if (!sid) {
      sid = generateId();
      window.sessionStorage.setItem(SESSION_KEY, sid);
    }
    return sid;
  }
  return generateId();
}

/** 当前视口宽高 */
function getViewport(): { w: number; h: number } {
  if (typeof window === 'undefined') return { w: 0, h: 0 };
  return { w: window.innerWidth, h: window.innerHeight };
}

/** 当前页面路径（与 tracker 的 page_path 一致，用 pathname） */
function getPagePath(): string | null {
  if (typeof window === 'undefined' || !window.location) return null;
  return window.location.pathname || null;
}

/** ISO8601 时间戳（rrweb event.timestamp 是 ms epoch） */
function toISO(ms: number | undefined): string | null {
  if (!ms || typeof ms !== 'number') return null;
  try {
    return new Date(ms).toISOString();
  } catch {
    return null;
  }
}

/**
 * flush 当前队列到后端。
 * @param sync true 表示由 beforeunload/visibilitychange 触发，优先 sendBeacon
 */
async function flush(sync = false): Promise<void> {
  if (!sync && flushing) return;
  if (eventQueue.length === 0) return;

  if (!sync) {
    flushing = true;
  }

  const events = eventQueue.splice(0, eventQueue.length);

  // 队列可能跨越多次 flush，取首尾事件时间戳作为本批次时间范围
  const startedAt = events.length > 0 ? toISO(events[0]?.timestamp) : null;
  const endedAt =
    events.length > 0 ? toISO(events[events.length - 1]?.timestamp) : null;

  const { w, h } = getViewport();
  const payload: SessionBatchPayload = {
    sessionId,
    viewportW: w,
    viewportH: h,
    pagePath: lastPagePath ?? getPagePath(),
    sequence,
    startedAt,
    endedAt,
    events,
  };
  sequence += 1;

  const body = JSON.stringify(payload);

  if (debug) {
    // eslint-disable-next-line no-console
    console.log('[SessionRecorder] flush events:', events.length, 'seq:', payload.sequence);
  }

  try {
    // 1) 兜底场景（页面卸载/隐藏）优先 sendBeacon
    if (sync && typeof navigator !== 'undefined' && navigator.sendBeacon) {
      const ok = navigator.sendBeacon(
        BATCH_URL,
        new Blob([body], { type: 'application/json' }),
      );
      if (ok) return;
      // sendBeacon 失败（如队列满/数据过大）：若环境有 fetch，立即用
      // fetch(keepalive) 兜底发送这一批；否则回插队列等下次 flush。
      if (typeof fetch !== 'undefined') {
        await fetch(BATCH_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body,
          keepalive: true,
        });
        return;
      }
      // 既无可用通道：回插保留数据
      eventQueue.unshift(...events);
      trimQueue();
      return;
    }

    // 2) 非兜底场景：直接 fetch(keepalive)
    if (typeof fetch !== 'undefined') {
      await fetch(BATCH_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
      });
      return;
    }

    // 3) 既无 sendBeacon 也无 fetch：丢弃本批（避免无限堆积）
    if (debug) {
      // eslint-disable-next-line no-console
      console.warn('[SessionRecorder] no transport available, drop batch');
    }
  } catch (error) {
    if (debug) {
      // eslint-disable-next-line no-console
      console.error('[SessionRecorder] flush error:', error);
    }
    // 上报失败：事件回插队列（上限 500）
    eventQueue.unshift(...events);
    trimQueue();
  } finally {
    if (!sync) {
      flushing = false;
    }
  }
}

/** 裁剪队列到上限 */
function trimQueue(): void {
  if (eventQueue.length > MAX_QUEUE_SIZE) {
    eventQueue = eventQueue.slice(0, MAX_QUEUE_SIZE);
  }
}

/** 启动定时 flush */
function startFlushTimer(): void {
  if (flushTimer) return;
  flushTimer = setInterval(() => {
    flush().catch(() => {
      /* 错误已在 flush 内部处理 */
    });
  }, BATCH_INTERVAL);
}

/** 停止定时 flush */
function stopFlushTimer(): void {
  if (flushTimer) {
    clearInterval(flushTimer);
    flushTimer = null;
  }
}

/**
 * 初始化会话录制器。
 *
 * 必须在客户端（document 可用）调用；非浏览器环境直接 no-op。
 *
 * @param options.enabled 是否启用录制，默认 false。rrweb 全量录制 DOM 变更
 *   会在短时间内产生大量事件，生产环境默认关闭，仅在需要排查问题的开发 /
 *   灰度环境显式开启。
 */
export function initSessionRecorder(options?: { enabled?: boolean }): void {
  // 仅在浏览器环境运行
  if (typeof document === 'undefined' || typeof window === 'undefined') {
    return;
  }

  // 默认关闭：生产环境全量录制开销过大，需显式 enabled: true 才启动
  if (!options?.enabled) {
    return;
  }

  if (recording) {
    if (debug) {
      // eslint-disable-next-line no-console
      console.warn('[SessionRecorder] already running, skip');
    }
    return;
  }

  sessionId = resolveSessionId();
  lastPagePath = getPagePath();
  sequence = 0;

  try {
    const stop = record<RRWebEvent>({
      emit(event) {
        if (!event) return;
        eventQueue.push(event);
        trimQueue();
        // 达到批量阈值立即 flush
        if (eventQueue.length >= BATCH_SIZE) {
          flush().catch(() => {});
        }
      },
      // 采样降频：关闭 mousemove（最高频事件），scroll 每 150ms 采样一次，
      // input 只保留最后一次值。显著减少录制事件量与上报频次。
      sampling: {
        mousemove: false,
        scroll: 150,
        input: 'last',
      },
    });
    stopFn = typeof stop === 'function' ? stop : null;
    recording = true;
  } catch (error) {
    if (debug) {
      // eslint-disable-next-line no-console
      console.error('[SessionRecorder] record start failed:', error);
    }
    return;
  }

  startFlushTimer();

  // 页面卸载 / 切后台兜底 flush（与 tracker.ts 一致）
  const onUnload = () => flush(true).catch(() => {});
  const onVisibility = () => {
    if (document.visibilityState === 'hidden') {
      flush(true).catch(() => {});
    }
  };
  window.addEventListener('beforeunload', onUnload);
  window.addEventListener('pagehide', onUnload);
  document.addEventListener('visibilitychange', onVisibility);

  // 记录停止时移除监听
  const originalStop = stopFn;
  stopFn = () => {
    window.removeEventListener('beforeunload', onUnload);
    window.removeEventListener('pagehide', onUnload);
    document.removeEventListener('visibilitychange', onVisibility);
    if (typeof originalStop === 'function') {
      try {
        originalStop();
      } catch {
        /* rrweb stop 失败不影响清理 */
      }
    }
  };

  if (debug) {
    // eslint-disable-next-line no-console
    console.log('[SessionRecorder] started, sessionId:', sessionId);
  }
}

/** 停止录制并清理（含定时器、监听、最后一批 flush） */
export function stopSessionRecorder(): void {
  if (!recording) return;
  stopFlushTimer();
  if (typeof stopFn === 'function') {
    stopFn();
    stopFn = null;
  }
  recording = false;
  // 停止前尽力 flush 剩余事件（同步，走 sendBeacon）
  flush(true).catch(() => {});
}

/** 强制立即 flush（异步，用于手动触发或测试） */
export async function forceFlush(): Promise<void> {
  await flush(false);
}
