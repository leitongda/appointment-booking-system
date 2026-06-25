/**
 * 会话回放 API 封装
 *
 * 对应后端路由前缀：/api/v1/session-events
 * - GET  /session-events            会话列表（按 session_id 聚合）
 * - GET  /session-events/{id}/replay 会话回放数据（presigned eventsUrl）
 * - GET  /session-events/heatmap    热力图坐标聚合查询
 *
 * 使用 @hospital/api 的 request（默认 axios 实例，请求拦截器自动注入
 * admin token 与 X-Tenant-ID，见 src/utils/request.ts）。
 */
import { request } from '@hospital/api';

/** 会话列表项（后端 SessionListResponse，camelCase） */
export interface SessionEventListItem {
  id: string;
  sessionId: string;
  actorId?: string | null;
  actorName?: string | null;
  pagePath?: string | null;
  viewportW?: number | null;
  viewportH?: number | null;
  eventCount: number;
  sequence: number;
  startedAt?: string | null;
  endedAt?: string | null;
  createdAt?: string | null;
}

/** 会话列表查询参数（对应 GET /session-events 的过滤项） */
export interface SessionEventListParams {
  platform?: string;
  actorId?: string;
  pagePath?: string;
  sessionId?: string;
  startTime?: string;
  endTime?: string;
  page?: number;
  pageSize?: number;
}

/** 分页响应（后端 PageResponse） */
export interface SessionEventPage {
  data: SessionEventListItem[];
  total: number;
  page: number;
  pageSize: number;
}

/** 单批次段（回放拼装用） */
export interface SessionSegment {
  segmentId: string;
  sequence: number;
  eventCount: number;
  eventsUrl?: string | null;
}

/** 会话回放数据响应 */
export interface SessionReplayData {
  sessionId: string;
  viewportW?: number | null;
  viewportH?: number | null;
  segments: SessionSegment[];
}

/** 热力图单点 */
export interface HeatmapPoint {
  xRatio: number;
  yRatio: number;
  weight: number;
}

/** 热力图查询响应 */
export interface HeatmapQueryResult {
  pagePath: string;
  viewportBucket?: string | null;
  eventType: string;
  points: HeatmapPoint[];
}

/** 热力图查询参数 */
export interface HeatmapQueryParams {
  pagePath: string;
  eventType?: 'click' | 'move';
  viewportBucket?: 'lg' | 'md' | 'sm';
  days?: number;
}

/** 会话回放 API */
export const sessionReplayApi = {
  /** 会话列表（按 session_id 聚合） */
  list: (params?: SessionEventListParams): Promise<SessionEventPage> => {
    return request.get('/session-events', { params });
  },

  /** 会话回放数据（按 sequence 排序的所有批次段） */
  getReplay: (sessionId: string): Promise<SessionReplayData> => {
    return request.get(`/session-events/${encodeURIComponent(sessionId)}/replay`);
  },

  /** 热力图坐标聚合查询 */
  getHeatmap: (params: HeatmapQueryParams): Promise<HeatmapQueryResult> => {
    return request.get('/session-events/heatmap', { params });
  },
};

export default sessionReplayApi;
