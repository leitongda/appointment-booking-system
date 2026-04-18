/**
 * 租户暂停/欠费跨 Tab 状态同步
 *
 * 模式与 authFeedback.ts 对称：
 * - 通过 localStorage 写入/读取标记，使同一浏览器的多个标签页同步跳转
 * - 写入触发 crossTabSync 的 storage 事件
 */

import type { TenantSuspendReason } from './tenantStatus';

const STORAGE_KEY = 'hospital_tenant_suspended';
const DEBOUNCE_MS = 300;

type SuspendListener = (reason: TenantSuspendReason) => void;

let listener: SuspendListener | null = null;
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

// ==================== 公开 API ====================

/** 标记租户已暂停（在响应拦截器中调用） */
export function markTenantSuspended(reason: TenantSuspendReason): void {
  if (typeof window === 'undefined') return;

  const payload = JSON.stringify({ reason, ts: Date.now() });
  localStorage.setItem(STORAGE_KEY, payload);
  // 当前 Tab 不触发 storage 事件，手动通知
  if (listener) {
    listener(reason);
  }
}

/** 清除暂停标记（续费恢复后调用） */
export function clearTenantSuspended(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(STORAGE_KEY);
}

/** 获取当前暂停原因（页面初始化时读取） */
export function getTenantSuspendedReason(): TenantSuspendReason | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const data = JSON.parse(raw);
    return data.reason ?? null;
  } catch {
    return null;
  }
}

/**
 * 订阅跨 Tab 的租户暂停事件
 *
 * @returns unsubscribe 函数
 */
export function subscribeTenantSuspended(cb: SuspendListener): () => void {
  listener = cb;

  const handler = (e: StorageEvent) => {
    if (e.key !== STORAGE_KEY) return;
    if (!e.newValue) return;
    try {
      const data = JSON.parse(e.newValue);
      const reason: TenantSuspendReason | undefined = data.reason;
      if (reason && listener) {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          debounceTimer = null;
          listener!(reason);
        }, DEBOUNCE_MS);
      }
    } catch { /* ignore */ }
  };

  if (typeof window !== 'undefined') {
    window.addEventListener('storage', handler);
  }

  return () => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('storage', handler);
    }
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
    listener = null;
  };
}
