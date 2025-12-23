/**
 * 用户行为追踪器
 * 支持页面访问、点击、搜索等事件追踪
 */

import type { TrackerConfig, TrackEvent, Platform, EventType } from './types';

// 声明微信小程序全局对象类型
declare const wx: {
  getStorageSync: (key: string) => string;
  setStorageSync: (key: string, value: string) => void;
  request: (options: {
    url: string;
    method: string;
    header: Record<string, string>;
    data: any;
  }) => void;
} | undefined;

/** 生成唯一 ID */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

/** 生成会话 ID */
function generateSessionId(): string {
  const key = '__tracker_session_id__';
  
  // 浏览器环境
  if (typeof window !== 'undefined' && window.sessionStorage) {
    let sessionId = sessionStorage.getItem(key);
    if (!sessionId) {
      sessionId = generateId();
      sessionStorage.setItem(key, sessionId);
    }
    return sessionId;
  }
  
  // 小程序环境
  if (typeof wx !== 'undefined' && wx.getStorageSync) {
    let sessionId = wx.getStorageSync(key);
    if (!sessionId) {
      sessionId = generateId();
      wx.setStorageSync(key, sessionId);
    }
    return sessionId;
  }
  
  return generateId();
}

/** 获取页面标题 */
function getPageTitle(): string {
  if (typeof document !== 'undefined') {
    return document.title || '';
  }
  return '';
}

/** 获取来源页面 */
function getReferrer(): string {
  if (typeof document !== 'undefined') {
    return document.referrer || '';
  }
  return '';
}

/**
 * 用户行为追踪器
 */
/** 默认的 Analytics API 路径 */
const DEFAULT_ANALYTICS_PATH = '/api/v1/analytics/batch';

export class Tracker {
  private config: Required<TrackerConfig>;
  private sessionId: string;
  private eventQueue: TrackEvent[] = [];
  private flushTimer: any = null;
  private pageEnterTime: number = 0;
  private currentPagePath: string = '';

  constructor(config: TrackerConfig) {
    this.config = {
      enabled: true,
      enableInDev: false,
      batchSize: 10,
      batchInterval: 5000,
      debug: false,
      apiPath: DEFAULT_ANALYTICS_PATH,
      ...config,
    };
    
    this.sessionId = generateSessionId();
    
    // 启动定时上报
    this.startFlushTimer();
    
    // 页面卸载时上报剩余数据
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => {
        this.flush(true);
      });
      window.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
          this.flush(true);
        }
      });
    }
  }

  /** 是否启用追踪 */
  private isEnabled(): boolean {
    if (!this.config.enabled) return false;
    
    // 开发环境检查
    if (typeof process !== 'undefined' && process.env?.NODE_ENV === 'development') {
      return this.config.enableInDev;
    }
    
    return true;
  }

  /** 启动定时上报 */
  private startFlushTimer(): void {
    if (this.flushTimer) return;
    
    this.flushTimer = setInterval(() => {
      this.flush();
    }, this.config.batchInterval);
  }

  /** 停止定时上报 */
  private stopFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
  }

  /** 添加事件到队列 */
  private addEvent(event: Partial<TrackEvent>): void {
    if (!this.isEnabled()) return;

    const fullEvent: TrackEvent = {
      platform: this.config.platform,
      session_id: this.sessionId,
      event_type: 'custom',
      ...event,
    };

    if (this.config.debug) {
      console.log('[Tracker] Event:', fullEvent);
    }

    this.eventQueue.push(fullEvent);

    // 达到批量阈值时立即上报
    if (this.eventQueue.length >= this.config.batchSize) {
      this.flush();
    }
  }

  /** 上报事件 */
  private async flush(sync = false): Promise<void> {
    if (this.eventQueue.length === 0) return;

    const events = [...this.eventQueue];
    this.eventQueue = [];

    // 使用配置的 apiPath，支持动态 API 路径
    const url = `${this.config.apiBaseUrl}${this.config.apiPath}`;
    const body = JSON.stringify({ events });

    if (this.config.debug) {
      console.log('[Tracker] Flush events:', events.length);
    }

    try {
      // 使用 sendBeacon 或 fetch
      if (sync && typeof navigator !== 'undefined' && navigator.sendBeacon) {
        navigator.sendBeacon(url, body);
      } else if (typeof fetch !== 'undefined') {
        await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body,
          keepalive: true,
        });
      } else if (typeof wx !== 'undefined' && wx.request) {
        // 小程序环境
        wx.request({
          url,
          method: 'POST',
          header: { 'Content-Type': 'application/json' },
          data: { events },
        });
      }
    } catch (error) {
      if (this.config.debug) {
        console.error('[Tracker] Flush error:', error);
      }
      // 上报失败时将事件放回队列
      this.eventQueue.unshift(...events);
    }
  }

  // ========== 公共 API ==========

  /**
   * 追踪页面访问
   * @param path 页面路径
   * @param title 页面标题
   */
  trackPageView(path?: string, title?: string): void {
    // 如果有上一个页面，记录离开事件
    if (this.currentPagePath && this.pageEnterTime > 0) {
      const duration = Date.now() - this.pageEnterTime;
      this.addEvent({
        event_type: 'page_leave',
        page_path: this.currentPagePath,
        duration,
      });
    }

    // 记录当前页面
    const pagePath = path || (typeof window !== 'undefined' ? window.location.pathname : '');
    const pageTitle = title || getPageTitle();
    
    this.currentPagePath = pagePath;
    this.pageEnterTime = Date.now();

    this.addEvent({
      event_type: 'page_view',
      page_path: pagePath,
      page_title: pageTitle,
      referrer: getReferrer(),
    });
  }

  /**
   * 追踪页面离开
   * @param path 页面路径
   * @param duration 停留时长（毫秒）
   */
  trackPageLeave(path?: string, duration?: number): void {
    const pagePath = path || this.currentPagePath;
    const dur = duration || (this.pageEnterTime > 0 ? Date.now() - this.pageEnterTime : undefined);

    this.addEvent({
      event_type: 'page_leave',
      page_path: pagePath,
      duration: dur,
    });

    this.currentPagePath = '';
    this.pageEnterTime = 0;
  }

  /**
   * 追踪点击事件
   * @param elementId 元素 ID
   * @param elementText 元素文本
   * @param extraData 额外数据
   */
  trackClick(elementId?: string, elementText?: string, extraData?: Record<string, any>): void {
    const pagePath = typeof window !== 'undefined' ? window.location.pathname : '';
    
    this.addEvent({
      event_type: 'click',
      page_path: pagePath,
      element_id: elementId,
      element_text: elementText,
      extra_data: extraData,
    });
  }

  /**
   * 追踪搜索事件
   * @param keyword 搜索关键词
   * @param extraData 额外数据
   */
  trackSearch(keyword: string, extraData?: Record<string, any>): void {
    const pagePath = typeof window !== 'undefined' ? window.location.pathname : '';
    
    this.addEvent({
      event_type: 'search',
      page_path: pagePath,
      search_keyword: keyword,
      extra_data: extraData,
    });
  }

  /**
   * 追踪自定义事件
   * @param eventName 事件名称
   * @param data 事件数据
   */
  trackEvent(eventName: string, data?: Record<string, any>): void {
    const pagePath = typeof window !== 'undefined' ? window.location.pathname : '';
    
    this.addEvent({
      event_type: 'custom',
      page_path: pagePath,
      event_name: eventName,
      extra_data: data,
    });
  }

  /**
   * 立即上报所有事件
   */
  async forceFlush(): Promise<void> {
    await this.flush();
  }

  /**
   * 销毁追踪器
   */
  destroy(): void {
    this.stopFlushTimer();
    this.flush(true);
  }

  /**
   * 设置是否启用
   */
  setEnabled(enabled: boolean): void {
    this.config.enabled = enabled;
  }

  /**
   * 获取会话 ID
   */
  getSessionId(): string {
    return this.sessionId;
  }
}

/** 全局追踪器实例 */
let globalTracker: Tracker | null = null;

/**
 * 初始化追踪器
 */
export function initTracker(config: TrackerConfig): Tracker {
  if (globalTracker) {
    globalTracker.destroy();
  }
  globalTracker = new Tracker(config);
  return globalTracker;
}

/**
 * 获取追踪器实例
 */
export function getTracker(): Tracker | null {
  return globalTracker;
}

/**
 * 销毁追踪器
 */
export function destroyTracker(): void {
  if (globalTracker) {
    globalTracker.destroy();
    globalTracker = null;
  }
}

