import request from '../request';
import type { Department, DepartmentTreeNode, PageResult } from '@hospital/shared';

export interface DepartmentListParams {
  name?: string;
  status?: number;
  parentId?: string;
  page?: number;
  pageSize?: number;
}

export interface DepartmentCreateData {
  name: string;
  parentId?: string;
  description?: string;
  sortOrder?: number;
  isHot?: number;
  status?: number;
}

export const departmentApi = {
  getList: (params?: DepartmentListParams): Promise<PageResult<Department>> => {
    return request.get('/departments', { params });
  },

  getTree: (status?: number): Promise<DepartmentTreeNode[]> => {
    return request.get('/departments/tree', { params: { status } });
  },

  getHot: (limit?: number): Promise<Department[]> => {
    return request.get('/departments/hot', { params: { limit } });
  },

  getDetail: (id: string): Promise<Department> => {
    return request.get(`/departments/${id}`);
  },

  create: (data: DepartmentCreateData): Promise<Department> => {
    return request.post('/departments', data);
  },

  update: (id: string, data: Partial<DepartmentCreateData>): Promise<Department> => {
    return request.put(`/departments/${id}`, data);
  },

  delete: (id: string): Promise<void> => {
    return request.delete(`/departments/${id}`);
  },
};
