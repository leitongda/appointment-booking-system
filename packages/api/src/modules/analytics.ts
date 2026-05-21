import { request } from '../request';

// ========== 类型定义 ==========

export interface BehaviorLog {
  id: string;
  platform: string;
  sessionId: string;
  eventType: string;
  pagePath?: string;
  elementId?: string;
  elementText?: string;
  searchKeyword?: string;
  duration?: number;
  referrer?: string;
  deviceType?: string;
  browser?: string;
  os?: string;
  ip?: string;
  extraData?: string;
  createdAt: string;
}

export interface BehaviorLogListParams {
  platform?: string;
  eventType?: string;
  pagePath?: string;
  startTime?: string;
  endTime?: string;
  page?: number;
  pageSize?: number;
}

export interface PageViewItem {
  pagePath: string;
  viewCount: number;
}

export interface ClickElementItem {
  elementId: string;
  clickCount: number;
}

export interface SearchKeywordItem {
  searchKeyword: string;
  searchCount: number;
}

export interface DailyBehaviorItem {
  date: string;
  pv: number;
  uv: number;
  clicks: number;
  searches: number;
}

export interface BehaviorOverview {
  totalPv: number;
  totalUv: number;
  totalClicks: number;
  totalSearches: number;
  avgDuration: number;
  topPages: PageViewItem[];
  topClickElements: ClickElementItem[];
  topSearchKeywords: SearchKeywordItem[];
  dailyBreakdown: DailyBehaviorItem[];
}

export interface DailyActivityItem {
  date: string;
  dau: number;
  totalSessions: number;
  newUsers: number;
}

export interface TenantActivity {
  currentDau: number;
  currentWau: number;
  currentMau: number;
  dailyBreakdown: DailyActivityItem[];
}

// ========== API ==========

const PREFIX = '/analytics';

export const analyticsApi = {
  // 获取行为日志列表
  getLogs: (params?: BehaviorLogListParams): Promise<{ data: BehaviorLog[]; total: number; page: number; pageSize: number }> => {
    return request.get(`${PREFIX}/logs`, { params });
  },

  // 获取行为概览统计
  getOverview: (params?: { days?: number; platform?: string }): Promise<BehaviorOverview> => {
    return request.get(`${PREFIX}/overview`, { params });
  },

  // 获取租户活跃度统计
  getTenantActivity: (params?: { days?: number }): Promise<TenantActivity> => {
    return request.get(`${PREFIX}/tenant-activity`, { params });
  },
};
