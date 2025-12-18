/**
 * 用户行为分析类型定义
 */

/** 平台类型 */
export type Platform = 'admin' | 'h5' | 'miniapp';

/** 事件类型 */
export type EventType = 'page_view' | 'page_leave' | 'click' | 'search' | 'custom';

/** 追踪配置 */
export interface TrackerConfig {
  /** API 基础地址 */
  apiBaseUrl: string;
  /** 平台类型 */
  platform: Platform;
  /** 是否启用 */
  enabled?: boolean;
  /** 是否在开发环境启用 */
  enableInDev?: boolean;
  /** 批量上报阈值 */
  batchSize?: number;
  /** 批量上报间隔（毫秒） */
  batchInterval?: number;
  /** 调试模式 */
  debug?: boolean;
}

/** 事件数据 */
export interface TrackEvent {
  platform: Platform;
  session_id?: string;
  event_type: EventType;
  page_path?: string;
  page_title?: string;
  element_id?: string;
  element_text?: string;
  search_keyword?: string;
  event_name?: string;
  duration?: number;
  referrer?: string;
  extra_data?: Record<string, any>;
}

/** 页面访问统计 */
export interface PageViewStats {
  page_path: string;
  page_title?: string;
  view_count: number;
  unique_users: number;
}

/** 点击统计 */
export interface ClickStats {
  element_id?: string;
  element_text?: string;
  page_path?: string;
  click_count: number;
}

/** 搜索关键词统计 */
export interface SearchKeywordStats {
  keyword: string;
  search_count: number;
}

/** 每日统计 */
export interface DailyStats {
  date: string;
  page_views: number;
  unique_users: number;
  clicks: number;
  searches: number;
}

/** 行为概览 */
export interface BehaviorOverview {
  total_page_views: number;
  total_unique_users: number;
  total_clicks: number;
  total_searches: number;
  avg_duration?: number;
  top_pages: PageViewStats[];
  top_clicks: ClickStats[];
  top_keywords: SearchKeywordStats[];
  daily_stats: DailyStats[];
}

