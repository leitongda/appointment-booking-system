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
    console.log('[departmentApi.getList] 原始参数:', params);
    // 转换参数名为 snake_case，过滤空值和 'all'
    const queryParams: Record<string, any> = {};

    if (params?.name) queryParams.name = params.name;
    if (params?.status !== undefined && params?.status !== null) queryParams.status = params.status;
    if (params?.parentId) queryParams.parent_id = params.parentId;
    // 门店筛选：排除 'all' 和空值
    if (params?.storeId && params.storeId !== 'all' && params.storeId !== '') {
      queryParams.store_id = params.storeId;
    }
    if (params?.page) queryParams.page = params.page;
    if (params?.pageSize) queryParams.page_size = params.pageSize;

    console.log('[departmentApi.getList] 转换后参数:', queryParams);
    return request.get('/departments', { params: queryParams });
  },

  getTree: (status?: number): Promise<DepartmentTreeNode[]> => {
    return request.get('/departments/tree', { params: { status } });
  },

  getHot: (limit?: number): Promise<Department[]> => {
    return request.get('/departments/hot', { params: { limit } });
  },

  /**
   * 获取所有启用的科室（下拉选择用）
   * @param storeId 门店ID（可选）
   */
  getAll: (storeId?: string): Promise<Department[]> => {
    return request.get('/departments/all', { params: storeId ? { store_id: storeId } : undefined });
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
