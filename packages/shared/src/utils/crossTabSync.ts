/**
 * 跨 Tab 状态同步模块
 *
 * 通过监听浏览器原生 `storage` 事件，检测其他 Tab 对 localStorage 的变更，
 * 实现 token、租户、门店等关键状态的跨 Tab 同步。
 *
 * 注意：`storage` 事件仅在 **其他 Tab** 修改 localStorage 时触发，
 * 同一 Tab 内的修改不会触发此事件。
 */

// ==================== 类型定义 ====================

export type CrossTabEvent =
  | { type: 'auth-change'; action: 'login' | 'logout' | 'switch-user'; newUserId?: string }
  | { type: 'tenant-change'; newTenantId: string; newTenantName?: string }
  | { type: 'store-change'; newStoreId: string; newStoreName?: string };

type EventHandler = (event: CrossTabEvent) => void;

// ==================== 常量 ====================

/** 需要监听的 localStorage keys */
const WATCHED_KEYS = new Set([
  'hospital_token',
  'hospital_current_tenant_id',
  'currentStore',
]);

/** 防抖间隔（ms），同一事件在短时间内只触发一次回调 */
const DEBOUNCE_MS = 300;

// ==================== 内部状态 ====================

let handler: EventHandler | null = null;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;
let pendingEvent: CrossTabEvent | null = null;
/** 当前 token 中的用户 ID 快照，用于判断是否切换了用户 */
let currentUserIdSnapshot: string | null = null;

// ==================== JWT 解析工具 ====================

/**
 * 从 JWT token 中解析 payload（不验证签名，仅用于读取 sub 字段）
 */
function parseJwtSub(token: string): string | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    return payload.sub || null;
  } catch {
    return null;
  }
}

// ==================== 事件处理 ====================

function onStorageChange(event: StorageEvent): void {
  if (!handler) return;

  // 只关注我们监听的 key
  if (!event.key || !WATCHED_KEYS.has(event.key)) return;

  const newValue = event.newValue;
  const oldValue = event.oldValue;

  switch (event.key) {
    case 'hospital_token':
      handleTokenChange(newValue, oldValue);
      break;
    case 'hospital_current_tenant_id':
      handleTenantChange(newValue);
      break;
    case 'currentStore':
      handleStoreChange(newValue);
      break;
  }
}

function handleTokenChange(newValue: string | null, oldValue: string | null): void {
  if (!handler) return;

  const hadToken = !!oldValue;
  const hasToken = !!newValue;

  // token 被移除 → 登出
  if (hadToken && !hasToken) {
    emitEvent({ type: 'auth-change', action: 'logout' });
    currentUserIdSnapshot = null;
    return;
  }

  // 新 token 出现 → 登录或切换用户
  if (!hadToken && hasToken) {
    const newSub = parseJwtSub(newValue!);
    currentUserIdSnapshot = newSub;
    emitEvent({ type: 'auth-change', action: 'login', newUserId: newSub || undefined });
    return;
  }

  // token 变更 → 判断是同用户换 token 还是切换用户
  if (hadToken && hasToken) {
    const oldSub = parseJwtSub(oldValue!);
    const newSub = parseJwtSub(newValue!);

    if (oldSub && newSub && oldSub !== newSub) {
      // 不同用户 → 切换用户
      currentUserIdSnapshot = newSub;
      emitEvent({ type: 'auth-change', action: 'switch-user', newUserId: newSub });
    }
    // 同用户（sub 相同或无法解析）→ 静默忽略，可能是 token 刷新
  }
}

function handleTenantChange(newValue: string | null): void {
  if (!handler) return;

  if (newValue) {
    emitEvent({ type: 'tenant-change', newTenantId: newValue });
  } else {
    // 租户被清空（登出或超管操作），也通知
    emitEvent({ type: 'tenant-change', newTenantId: '' });
  }
}

function handleStoreChange(newValue: string | null): void {
  if (!handler) return;

  if (newValue) {
    try {
      const store = JSON.parse(newValue);
      emitEvent({
        type: 'store-change',
        newStoreId: store.id || '',
        newStoreName: store.name || '',
      });
    } catch {
      // JSON 解析失败，用原始值
      emitEvent({ type: 'store-change', newStoreId: newValue, newStoreName: '' });
    }
  } else {
    // 门店被清空
    emitEvent({ type: 'store-change', newStoreId: '', newStoreName: '' });
  }
}

/**
 * 带防抖的事件发射，避免短时间内多个 storage 事件连续触发多次弹框
 */
function emitEvent(event: CrossTabEvent): void {
  pendingEvent = event;

  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }

  debounceTimer = setTimeout(() => {
    debounceTimer = null;
    if (handler && pendingEvent) {
      handler(pendingEvent);
      pendingEvent = null;
    }
  }, DEBOUNCE_MS);
}

// ==================== 公开 API ====================

/**
 * 初始化跨 Tab 状态同步
 *
 * @param handler 事件回调，接收 CrossTabEvent
 * @returns unsubscribe 函数，调用后停止监听
 */
export function initCrossTabSync(eventHandler: EventHandler): () => void {
  if (handler) {
    // 已经初始化过，先清理旧的
    destroyCrossTabSync();
  }

  handler = eventHandler;

  // 初始化用户 ID 快照
  if (typeof window !== 'undefined') {
    const currentToken = localStorage.getItem('hospital_token');
    if (currentToken) {
      currentUserIdSnapshot = parseJwtSub(currentToken);
    }
  }

  // 绑定 storage 事件
  if (typeof window !== 'undefined') {
    window.addEventListener('storage', onStorageChange);
  }

  // 返回 unsubscribe 函数
  return () => {
    destroyCrossTabSync();
  };
}

/**
 * 销毁跨 Tab 状态同步
 */
export function destroyCrossTabSync(): void {
  if (typeof window !== 'undefined') {
    window.removeEventListener('storage', onStorageChange);
  }

  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }

  handler = null;
  pendingEvent = null;
  currentUserIdSnapshot = null;
}
