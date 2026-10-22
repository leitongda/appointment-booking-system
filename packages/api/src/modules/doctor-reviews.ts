import request from '../request';

/**
 * 医生评价条目（患者端公开接口契约，后端 BaseSchema 统一按 camelCase 序列化）
 */
export interface DoctorReviewItem {
  id: string;
  patientName?: string | null;
  rating?: number | null;
  content?: string | null;
  createdAt?: string | null;
}

/**
 * 医生评价分页响应（契约：{ items, total }）
 */
export interface DoctorReviewPageResult {
  items: DoctorReviewItem[];
  total: number;
}

export interface DoctorReviewListParams {
  doctorId: string;
  page?: number;
  pageSize?: number;
}

export interface DoctorReviewCreateData {
  doctorId: string;
  rating: number;
  content?: string;
}

export const doctorReviewApi = {
  /**
   * 获取医生评价列表（公开）
   * GET /doctor-reviews?doctor_id=&page=&page_size=
   */
  getList: (params: DoctorReviewListParams): Promise<DoctorReviewPageResult> => {
    return request.get('/doctor-reviews', {
      params: {
        doctor_id: params.doctorId,
        page: params.page,
        page_size: params.pageSize,
      },
    });
  },

  /**
   * 提交医生评价
   * POST /doctor-reviews body { doctor_id, rating, content }
   */
  create: (data: DoctorReviewCreateData): Promise<DoctorReviewItem> => {
    const payload: Record<string, any> = {
      doctor_id: data.doctorId,
      rating: data.rating,
    };
    if (data.content) payload.content = data.content;
    return request.post('/doctor-reviews', payload);
  },
};
