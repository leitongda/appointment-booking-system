/**
 * 租户/订阅状态工具
 *
 * 供多端复用的纯函数，不依赖任何框架或 store。
 */

export type TenantSuspendReason = 'overdue' | 'disabled' | 'trial_expired';

export interface TenantStatusInfo {
  status: number;                     // 0-禁用 1-正常 2-欠费 3-试用
  subscriptionPlanName?: string;
  subscriptionEndAt?: string | null;
  isSubscriptionActive: boolean;
  daysUntilExpiry?: number | null;
  contactPhone?: string;
}

export type BannerLevel = 'none' | 'warning' | 'critical';

/**
 * 根据租户状态推导顶栏 Banner 等级
 *
 * - none     : 正常，无需提示
 * - warning  : 订阅 ≤7 天到期（黄条）
 * - critical : 订阅 ≤1 天 / 已过期 / status != 1（红条）
 */
export function deriveTenantBannerLevel(t: TenantStatusInfo | null | undefined): BannerLevel {
  if (!t) return 'none';

  // 禁用 / 欠费 → 红
  if (t.status === 0 || t.status === 2) return 'critical';

  // 试用到期
  if (t.status === 3 && !t.isSubscriptionActive) return 'critical';

  // 正常状态 → 按天数
  if (t.daysUntilExpiry != null) {
    if (t.daysUntilExpiry <= 1) return 'critical';
    if (t.daysUntilExpiry <= 7) return 'warning';
  }

  // subscriptionEndAt 存在但已过期（定时任务尚未刷新 status 的窗口期）
  if (t.subscriptionEndAt && new Date(t.subscriptionEndAt) < new Date()) {
    return 'critical';
  }

  return 'none';
}

/** 租户是否处于"暂停服务"状态（前端应阻断写操作） */
export function isTenantSuspended(t: TenantStatusInfo | null | undefined): boolean {
  if (!t) return false;
  if (t.status === 0 || t.status === 2) return true;
  if (!t.isSubscriptionActive) return true;
  return false;
}

/** 租户是否应阻断前端写操作（与 isTenantSuspended 相同语义，语义别名） */
export function shouldBlockWrite(t: TenantStatusInfo | null | undefined): boolean {
  return isTenantSuspended(t);
}
