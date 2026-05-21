import request from '../request';

// -------------------------------------------
// Types
// -------------------------------------------

/** 候补状态 */
export type WaitlistStatus = 'WAITING' | 'PROMOTED' | 'CANCELLED' | 'EXPIRED';

/** 候补记录 */
export interface WaitlistEntry {
  id: string;
  userId: string;
  patientId: string;
  patientName?: string;
  scheduleId: string;
  shiftTypeId?: string;
  status: WaitlistStatus;
  position: number;
  priority: number;
  symptomDescription?: string;
  createdAt: string;
  promotedAt?: string;
  cancelledAt?: string;
  // 关联的排班信息（详情接口返回）
  schedule?: {
    id: string;
    scheduleDate: string;
    timeSlot: string;
    startTime?: string;
    endTime?: string;
    totalSlots: number;
    bookedSlots: number;
    doctorName?: string;
    doctorTitle?: string;
    departmentName?: string;
    storeName?: string;
  };
}

/** 加入候补请求 */
export interface JoinWaitlistParams {
  scheduleId: string;
  patientId: string;
  symptomDescription?: string;
}

/** 我的候补列表查询参数 */
export interface MyWaitlistParams {
  status?: WaitlistStatus;
  page?: number;
  pageSize?: number;
}

/** 分页结果 */
export interface WaitlistPageResult {
  items: WaitlistEntry[];
  total: number;
  page: number;
  pageSize: number;
}

/** 候补统计 */
export interface WaitlistStats {
  totalWaiting: number;
  totalPromoted: number;
  totalCancelled: number;
  totalExpired: number;
}

/** 管理端列表查询参数 */
export interface WaitlistListParams {
  storeId?: string;
  departmentId?: string;
  doctorId?: string;
  status?: WaitlistStatus;
  startDate?: string;
  endDate?: string;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

// -------------------------------------------
// API
// -------------------------------------------

export const waitlistApi = {
  /**
   * 加入候补队列
   */
  join: (params: JoinWaitlistParams): Promise<WaitlistEntry> => {
    return request.post('/waitlist', {
      schedule_id: params.scheduleId,
      patient_id: params.patientId,
      symptom_description: params.symptomDescription,
    });
  },

  /**
   * 取消候补
   */
  leave: (entryId: string): Promise<WaitlistEntry> => {
    return request.put(`/waitlist/${entryId}/cancel`);
  },

  /**
   * 获取我的候补列表
   */
  getMyList: (params?: MyWaitlistParams): Promise<WaitlistPageResult> => {
    const queryParams = params
      ? {
          status: params.status,
          page: params.page,
          page_size: params.pageSize,
        }
      : undefined;
    return request.get('/waitlist/my', { params: queryParams });
  },

  /**
   * 获取候补详情
   */
  getDetail: (entryId: string): Promise<WaitlistEntry> => {
    return request.get(`/waitlist/${entryId}`);
  },

  /**
   * 获取用户在指定排班候补队列中的位置
   */
  getPosition: (scheduleId: string): Promise<{ position: number | null }> => {
    return request.get('/waitlist/position', { params: { schedule_id: scheduleId } });
  },

  // ---- 管理端接口 ----

  /**
   * 管理端：获取候补列表（支持多条件筛选）
   */
  adminList: (params?: WaitlistListParams): Promise<WaitlistPageResult> => {
    const queryParams = params
      ? {
          store_id: params.storeId,
          department_id: params.departmentId,
          doctor_id: params.doctorId,
          status: params.status,
          start_date: params.startDate,
          end_date: params.endDate,
          keyword: params.keyword,
          page: params.page,
          page_size: params.pageSize,
        }
      : undefined;
    return request.get('/waitlist', { params: queryParams });
  },

  /**
   * 管理端：手动递补候补用户
   */
  adminPromote: (entryId: string): Promise<WaitlistEntry> => {
    return request.post(`/waitlist/${entryId}/promote`);
  },

  /**
   * 管理端：取消候补
   */
  adminCancel: (entryId: string): Promise<WaitlistEntry> => {
    return request.post(`/waitlist/${entryId}/cancel`);
  },

  /**
   * 管理端：获取候补统计
   */
  getStats: (params?: { storeId?: string; startDate?: string; endDate?: string }): Promise<WaitlistStats> => {
    const queryParams = params
      ? {
          store_id: params.storeId,
          start_date: params.startDate,
          end_date: params.endDate,
        }
      : undefined;
    return request.get('/waitlist/stats', { params: queryParams });
  },
};
