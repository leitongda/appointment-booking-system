import request from '../request';
import type { PageResult } from '@hospital/shared';

// ==================== 类型定义 ====================

export interface DictTypeItem {
  id: string;
  code: string;
  name: string;
  description?: string;
  status: number;
  tenantId?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface DictItemData {
  id: string;
  dictTypeId: string;
  label: string;
  value: string;
  sortOrder: number;
  status: number;
  extra?: Record<string, unknown>;
  createdAt?: string;
  updatedAt?: string;
}

export interface DictTypeListParams {
  status?: number;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface DictTypeCreateData {
  code: string;
  name: string;
  description?: string;
}

export interface DictTypeUpdateData {
  name?: string;
  description?: string;
  status?: number;
}

export interface DictItemCreateData {
  label: string;
  value: string;
  sortOrder?: number;
  extra?: Record<string, unknown>;
}

export interface DictItemUpdateData {
  label?: string;
  value?: string;
  sortOrder?: number;
  status?: number;
  extra?: Record<string, unknown>;
}

export interface DictOptionItem {
  label: string;
  value: string;
  extra?: Record<string, unknown>;
}

export interface DictOptionsResponse {
  code: string;
  items: DictOptionItem[];
}

export interface SortItemData {
  id: string;
  sortOrder: number;
}

// ==================== 管理 API ====================

export const dictApi = {
  // ---- 字典类型 ----

  getTypeList: (params?: DictTypeListParams): Promise<PageResult<DictTypeItem>> => {
    const queryParams = params ? {
      status: params.status,
      keyword: params.keyword,
      page: params.page,
      page_size: params.pageSize,
    } : undefined;
    return request.get('/dicts', { params: queryParams });
  },

  getTypeDetail: (id: string): Promise<DictTypeItem> => {
    return request.get(`/dicts/${id}`);
  },

  createType: (data: DictTypeCreateData): Promise<DictTypeItem> => {
    return request.post('/dicts', data);
  },

  updateType: (id: string, data: DictTypeUpdateData): Promise<DictTypeItem> => {
    return request.put(`/dicts/${id}`, data);
  },

  deleteType: (id: string): Promise<void> => {
    return request.delete(`/dicts/${id}`);
  },

  // ---- 字典项 ----

  getItems: (
    typeId: string,
    params?: { status?: number; keyword?: string; page?: number; pageSize?: number }
  ): Promise<PageResult<DictItemData>> => {
    const queryParams = params ? {
      status: params.status,
      keyword: params.keyword,
      page: params.page,
      page_size: params.pageSize,
    } : undefined;
    return request.get(`/dicts/${typeId}/items`, { params: queryParams });
  },

  createItem: (typeId: string, data: DictItemCreateData): Promise<DictItemData> => {
    return request.post(`/dicts/${typeId}/items`, data);
  },

  updateItem: (typeId: string, itemId: string, data: DictItemUpdateData): Promise<DictItemData> => {
    return request.put(`/dicts/${typeId}/items/${itemId}`, data);
  },

  deleteItem: (typeId: string, itemId: string): Promise<void> => {
    return request.delete(`/dicts/${typeId}/items/${itemId}`);
  },

  sortItems: (typeId: string, items: SortItemData[]): Promise<void> => {
    return request.put(`/dicts/${typeId}/items-sort`, { items });
  },

  // ==================== 公开查询 API ====================

  getOptions: (typeCode: string): Promise<DictOptionsResponse> => {
    return request.get(`/dict-options/${typeCode}`);
  },

  batchGetOptions: (codes: string[]): Promise<{ dicts: DictOptionsResponse[] }> => {
    return request.get('/dict-options', { params: { codes: codes.join(',') } });
  },
};
