import { request } from '../request';
import type { PageParams, PageResult } from '@hospital/shared';

const PREFIX = '/content';

/**
 * Banner 类型
 */
export interface Banner {
  id: string;
  title?: string;
  imageUrl: string;
  linkUrl?: string;
  linkType: number;
  sortOrder: number;
}

/**
 * 新闻类型
 */
export interface News {
  id: string;
  typeId: string;
  typeName?: string;
  title: string;
  summary?: string;
  content: string;
  coverImage?: string;
  author?: string;
  viewCount: number;
  isTop: boolean;
  publishTime: string;
}

/**
 * 公告类型
 */
export interface Notice {
  id: string;
  title: string;
  content: string;
  type: number;
  isTop: boolean;
  publishTime: string;
}

/**
 * 弹框类型
 */
export interface Popup {
  id: string;
  title?: string;
  imageUrl: string;
  linkUrl?: string;
}

/**
 * 获取轮播图
 */
export const getBanners = (): Promise<Banner[]> => {
  return request.get(`${PREFIX}/banners`);
};

/**
 * 获取新闻列表
 */
export const getNewsList = (params?: PageParams & { typeId?: string }): Promise<PageResult<News>> => {
  return request.get(`${PREFIX}/news`, { params });
};

/**
 * 获取新闻详情
 */
export const getNewsDetail = (id: string): Promise<News> => {
  return request.get(`${PREFIX}/news/${id}`);
};

/**
 * 获取公告列表
 */
export const getNotices = (params?: PageParams & { type?: number }): Promise<PageResult<Notice>> => {
  return request.get(`${PREFIX}/notices`, { params });
};

/**
 * 获取弹框
 */
export const getPopups = (position?: string): Promise<Popup[]> => {
  return request.get(`${PREFIX}/popups`, { params: { position } });
};

