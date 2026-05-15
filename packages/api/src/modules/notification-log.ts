import request from '../request';
import type { PageResult, UsageStats, NotificationQuota, NotificationQuotaUpdate } from '@hospital/shared';

export interface NotificationLog {
  id: string;
  tenantId?: string;
  storeId?: string;
  userId?: string;
  userType?: string;
  channel: 'sms' | 'email' | 'in_app' | 'wechat';
  messageType?: string;
  title?: string;
  content?: string;
  status: 'pending' | 'sent' | 'failed' | 'permanently_failed';
  errorMessage?: string;
  recipient?: string;
  relatedId?: string;
  retryCount?: number;
  maxRetries?: number;
  nextRetryAt?: string;
  sentAt?: string;
  createdAt: string;
  extraData?: Record<string, any>;
}

export interface NotificationLogListParams {
  channel?: 'sms' | 'email' | 'in_app' | 'wechat';
  status?: 'pending' | 'sent' | 'failed' | 'permanently_failed';
  messageType?: string;
  userId?: string;
  storeId?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  pageSize?: number;
}

export interface NotificationLogStats {
  total: number;
  sent: number;
  failed: number;
  pending: number;
  failureRate: number;
  byChannel: Record<string, number>;
  byType: Record<string, number>;
}

export const notificationLogApi = {
  getList: (params: NotificationLogListParams): Promise<PageResult<NotificationLog>> => {
    return request.get('/notification-logs', {
      params: {
        channel: params.channel,
        status: params.status,
        message_type: params.messageType,
        user_id: params.userId,
        store_id: params.storeId,
        start_date: params.startDate,
        end_date: params.endDate,
        page: params.page,
        page_size: params.pageSize,
      },
    });
  },

  getStats: (params?: { storeId?: string; startDate?: string; endDate?: string }): Promise<NotificationLogStats> => {
    return request.get('/notification-logs/stats', {
      params: {
        store_id: params?.storeId,
        start_date: params?.startDate,
        end_date: params?.endDate,
      },
    });
  },

  getDetail: (id: string): Promise<NotificationLog> => {
    return request.get(`/notification-logs/${id}`);
  },

  retry: (id: string): Promise<{ message: string }> => {
    return request.post(`/notification-logs/${id}/retry`);
  },

  getUsageStats: (params?: { period?: string }): Promise<UsageStats> => {
    return request.get('/notification-logs/usage-stats', {
      params: { period: params?.period || 'month' },
    });
  },

  getQuota: (): Promise<NotificationQuota> => {
    return request.get('/notification-logs/quota');
  },

  updateQuota: (data: NotificationQuotaUpdate): Promise<NotificationQuota> => {
    return request.put('/notification-logs/quota', data);
  },
};
