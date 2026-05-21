import request from '../request';
import type { PageResult } from '@hospital/shared';

export interface SupportTicket {
  id: string;
  tenantId?: string;
  title?: string;
  description?: string;
  type?: string; // suggestion/complaint/bug/other
  status?: string; // pending/processing/resolved/closed
  priority?: string; // low/medium/high/urgent
  creatorId?: string;
  creatorType?: string; // user/admin
  assigneeId?: string;
  contactInfo?: string;
  attachments?: string[];
  resolution?: string;
  closedAt?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface SupportTicketCreateData {
  title: string;
  description: string;
  type?: string;
  priority?: string;
  contactInfo?: string;
  attachments?: string[];
}

export interface SupportTicketUpdateData {
  title?: string;
  description?: string;
  type?: string;
  priority?: string;
  contactInfo?: string;
  attachments?: string[];
  resolution?: string;
}

export interface SupportTicketListParams {
  status?: string;
  type?: string;
  priority?: string;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface SupportTicketStatistics {
  total: number;
  pending: number;
  processing: number;
  resolved: number;
  closed: number;
}

export const supportTicketApi = {
  getList: (params?: SupportTicketListParams): Promise<PageResult<SupportTicket>> => {
    return request.get('/support-tickets', { params });
  },

  getDetail: (id: string): Promise<SupportTicket> => {
    return request.get(`/support-tickets/${id}`);
  },

  create: (data: SupportTicketCreateData): Promise<SupportTicket> => {
    return request.post('/support-tickets', data);
  },

  update: (id: string, data: SupportTicketUpdateData): Promise<SupportTicket> => {
    return request.put(`/support-tickets/${id}`, data);
  },

  assign: (id: string, assigneeId: string): Promise<SupportTicket> => {
    return request.post(`/support-tickets/${id}/assign`, { assigneeId });
  },

  resolve: (id: string, resolution?: string): Promise<SupportTicket> => {
    return request.post(`/support-tickets/${id}/resolve`, { resolution });
  },

  close: (id: string, resolution?: string): Promise<SupportTicket> => {
    return request.post(`/support-tickets/${id}/close`, { resolution });
  },

  reopen: (id: string): Promise<SupportTicket> => {
    return request.post(`/support-tickets/${id}/reopen`);
  },

  getStatistics: (): Promise<SupportTicketStatistics> => {
    return request.get('/support-tickets/statistics');
  },
};
