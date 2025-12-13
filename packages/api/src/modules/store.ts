import request from '../request';
import type { Store, StoreDepartment, PageResult } from '@hospital/shared';

export interface StoreListParams {
  keyword?: string;
  status?: number;
  city?: string;
  page?: number;
  pageSize?: number;
}

export interface StoreCreateData {
  name: string;
  code?: string;
  address?: string;
  province?: string;
  city?: string;
  district?: string;
  latitude?: string;
  longitude?: string;
  phone?: string;
  contactPerson?: string;
  description?: string;
  openingTime?: string;
  closingTime?: string;
  workingDays?: string;
  image?: string;
  sortOrder?: number;
  status?: number;
}

export const storeApi = {
  getList: (params?: StoreListParams): Promise<PageResult<Store>> => {
    // 转换参数名为后端期望的 snake_case 格式
    const queryParams = params ? {
      keyword: params.keyword,
      status: params.status,
      city: params.city,
      page: params.page,
      page_size: params.pageSize, // 转换为 snake_case
    } : undefined;
    return request.get('/stores', { params: queryParams });
  },

  getAll: (): Promise<Store[]> => {
    return request.get('/stores/all');
  },

  getDetail: (id: string): Promise<Store> => {
    return request.get(`/stores/${id}`);
  },

  create: (data: StoreCreateData): Promise<Store> => {
    return request.post('/stores', data);
  },

  update: (id: string, data: Partial<StoreCreateData>): Promise<Store> => {
    return request.put(`/stores/${id}`, data);
  },

  delete: (id: string): Promise<void> => {
    return request.delete(`/stores/${id}`);
  },

  updateStatus: (id: string, status: number): Promise<void> => {
    return request.patch(`/stores/${id}/status`, null, { params: { status } });
  },

  // 门店科室关联
  getDepartments: (storeId: string): Promise<StoreDepartment[]> => {
    return request.get(`/stores/${storeId}/departments`);
  },

  addDepartment: (
    storeId: string, 
    departmentId: string, 
    floor?: string, 
    room?: string
  ): Promise<StoreDepartment> => {
    return request.post(`/stores/${storeId}/departments`, null, {
      params: { department_id: departmentId, floor, room }
    });
  },

  updateDepartment: (
    relationId: string, 
    data: { floor?: string; room?: string; status?: number }
  ): Promise<StoreDepartment> => {
    return request.put(`/stores/departments/${relationId}`, data);
  },

  removeDepartment: (relationId: string): Promise<void> => {
    return request.delete(`/stores/departments/${relationId}`);
  },
};
