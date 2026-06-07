import request from '../request';
import type { PageResult } from '@hospital/shared';

// ========== 新闻 ==========
export interface News {
  id: string;
  title: string;
  type: number;
  coverImage?: string;
  summary?: string;
  content: string;
  viewCount: number;
  isTop: boolean;
  status: number;
  publishTime?: string;
  createdAt: string;
}

export interface NewsCreateData {
  title: string;
  type: number;
  coverImage?: string;
  summary?: string;
  content: string;
  isTop?: number;
  status?: number;
}

// ========== 公告 ==========
export interface Notice {
  id: string;
  title: string;
  type: number;
  content: string;
  viewCount: number;
  isTop: boolean;
  status: number;
  publishTime?: string;
  createdAt: string;
}

export interface NoticeCreateData {
  title: string;
  type: number;
  content: string;
  isTop?: number;
  status?: number;
}

// ========== 轮播图 ==========
export interface Banner {
  id: string;
  title?: string;
  imageUrl: string;
  linkType: number;
  linkUrl?: string;
  position: string;
  sortOrder: number;
  status: number;
  createdAt: string;
}

export interface BannerCreateData {
  title?: string;
  imageUrl: string;
  linkType?: number;
  linkUrl?: string;
  position?: string;
  sortOrder?: number;
  status?: number;
}

export const contentApi = {
  // 新闻
  getNewsList: (params?: { type?: number; status?: number; keyword?: string; page?: number; pageSize?: number }): Promise<PageResult<News>> => {
    return request.get('/content/news', { params });
  },

  getPublishedNews: (params?: { type?: number; limit?: number }): Promise<News[]> => {
    return request.get('/content/news/published', { params });
  },

  getNewsDetail: (id: string): Promise<News> => {
    return request.get(`/content/news/${id}`);
  },

  createNews: (data: NewsCreateData): Promise<News> => {
    return request.post('/content/news', data);
  },

  updateNews: (id: string, data: Partial<NewsCreateData>): Promise<void> => {
    return request.put(`/content/news/${id}`, data);
  },

  deleteNews: (id: string): Promise<void> => {
    return request.delete(`/content/news/${id}`);
  },

  batchDeleteNews: (ids: string[]): Promise<{ message: string; deletedCount: number }> => {
    return request.post('/content/news/batch-delete', { ids });
  },

  // 公告
  getNoticeList: (params?: { type?: number; status?: number; keyword?: string; page?: number; pageSize?: number }): Promise<PageResult<Notice>> => {
    return request.get('/content/notices', { params });
  },

  getPublishedNotices: (limit?: number): Promise<Notice[]> => {
    return request.get('/content/notices/published', { params: { limit } });
  },

  getNoticeDetail: (id: string): Promise<Notice> => {
    return request.get(`/content/notices/${id}`);
  },

  createNotice: (data: NoticeCreateData): Promise<Notice> => {
    return request.post('/content/notices', data);
  },

  updateNotice: (id: string, data: Partial<NoticeCreateData>): Promise<void> => {
    return request.put(`/content/notices/${id}`, data);
  },

  deleteNotice: (id: string): Promise<void> => {
    return request.delete(`/content/notices/${id}`);
  },

  batchDeleteNotices: (ids: string[]): Promise<{ message: string; deletedCount: number }> => {
    return request.post('/content/notices/batch-delete', { ids });
  },

  // 轮播图
  getBannerList: (params?: { position?: string; status?: number; storeId?: string; page?: number; pageSize?: number }): Promise<PageResult<Banner>> => {
    return request.get('/content/banners', { params });
  },

  getActiveBanners: (position?: string): Promise<Banner[]> => {
    return request.get('/content/banners/active', { params: { position } });
  },

  getBannerDetail: (id: string): Promise<Banner> => {
    return request.get(`/content/banners/${id}`);
  },

  createBanner: (data: BannerCreateData): Promise<Banner> => {
    return request.post('/content/banners', data);
  },

  updateBanner: (id: string, data: Partial<BannerCreateData>): Promise<void> => {
    return request.put(`/content/banners/${id}`, data);
  },

  deleteBanner: (id: string): Promise<void> => {
    return request.delete(`/content/banners/${id}`);
  },

  batchDeleteBanners: (ids: string[]): Promise<{ message: string; deletedCount: number }> => {
    return request.post('/content/banners/batch-delete', { ids });
  },

  updateBannerSort: (items: { id: string; sortOrder: number }[]): Promise<{ message: string; updatedCount: number }> => {
    return request.put('/content/banners/sort', { items });
  },
};
