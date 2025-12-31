import request from '../request';
import type { Department, DepartmentTreeNode, DoctorListItem, PageResult } from '@hospital/shared';

export interface DepartmentListParams {
  name?: string;
  status?: number;
  parentId?: string;
  storeId?: string;
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
  
  // 基础配置
  storeId?: string;
  tag?: string;
  enableBanner?: number;
  enableIntro?: number;
  isFinal?: number;
  isRecommended?: number;
  
  // 图片资源
  bannerImage?: string;
  icon?: string;
  introImages?: string;
  
  // 详情内容
  introContent?: string;
  features?: string;
  appointmentNotice?: string;
  
  // 联系信息
  phone?: string;
  location?: string;
  workingHours?: string;
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

  /**
   * 搜索科室
   */
  search: async (keyword: string, limit?: number): Promise<Department[]> => {
    const result = await request.get<PageResult<Department>>('/departments', {
      params: { name: keyword, page: 1, pageSize: limit || 10 },
    });
    return result.data ?? [];
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

  // 科室医生关联
  getDoctors: (deptId: string): Promise<DoctorListItem[]> => {
    return request.get(`/departments/${deptId}/doctors`);
  },

  getAvailableDoctors: (deptId: string): Promise<DoctorListItem[]> => {
    return request.get(`/departments/${deptId}/available-doctors`);
  },

  batchBindDoctors: (deptId: string, doctorIds: string[]): Promise<{ message: string; count: number }> => {
    return request.put(`/departments/${deptId}/doctors/batch`, doctorIds);
  },

  /**
   * 批量更新科室排序
   */
  batchUpdateSort: (items: { id: string; sortOrder: number }[]): Promise<{ message: string; count: number }> => {
    return request.put('/departments/batch-sort', {
      items: items.map(item => ({ id: item.id, sort_order: item.sortOrder })),
    });
  },
};
