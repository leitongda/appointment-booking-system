import request from '../request';
import type { PageResult } from '@hospital/shared';

// ========== 站点 ==========
export interface CmsSite {
  id: string;
  tenantId?: string;
  name: string;
  code: string;
  description?: string;
  domain?: string;
  logoUrl?: string;
  faviconUrl?: string;
  themeConfig?: Record<string, any>;
  seoConfig?: Record<string, any>;
  status: number;
  isDefault: number;
  isDeleted?: boolean;
  createdAt: string;
  updatedAt?: string;
}

export interface CmsSiteCreateData {
  name: string;
  code: string;
  description?: string;
  domain?: string;
  logoUrl?: string;
  faviconUrl?: string;
  themeConfig?: Record<string, any>;
  seoConfig?: Record<string, any>;
  status?: number;
  isDefault?: number;
}

export interface CmsSiteUpdateData extends Partial<CmsSiteCreateData> {}

// ========== 栏目 ==========
export interface CmsCategory {
  id: string;
  tenantId?: string;
  siteId: string;
  name: string;
  slug: string;
  parentId?: string;
  sortOrder: number;
  icon?: string;
  description?: string;
  status: number;
  isDeleted?: boolean;
  createdAt: string;
  updatedAt?: string;
}

export interface CmsCategoryTreeNode extends CmsCategory {
  children: CmsCategoryTreeNode[];
}

export interface CmsCategoryCreateData {
  siteId: string;
  name: string;
  slug: string;
  parentId?: string;
  sortOrder?: number;
  icon?: string;
  description?: string;
  status?: number;
}

export interface CmsCategoryUpdateData extends Partial<CmsCategoryCreateData> {}

// ========== 文章 ==========
export interface CmsArticle {
  id: string;
  tenantId?: string;
  siteId: string;
  storeId?: string;
  categoryId?: string;
  title: string;
  subtitle?: string;
  slug?: string;
  coverImage?: string;
  summary?: string;
  content?: string;
  author?: string;
  source?: string;
  tags?: string[];
  sortOrder: number;
  isTop: number;
  status: number;
  publishTime?: string;
  viewCount: number;
  seoTitle?: string;
  seoKeywords?: string;
  seoDescription?: string;
  isDeleted?: boolean;
  createdAt: string;
  updatedAt?: string;
}

export interface CmsArticleCreateData {
  siteId: string;
  categoryId?: string;
  title: string;
  subtitle?: string;
  slug?: string;
  coverImage?: string;
  summary?: string;
  content: string;
  author?: string;
  source?: string;
  tags?: string[];
  sortOrder?: number;
  isTop?: number;
  status?: number;
  storeId?: string;
  seoTitle?: string;
  seoKeywords?: string;
  seoDescription?: string;
}

export interface CmsArticleUpdateData extends Partial<CmsArticleCreateData> {}

// ========== 站点 API ==========
export const siteApi = {
  getList: (params?: {
    keyword?: string;
    status?: number;
    page?: number;
    pageSize?: number;
  }): Promise<PageResult<CmsSite>> => request.get('/cms/sites', { params }),

  getDetail: (id: string): Promise<CmsSite> => request.get(`/cms/sites/${id}`),

  create: (data: CmsSiteCreateData): Promise<CmsSite> => request.post('/cms/sites', data),

  update: (id: string, data: CmsSiteUpdateData): Promise<CmsSite> =>
    request.put(`/cms/sites/${id}`, data),

  delete: (id: string): Promise<void> => request.delete(`/cms/sites/${id}`),

  restore: (id: string): Promise<void> => request.post(`/cms/sites/${id}/restore`),

  permanentDelete: (id: string): Promise<void> =>
    request.delete(`/cms/sites/${id}/permanent`),

  batchDelete: (ids: string[]): Promise<{ message: string; deletedCount: number }> =>
    request.post('/cms/sites/batch-delete', { ids }),
};

// ========== 栏目 API ==========
export const categoryApi = {
  getList: (params?: {
    siteId?: string;
    keyword?: string;
    status?: number;
  }): Promise<CmsCategory[]> => request.get('/cms/categories', { params }),

  getTree: (params?: { siteId?: string }): Promise<CmsCategoryTreeNode[]> =>
    request.get('/cms/categories/tree', { params }),

  getDetail: (id: string): Promise<CmsCategory> => request.get(`/cms/categories/${id}`),

  create: (data: CmsCategoryCreateData): Promise<CmsCategory> =>
    request.post('/cms/categories', data),

  update: (id: string, data: CmsCategoryUpdateData): Promise<CmsCategory> =>
    request.put(`/cms/categories/${id}`, data),

  delete: (id: string): Promise<void> => request.delete(`/cms/categories/${id}`),

  sort: (
    items: { id: string; sortOrder: number }[],
  ): Promise<{ message: string; updatedCount: number }> =>
    request.put('/cms/categories/sort', { items }),
};

// ========== 文章 API ==========
export const articleApi = {
  getList: (params?: {
    siteId?: string;
    categoryId?: string;
    status?: number;
    keyword?: string;
    storeId?: string;
    page?: number;
    pageSize?: number;
  }): Promise<PageResult<CmsArticle>> => request.get('/cms/articles', { params }),

  getPublished: (params: {
    siteId: string;
    categoryId?: string;
    storeId?: string;
    limit?: number;
  }): Promise<CmsArticle[]> => request.get('/cms/articles/published', { params }),

  getTrashList: (params?: {
    siteId?: string;
    page?: number;
    pageSize?: number;
  }): Promise<PageResult<CmsArticle>> => request.get('/cms/articles/trash', { params }),

  getDetail: (id: string): Promise<CmsArticle> => request.get(`/cms/articles/${id}`),

  getVersions: (
    id: string,
  ): Promise<
    {
      id: string;
      contentType: string;
      contentId: string;
      operatorId?: string;
      snapshot: Record<string, any>;
      createdAt?: string;
    }[]
  > => request.get(`/cms/articles/${id}/versions`),

  create: (data: CmsArticleCreateData): Promise<CmsArticle> =>
    request.post('/cms/articles', data),

  update: (id: string, data: CmsArticleUpdateData): Promise<CmsArticle> =>
    request.put(`/cms/articles/${id}`, data),

  delete: (id: string): Promise<void> => request.delete(`/cms/articles/${id}`),

  restore: (id: string): Promise<void> => request.post(`/cms/articles/${id}/restore`),

  permanentDelete: (id: string): Promise<void> =>
    request.delete(`/cms/articles/${id}/permanent`),

  batchDelete: (ids: string[]): Promise<{ message: string; deletedCount: number }> =>
    request.post('/cms/articles/batch-delete', { ids }),

  incrementView: (id: string): Promise<void> => request.post(`/cms/articles/${id}/view`),
};
