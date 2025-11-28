import request from '../request';
import type { Feedback, FeedbackType, PageResult } from '@hospital/shared';

export interface FeedbackCreateData {
  userId: string;
  userType?: string;
  feedbackType?: FeedbackType;
  title: string;
  content: string;
  images?: string[];
  contact?: string;
}

export interface FeedbackListParams {
  userId?: string;
  feedbackType?: string;
  status?: string;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export const feedbackApi = {
  // 获取反馈列表（管理端）
  getList: (params?: FeedbackListParams): Promise<PageResult<Feedback>> => {
    return request.get('/feedbacks', { 
      params: {
        user_id: params?.userId,
        feedback_type: params?.feedbackType,
        status: params?.status,
        keyword: params?.keyword,
        page: params?.page,
        page_size: params?.pageSize,
      }
    });
  },

  // 获取我的反馈列表
  getMyList: (userId: string): Promise<Feedback[]> => {
    return request.get('/feedbacks/my', { params: { user_id: userId } });
  },

  // 获取待处理数量
  getPendingCount: (): Promise<{ count: number }> => {
    return request.get('/feedbacks/pending-count');
  },

  // 获取统计数据
  getStatistics: (): Promise<any> => {
    return request.get('/feedbacks/statistics');
  },

  // 获取反馈详情
  getDetail: (id: string): Promise<Feedback> => {
    return request.get(`/feedbacks/${id}`);
  },

  // 提交反馈
  create: (data: FeedbackCreateData): Promise<Feedback> => {
    return request.post('/feedbacks', {
      user_id: data.userId,
      user_type: data.userType || 'patient',
      feedback_type: data.feedbackType || 'suggestion',
      title: data.title,
      content: data.content,
      images: data.images,
      contact: data.contact,
    });
  },

  // 回复反馈
  reply: (id: string, handlerId: string, reply: string, status?: string): Promise<Feedback> => {
    return request.post(`/feedbacks/${id}/reply`, 
      { reply, status: status || 'resolved' },
      { params: { handler_id: handlerId } }
    );
  },

  // 更新状态
  updateStatus: (id: string, status: string): Promise<void> => {
    return request.patch(`/feedbacks/${id}/status`, null, { params: { status } });
  },

  // 删除反馈
  delete: (id: string): Promise<void> => {
    return request.delete(`/feedbacks/${id}`);
  },
};
