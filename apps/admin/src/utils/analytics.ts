/**
 * 规则组预览埋点工具
 * 用于追踪用户在规则组管理中的预览行为
 */

import { getTracker } from '@hospital/shared';

// ==================== 埋点事件常量 ====================

/**
 * 规则组预览相关埋点事件
 */
export const RULE_PREVIEW_EVENTS = {
  // 实时预览
  LIVE_PREVIEW_OPEN: 'rule_preview:live:open',
  LIVE_PREVIEW_UPDATE: 'rule_preview:live:update',

  // 规则效果预览（Modal）
  MODAL_PREVIEW_OPEN: 'rule_preview:modal:open',
  MODAL_PREVIEW_START: 'rule_preview:modal:start',
  MODAL_PREVIEW_SUCCESS: 'rule_preview:modal:success',
  MODAL_PREVIEW_FAIL: 'rule_preview:modal:fail',

  // 快速查看（Drawer）
  DRAWER_PREVIEW_OPEN: 'rule_preview:drawer:open',
  DRAWER_PREVIEW_CLOSE: 'rule_preview:drawer:close',

  // 编辑行为
  EDIT_BEFORE_PREVIEW: 'rule_preview:edit:before',
  EDIT_AFTER_PREVIEW: 'rule_preview:edit:after',
  EDIT_EXIT_TAB: 'rule_preview:edit:exit_tab',
  EDIT_SAVE: 'rule_preview:edit:save',
  EDIT_CANCEL: 'rule_preview:edit:cancel',
} as const;

/**
 * 预览类型
 */
export type PreviewType = 'live' | 'modal' | 'drawer';

/**
 * 编辑页 Tab 类型
 */
export type EditTabType = 'basic' | 'time' | 'windows' | 'booking' | 'checkin' | 'capacity';

// ==================== 埋点数据接口 ====================

/**
 * 基础埋点数据
 */
interface BasePreviewData {
  ruleSetId?: string;
  ruleSetName?: string;
  timestamp: number;
}

/**
 * 实时预览埋点数据
 */
export interface LivePreviewData extends BasePreviewData {
  updateCount?: number;
  hasWindows?: boolean;
  hasShiftTypes?: boolean;
}

/**
 * Modal 预览埋点数据
 */
export interface ModalPreviewData extends BasePreviewData {
  shiftTypeId?: string;
  scheduleDate?: string;
  hasCurrentTime?: boolean;
  previewDuration?: number;
}

/**
 * Drawer 预览埋点数据
 */
export interface DrawerPreviewData extends BasePreviewData {
  viewDuration?: number;
}

/**
 * 编辑行为埋点数据
 */
export interface EditBehaviorData extends BasePreviewData {
  tab: EditTabType;
  changedFields?: string[];
  hasWindows?: boolean;
  isPresetApplied?: boolean;
}

// ==================== 埋点函数 ====================

/**
 * 追踪实时预览打开
 */
export function trackLivePreviewOpen(data: LivePreviewData): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.LIVE_PREVIEW_OPEN, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    hasWindows: data.hasWindows,
    hasShiftTypes: data.hasShiftTypes,
    timestamp: data.timestamp,
  });
}

/**
 * 追踪实时预览更新（节流，避免过于频繁）
 */
let livePreviewUpdateTimer: ReturnType<typeof setTimeout> | null = null;
let livePreviewUpdateCount = 0;

export function trackLivePreviewUpdate(data: LivePreviewData): void {
  const tracker = getTracker();
  if (!tracker) return;

  livePreviewUpdateCount++;

  // 节流：每 3 秒最多上报一次
  if (livePreviewUpdateTimer) return;

  livePreviewUpdateTimer = setTimeout(() => {
    tracker.trackEvent(RULE_PREVIEW_EVENTS.LIVE_PREVIEW_UPDATE, {
      ruleSetId: data.ruleSetId,
      ruleSetName: data.ruleSetName,
      updateCount: livePreviewUpdateCount,
      timestamp: data.timestamp,
    });

    livePreviewUpdateCount = 0;
    livePreviewUpdateTimer = null;
  }, 3000);
}

/**
 * 追踪 Modal 预览打开
 */
export function trackModalPreviewOpen(data: ModalPreviewData): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.MODAL_PREVIEW_OPEN, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    timestamp: data.timestamp,
  });
}

/**
 * 追踪 Modal 预览开始
 */
export function trackModalPreviewStart(data: ModalPreviewData): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.MODAL_PREVIEW_START, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    shiftTypeId: data.shiftTypeId,
    scheduleDate: data.scheduleDate,
    hasCurrentTime: data.hasCurrentTime,
    timestamp: data.timestamp,
  });
}

/**
 * 追踪 Modal 预览成功
 */
export function trackModalPreviewSuccess(data: ModalPreviewData): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.MODAL_PREVIEW_SUCCESS, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    previewDuration: data.previewDuration,
    timestamp: data.timestamp,
  });
}

/**
 * 追踪 Modal 预览失败
 */
export function trackModalPreviewFail(data: ModalPreviewData & { error?: string }): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.MODAL_PREVIEW_FAIL, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    error: data.error,
    timestamp: data.timestamp,
  });
}

/**
 * 追踪 Drawer 预览打开
 */
export function trackDrawerPreviewOpen(data: DrawerPreviewData): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.DRAWER_PREVIEW_OPEN, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    timestamp: data.timestamp,
  });
}

/**
 * 追踪 Drawer 预览关闭
 */
export function trackDrawerPreviewClose(data: DrawerPreviewData): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.DRAWER_PREVIEW_CLOSE, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    viewDuration: data.viewDuration,
    timestamp: data.timestamp,
  });
}

/**
 * 追踪预览前的编辑状态
 */
export function trackEditBeforePreview(data: EditBehaviorData): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.EDIT_BEFORE_PREVIEW, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    tab: data.tab,
    changedFields: data.changedFields,
    hasWindows: data.hasWindows,
    isPresetApplied: data.isPresetApplied,
    timestamp: data.timestamp,
  });
}

/**
 * 追踪预览后的编辑状态
 */
export function trackEditAfterPreview(data: EditBehaviorData): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.EDIT_AFTER_PREVIEW, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    tab: data.tab,
    changedFields: data.changedFields,
    hasWindows: data.hasWindows,
    timestamp: data.timestamp,
  });
}

/**
 * 追踪编辑页退出（通过 Tab 切换）
 */
export function trackEditExitTab(data: EditBehaviorData): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.EDIT_EXIT_TAB, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    tab: data.tab,
    timestamp: data.timestamp,
  });
}

/**
 * 追踪编辑保存
 */
export function trackEditSave(data: EditBehaviorData): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.EDIT_SAVE, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    tab: data.tab,
    hasWindows: data.hasWindows,
    timestamp: data.timestamp,
  });
}

/**
 * 追踪编辑取消
 */
export function trackEditCancel(data: EditBehaviorData): void {
  const tracker = getTracker();
  if (!tracker) return;

  tracker.trackEvent(RULE_PREVIEW_EVENTS.EDIT_CANCEL, {
    ruleSetId: data.ruleSetId,
    ruleSetName: data.ruleSetName,
    tab: data.tab,
    timestamp: data.timestamp,
  });
}

// ==================== 辅助函数 ====================

/**
 * 获取当前时间戳
 */
export function getTimestamp(): number {
  return Date.now();
}

/**
 * 比较两个对象是否有差异
 */
export function hasChanged(obj1: any, obj2: any): boolean {
  return JSON.stringify(obj1) !== JSON.stringify(obj2);
}

/**
 * 获取变化的字段列表
 */
export function getChangedFields(obj1: any, obj2: any): string[] {
  const changed: string[] = [];

  const compare = (o1: any, o2: any, prefix = ''): void => {
    const keys1 = Object.keys(o1 || {});
    const keys2 = Object.keys(o2 || {});
    const allKeys = Array.from(new Set([...keys1, ...keys2]));

    allKeys.forEach((key) => {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      const v1 = o1?.[key];
      const v2 = o2?.[key];

      if (typeof v1 === 'object' && typeof v2 === 'object' && v1 !== null && v2 !== null) {
        compare(v1, v2, fullKey);
      } else if (v1 !== v2) {
        changed.push(fullKey);
      }
    });
  };

  compare(obj1, obj2);
  return changed;
}
