import request from '../request';
import type { PageResult } from '@hospital/shared';

// ========== 类型定义 ==========

export interface Freelancer {
  id: string;
  tenantId?: string;
  storeId?: string;
  name: string;
  phone?: string;
  accountName?: string;
  accountPlatform: string;
  accountType: string;
  status: number;
  accessToken?: string;
  remark?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface FreelancerCreateData {
  name: string;
  phone?: string;
  storeId?: string;
  accountName?: string;
  accountPlatform?: string;
  accountType?: string;
  status?: number;
  remark?: string;
}

export interface FreelancerUpdateData {
  name?: string;
  phone?: string;
  storeId?: string;
  accountName?: string;
  accountPlatform?: string;
  accountType?: string;
  status?: number;
  remark?: string;
}

export interface FreelanceTask {
  id: string;
  tenantId?: string;
  storeId?: string;
  freelancerId: string;
  title: string;
  contentUrl?: string;
  publishedAt?: string;
  status: string;
  isIndexed: boolean;
  likesCount: number;
  commentsCount: number;
  baseAmount: number;
  bonusAmount: number;
  likesBonusAmount: number;
  plannedBaseSettleAt?: string;
  plannedBonusSettleAt?: string;
  plannedLikesSettleAt?: string;
  remark?: string;
  createdAt?: string;
  updatedAt?: string;
  freelancerName?: string;
}

export interface FreelanceTaskCreateData {
  freelancerId: string;
  storeId?: string;
  title: string;
  contentUrl?: string;
  publishedAt?: string;
  remark?: string;
}

export interface FreelanceTaskUpdateData {
  title?: string;
  contentUrl?: string;
  publishedAt?: string;
  status?: string;
  isIndexed?: boolean;
  likesCount?: number;
  commentsCount?: number;
  bonusAmount?: number;
  remark?: string;
}

export interface FreelanceInteraction {
  id: string;
  taskId: string;
  interactionType: string;
  content?: string;
  amount: number;
  interactedAt?: string;
  createdAt?: string;
}

export interface FreelanceInteractionCreateData {
  taskId: string;
  interactionType: string;
  content?: string;
  interactedAt?: string;
}

export interface FreelanceSettlement {
  id: string;
  tenantId?: string;
  storeId?: string;
  freelancerId: string;
  settlementNo: string;
  periodStart?: string;
  periodEnd?: string;
  baseTotal: number;
  bonusTotal: number;
  likesBonusTotal: number;
  interactionTotal: number;
  totalAmount: number;
  taxAmount: number;
  actualAmount: number;
  status: string;
  confirmedAt?: string;
  confirmedBy?: string;
  paidAt?: string;
  rejectReason?: string;
  remark?: string;
  createdAt?: string;
  updatedAt?: string;
  freelancerName?: string;
  items?: FreelanceSettlementItem[];
}

export interface FreelanceSettlementItem {
  id: string;
  settlementId: string;
  itemType: string;
  taskId?: string;
  interactionId?: string;
  description?: string;
  amount: number;
  createdAt?: string;
}

export interface FreelanceListParams {
  name?: string;
  storeId?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

export interface FreelanceTaskListParams {
  freelancerId?: string;
  storeId?: string;
  status?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  pageSize?: number;
}

export interface FreelanceSettlementListParams {
  freelancerId?: string;
  storeId?: string;
  status?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  pageSize?: number;
}

// ========== API ==========

export const freelancerApi = {
  getList: (params?: FreelanceListParams): Promise<PageResult<Freelancer>> => {
    return request.get('/freelance-fees/freelancers', {
      params: {
        name: params?.name,
        store_id: params?.storeId,
        status: params?.status,
        page: params?.page,
        page_size: params?.pageSize,
      },
    });
  },

  getDetail: (id: string): Promise<Freelancer> => {
    return request.get(`/freelance-fees/freelancers/${id}`);
  },

  create: (data: FreelancerCreateData): Promise<Freelancer> => {
    return request.post('/freelance-fees/freelancers', {
      name: data.name,
      phone: data.phone,
      store_id: data.storeId,
      account_name: data.accountName,
      account_platform: data.accountPlatform,
      account_type: data.accountType,
      status: data.status,
      remark: data.remark,
    });
  },

  update: (id: string, data: FreelancerUpdateData): Promise<Freelancer> => {
    return request.put(`/freelance-fees/freelancers/${id}`, {
      name: data.name,
      phone: data.phone,
      store_id: data.storeId,
      account_name: data.accountName,
      account_platform: data.accountPlatform,
      account_type: data.accountType,
      status: data.status,
      remark: data.remark,
    });
  },

  delete: (id: string): Promise<void> => {
    return request.delete(`/freelance-fees/freelancers/${id}`);
  },
};

export const freelanceTaskApi = {
  getList: (params?: FreelanceTaskListParams): Promise<PageResult<FreelanceTask>> => {
    return request.get('/freelance-fees/tasks', {
      params: {
        freelancer_id: params?.freelancerId,
        store_id: params?.storeId,
        status: params?.status,
        start_date: params?.startDate,
        end_date: params?.endDate,
        page: params?.page,
        page_size: params?.pageSize,
      },
    });
  },

  getDetail: (id: string): Promise<FreelanceTask> => {
    return request.get(`/freelance-fees/tasks/${id}`);
  },

  create: (data: FreelanceTaskCreateData): Promise<FreelanceTask> => {
    return request.post('/freelance-fees/tasks', {
      freelancer_id: data.freelancerId,
      store_id: data.storeId,
      title: data.title,
      content_url: data.contentUrl,
      published_at: data.publishedAt,
      remark: data.remark,
    });
  },

  update: (id: string, data: FreelanceTaskUpdateData): Promise<FreelanceTask> => {
    return request.put(`/freelance-fees/tasks/${id}`, {
      title: data.title,
      content_url: data.contentUrl,
      published_at: data.publishedAt,
      status: data.status,
      is_indexed: data.isIndexed,
      likes_count: data.likesCount,
      comments_count: data.commentsCount,
      bonus_amount: data.bonusAmount,
      remark: data.remark,
    });
  },

  getInteractions: (taskId: string): Promise<FreelanceInteraction[]> => {
    return request.get(`/freelance-fees/tasks/${taskId}/interactions`);
  },

  addInteraction: (data: FreelanceInteractionCreateData): Promise<FreelanceInteraction> => {
    return request.post('/freelance-fees/interactions', {
      task_id: data.taskId,
      interaction_type: data.interactionType,
      content: data.content,
      interacted_at: data.interactedAt,
    });
  },
};

export const freelanceSettlementApi = {
  getList: (params?: FreelanceSettlementListParams): Promise<PageResult<FreelanceSettlement>> => {
    return request.get('/freelance-fees/settlements', {
      params: {
        freelancer_id: params?.freelancerId,
        store_id: params?.storeId,
        status: params?.status,
        start_date: params?.startDate,
        end_date: params?.endDate,
        page: params?.page,
        page_size: params?.pageSize,
      },
    });
  },

  getDetail: (id: string): Promise<FreelanceSettlement> => {
    return request.get(`/freelance-fees/settlements/${id}`);
  },

  generate: (freelancerId: string, storeId?: string): Promise<FreelanceSettlement> => {
    return request.post('/freelance-fees/settlements/generate', null, {
      params: { freelancer_id: freelancerId, store_id: storeId },
    });
  },

  confirm: (id: string, remark?: string): Promise<FreelanceSettlement> => {
    return request.post(`/freelance-fees/settlements/${id}/confirm`, { remark });
  },

  reject: (id: string, rejectReason: string): Promise<FreelanceSettlement> => {
    return request.post(`/freelance-fees/settlements/${id}/reject`, { reject_reason: rejectReason });
  },

  markPaid: (id: string): Promise<FreelanceSettlement> => {
    return request.post(`/freelance-fees/settlements/${id}/paid`);
  },

  getStatistics: (storeId?: string): Promise<{
    totalFreelancers: number;
    totalSettledAmount: number;
    totalPendingAmount: number;
  }> => {
    return request.get('/freelance-fees/statistics', { params: { store_id: storeId } });
  },

  getStatisticsByFreelancer: (storeId?: string): Promise<Array<{
    freelancerId: string;
    freelancerName: string;
    settlementCount: number;
    totalAmount: number;
    actualAmount: number;
  }>> => {
    return request.get('/freelance-fees/statistics/by-freelancer', { params: { store_id: storeId } });
  },

  getStatisticsByMonth: (storeId?: string, months?: number): Promise<Array<{
    month: string;
    settlementCount: number;
    totalAmount: number;
    actualAmount: number;
  }>> => {
    return request.get('/freelance-fees/statistics/by-month', { params: { store_id: storeId, months } });
  },

  getTaskStatistics: (storeId?: string): Promise<{
    taskCounts: Record<string, number>;
    totalTasks: number;
    totalInteractions: number;
  }> => {
    return request.get('/freelance-fees/statistics/tasks', { params: { store_id: storeId } });
  },

  batchUpdateEngagement: (updates: Array<{
    taskId: string;
    likesCount?: number;
    commentsCount?: number;
    isIndexed?: boolean;
    screenshotUrl?: string;
  }>): Promise<{ updated: number; errors: Array<{ task_id: string; error: string }> }> => {
    return request.post('/freelance-fees/engagement/batch-update', {
      updates: updates.map(u => ({
        task_id: u.taskId,
        likes_count: u.likesCount,
        comments_count: u.commentsCount,
        is_indexed: u.isIndexed,
        screenshot_url: u.screenshotUrl,
      })),
    });
  },

  getExportSettlementsUrl: (params?: { storeId?: string; status?: string; startDate?: string; endDate?: string }): string => {
    const base = '/api/v1/freelance-fees/export/settlements';
    const query = new URLSearchParams();
    if (params?.storeId) query.set('store_id', params.storeId);
    if (params?.status) query.set('status', params.status);
    if (params?.startDate) query.set('start_date', params.startDate);
    if (params?.endDate) query.set('end_date', params.endDate);
    const qs = query.toString();
    return qs ? `${base}?${qs}` : base;
  },

  getImportTemplateUrl: (): string => {
    return '/api/v1/freelance-fees/import/template';
  },

  importFreelancers: async (file: File): Promise<{
    success_count: number;
    fail_count: number;
    skipped_count: number;
    total: number;
    errors: string[];
  }> => {
    const formData = new FormData();
    formData.append('file', file);
    return request.post('/freelance-fees/import/freelancers', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};
