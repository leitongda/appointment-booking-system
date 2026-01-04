import request from '../request';
import type { Store, StoreDepartment, Department, PageResult, StoreWechatConfig } from '@hospital/shared';

export interface StoreAdmin {
  id: string;
  username: string;
  name?: string;
  phone?: string;
  email?: string;
  avatar?: string;
  roleId?: string;
  status: number;
  createdAt?: string;
}

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
  logo?: string;
  password?: string;
  email?: string;
  themeStyle?: string;
  sortOrder?: number;
  status?: number;
  maxCardsPerUser?: number;
}

export const storeApi = {
  /**
   * 通过门店编码获取门店信息（公开接口，无需登录）
   * 用于患者端初始化时验证门店
   */
  getByCode: (code: string): Promise<Store> => {
    return request.get(`/stores/by-code/${code}`);
  },

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
  getDepartments: (storeId: string): Promise<Department[]> => {
    return request.get(`/stores/${storeId}/departments`);
  },

  batchBindDepartments: (storeId: string, departmentIds: string[]): Promise<{ message: string; count: number }> => {
    return request.put(`/stores/${storeId}/departments/batch`, departmentIds);
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

  // 门店用户关联
  getAdmins: (storeId: string): Promise<StoreAdmin[]> => {
    return request.get(`/stores/${storeId}/admins`);
  },

  batchBindAdmins: (storeId: string, adminIds: string[]): Promise<{ message: string; count: number }> => {
    return request.put(`/stores/${storeId}/admins/batch`, adminIds);
  },

  // 门店微信配置
  getWechatConfig: (storeId: string): Promise<StoreWechatConfig> => {
    return request.get(`/stores/${storeId}/wechat-config`);
  },

  updateWechatConfig: (storeId: string, data: StoreWechatConfig): Promise<{ message: string }> => {
    return request.put(`/stores/${storeId}/wechat-config`, data);
  },

  // 门店签到二维码
  getCheckinQrcode: (storeId: string): Promise<{
    storeId: string;
    storeName: string;
    qrcodeContent: string;
    description: string;
  }> => {
    return request.get(`/stores/${storeId}/checkin-qrcode`);
  },

  // 检查门店名称或编码唯一性
  checkUnique: (
    field: 'name' | 'code',
    value: string,
    excludeId?: string
  ): Promise<{ exists: boolean }> => {
    return request.get('/stores/check-unique', {
      params: { field, value, exclude_id: excludeId }
    });
  },
};
