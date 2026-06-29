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
/** 错误触发模式下，捕获到错误后持续录制/上报的窗口时长（ms） */
const ERROR_TRIGGER_WINDOW = 30_000;

/** 录制模式
 * - always：全量录制（dev 环境），事件一旦入队即按阈值/定时 flush
 * - error-triggered：生产推荐。持续录制进环形缓冲但不 flush，直到捕获到
 *   JS error / unhandledrejection 才"激活"——保留缓冲 + 开始正常 flush，
 *   持续 ERROR_TRIGGER_WINDOW 后回到待机。这样生产环境只录出错会话，
 *   开销可控且最有诊断价值。
 * - disabled：不录制
 */
export type RecordingMode = 'always' | 'error-triggered' | 'disabled';

let eventQueue: RRWebEvent[] = [];
let flushTimer: ReturnType<typeof setInterval> | null = null;
let stopFn: (() => void) | null = null;
let sessionId = '';
let sequence = 0;
let recording = false;
let flushing = false;
/** 当前录制模式 */
let recordingMode: RecordingMode = 'disabled';
/** error-triggered 模式下，是否已因错误被激活（激活后才开始 flush 上报） */
let errorTriggered = false;
/** 错误激活后的窗口结束时间戳；过期后回到待机 */
let errorWindowEnd = 0;
/** 上次 flush 时的视口/路径快照（用于在 batch 维度记录主要页面） */
let lastPagePath: string | null = null;

const debug = process.env.NODE_ENV === 'development';
const API_BASE = process.env.API_BASE_URL || '/api/v1';
const BATCH_URL = `${API_BASE}/session-events/batch`;

/** 生成兜底 session_id（优先 crypto.randomUUID，回退时间戳+随机串） */
function generateId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

/** 获取或生成 session_id：优先复用 tracker 的会话（内存单例，最可靠）。
 *
 * 强保证链路：
 *   1) getTracker().getSessionId() —— tracker 已初始化时直接复用其内存中的 sessionId
 *   2) sessionStorage 的 tracker key —— tracker 未导出但已初始化过（同 tab）
 *   3) sessionStorage 自有 key —— tracker 完全未初始化时的兜底
 * 兜底写入时统一写到 tracker 的 key，确保 behavior_log 与 rrweb 即使在
 * tracker 后初始化的情况下也能读到同一个 session_id，保证两条链路可串联。
 */
function resolveSessionId(): string {
  const tracker = getTracker();
  if (tracker) {
    const sid = tracker.getSessionId();
    if (sid) return sid;
  }
  if (typeof window !== 'undefined' && window.sessionStorage) {
    const fromTracker = window.sessionStorage.getItem('__tracker_session_id__');
    if (fromTracker) return fromTracker;
    // 自有 key 兜底；同时写到 tracker key，保证后续 tracker 初始化时复用同一个 id
    let sid = window.sessionStorage.getItem(SESSION_KEY);
    if (!sid) {
      sid = generateId();
      window.sessionStorage.setItem(SESSION_KEY, sid);
    }
    // 尽力写回 tracker key（若 tracker 之后初始化，会读到这个值实现串联）
    try {
      window.sessionStorage.setItem('__tracker_session_id__', sid);
    } catch {
      /* sessionStorage 写入失败（隐私模式/配额）忽略，不影响主流程 */
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
  // error-triggered 待机态：不上报（缓冲继续滚动，等错误激活）
  if (!shouldFlush()) return;

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

/** 裁剪队列到上限（保留最新事件：rrweb 回放场景下新事件价值更高） */
function trimQueue(): void {
  if (eventQueue.length > MAX_QUEUE_SIZE) {
    eventQueue = eventQueue.slice(-MAX_QUEUE_SIZE);
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

/** 判断当前是否应 flush 上报。
 *
 * - always 模式：始终 flush
 * - error-triggered 模式：仅在被错误激活且窗口未过期时 flush
 */
function shouldFlush(): boolean {
  if (recordingMode === 'always') return true;
  if (recordingMode === 'error-triggered') {
    // 窗口过期：回到待机，清除激活态
    if (errorTriggered && Date.now() > errorWindowEnd) {
      errorTriggered = false;
    }
    return errorTriggered;
  }
  return false;
}

/** 错误触发：激活 error-triggered 模式的上报窗口。
 *
 * 由 window 'error' / 'unhandledrejection' 事件调用。激活后：
 * - 保留环形缓冲中已有的错误现场事件（trimQueue 不动）
 * - 启动 ERROR_TRIGGER_WINDOW 窗口，窗口内正常 flush 上报
 * - 窗口过期后自动回到待机（缓冲继续滚动，但不上报）
 */
function triggerOnError(): void {
  if (recordingMode !== 'error-triggered') return;
  if (!errorTriggered) {
    errorTriggered = true;
    if (debug) {
      // eslint-disable-next-line no-console
      console.log('[SessionRecorder] error-triggered 激活，开始上报录制');
    }
    // 立即 flush 一次，把错误发生前的现场事件发出去
    flush().catch(() => {});
  }
  // 续期：每次新错误都重置窗口
  errorWindowEnd = Date.now() + ERROR_TRIGGER_WINDOW;
}

/**
 * 初始化会话录制器。
 *
 * 必须在客户端（document 可用）调用；非浏览器环境直接 no-op。
 *
 * @param options.mode 录制模式，默认 'disabled'。
 *   - 'always'：全量录制（dev 环境），开销大
 *   - 'error-triggered'（生产推荐）：持续录进环形缓冲，捕获到 JS 错误
 *     后才激活上报，持续 30s 窗口。生产环境只录出错会话，开销可控。
 *   - 'disabled'：不录制
 * @param options.enabled 向后兼容：true 等价于 mode='always'，
 *   false 等价于 mode='disabled'。若同时提供 mode，以 mode 为准。
 */
export function initSessionRecorder(
  options?: { mode?: RecordingMode; enabled?: boolean },
): void {
  // 仅在浏览器环境运行
  if (typeof document === 'undefined' || typeof window === 'undefined') {
    return;
  }

  // 解析模式：优先 mode，回退 enabled（向后兼容）
  let mode: RecordingMode = options?.mode ?? 'disabled';
  if (options?.mode === undefined && options?.enabled !== undefined) {
    mode = options.enabled ? 'always' : 'disabled';
  }
  if (mode === 'disabled') {
    return;
  }

  if (recording) {
    if (debug) {
      // eslint-disable-next-line no-console
      console.warn('[SessionRecorder] already running, skip');
    }
    return;
  }

  recordingMode = mode;
  sessionId = resolveSessionId();
  lastPagePath = getPagePath();
  sequence = 0;
  errorTriggered = false;
  errorWindowEnd = 0;

  try {
    const stop = record<RRWebEvent>({
      emit(event) {
        if (!event) return;
        eventQueue.push(event);
        trimQueue();
        // 达到批量阈值立即 flush（error-triggered 模式由 shouldFlush 决定是否真发）
        if (eventQueue.length >= BATCH_SIZE && shouldFlush()) {
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

  // error-triggered 模式：注册全局错误监听，捕获到错误即激活上报窗口
  // （always 模式无需监听，始终上报）
  const onError = (event: ErrorEvent): void => {
    // 忽略资源加载错误（img/script/css），与 tracker.initErrorCapture 一致
    if (event.target && (event.target as HTMLElement).tagName) return;
    triggerOnError();
  };
  const onRejection = (event: PromiseRejectionEvent): void => {
    triggerOnError();
  };
  if (recordingMode === 'error-triggered') {
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onRejection);
  }

  // 页面卸载 / 切后台兜底 flush（与 tracker.ts 一致）
  // 注意：error-triggered 待机态下若队列非空，卸载时也尝试 flush——
  // 但 shouldFlush 会拦截，避免无意义上报。仅在激活态生效。
  const onUnload = () => {
    if (shouldFlush()) flush(true).catch(() => {});
  };
  const onVisibility = () => {
    if (document.visibilityState === 'hidden' && shouldFlush()) {
      flush(true).catch(() => {});
    }
  };
  window.addEventListener('beforeunload', onUnload);
  window.addEventListener('pagehide', onUnload);
  document.addEventListener('visibilitychange', onVisibility);

  // 记录停止时移除监听
  const originalStop = stopFn;
  stopFn = () => {
    window.removeEventListener('error', onError);
    window.removeEventListener('unhandledrejection', onRejection);
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
    console.log(
      `[SessionRecorder] started (mode=${recordingMode}), sessionId:`,
      sessionId,
    );
  }
}

/** 停止录制并清理（含定时器、监听、最后一批 flush） */
export function stopSessionRecorder(): void {
  if (!recording) return;
  // 停止时强制上报剩余缓冲（即使 error-triggered 待机态，停止时也尝试发一次，
  // 避免待机缓冲中的潜在有用数据丢失——失败也无所谓，尽力而为）
  const wasActive = recordingMode === 'always' || errorTriggered;
  stopFlushTimer();
  if (typeof stopFn === 'function') {
    stopFn();
    stopFn = null;
  }
  recording = false;
  recordingMode = 'disabled';
  errorTriggered = false;
  errorWindowEnd = 0;
  // 仅在激活态或有数据时尝试 flush（待机态无意义上报）
  if (wasActive) {
    flush(true).catch(() => {});
  }
}

/** 强制立即 flush（异步，用于手动触发或测试） */
export async function forceFlush(): Promise<void> {
  await flush(false);
}
