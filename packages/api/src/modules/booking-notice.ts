import request from '../request';

export interface BookingNotice {
  id: string;
  type: string;
  title?: string;
  content?: string;
  sortOrder: number;
  status: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface BookingNoticeListResult {
  data: BookingNotice[];
  total: number;
  page: number;
  pageSize: number;
}

export interface BookingNoticeCreateData {
  type: string;
  title?: string;
  content?: string;
  sortOrder?: number;
  status?: number;
}

export interface BookingNoticeUpdateData {
  type?: string;
  title?: string;
  content?: string;
  sortOrder?: number;
  status?: number;
}

export const bookingNoticeApi = {
  /**
   * 获取生效的预约须知列表（公开接口）
   */
  getPublicList: (type?: 'BOOKING' | 'VISIT' | 'REFUND'): Promise<BookingNotice[]> => {
    return request.get('/booking-notices/public', {
      params: type ? { type } : undefined,
    });
  },

  /**
   * 获取预约须知列表（管理端）
   */
  getList: (params?: {
    type?: string;
    status?: number;
    page?: number;
    pageSize?: number;
  }): Promise<BookingNoticeListResult> => {
    return request.get('/booking-notices', { params });
  },

  /**
   * 获取预约须知详情
   */
  getDetail: (id: string): Promise<BookingNotice> => {
    return request.get(`/booking-notices/${id}`);
  },

  /**
   * 创建预约须知
   */
  create: (data: BookingNoticeCreateData): Promise<BookingNotice> => {
    return request.post('/booking-notices', data);
  },

  /**
   * 更新预约须知
   */
  update: (id: string, data: BookingNoticeUpdateData): Promise<BookingNotice> => {
    return request.put(`/booking-notices/${id}`, data);
  },

  /**
   * 删除预约须知
   */
  delete: (id: string): Promise<void> => {
    return request.delete(`/booking-notices/${id}`);
  },

  /**
   * 更新预约须知状态
   */
  updateStatus: (id: string, status: number): Promise<BookingNotice> => {
    return request.patch(`/booking-notices/${id}/status`, null, {
      params: { status },
    });
  },
};

