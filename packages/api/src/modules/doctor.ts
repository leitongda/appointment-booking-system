import request from '../request';
import type { Doctor, PageResult } from '@hospital/shared';

/**
 * 将 camelCase 字符串转换为 snake_case
 */
const toSnakeCase = (str: string): string => {
  return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
};

/**
 * 将对象的所有键从 camelCase 转换为 snake_case
 */
const toSnakeCaseKeys = (obj: Record<string, any>): Record<string, any> => {
  const result: Record<string, any> = {};
  for (const key of Object.keys(obj)) {
    const snakeKey = toSnakeCase(key);
    result[snakeKey] = obj[key];
  }
  return result;
};

export interface DoctorListParams {
  name?: string;
  storeId?: string;
  departmentId?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

export interface DoctorCreateData {
  // 基础信息
  storeId?: string;
  departmentId: string;
  name: string;
  username?: string;
  phone?: string;
  gender?: number;
  avatar?: string;
  banner?: string;
  title?: string;
  yearsOfExperience?: number;
  
  // 资质信息
  education?: string;
  graduateSchool?: string;
  licenseNumber?: string;
  licenseImage?: string;
  honors?: string;
  
  // 坐诊设置
  scheduleDesc?: string;
  maxDailyAppointments?: number;
  onlineConsultEnabled?: number;
  onlineConsultFee?: number;
  registrationFee?: number;
  
  // 展示设置
  pageStyle?: number;
  promoVideo?: string;
  tags?: string;
  specialty?: string;
  introduction?: string;
  
  // 其他设置
  isRecommended?: number;
  sortOrder?: number;
  status?: number;
  password?: string;
  
  // 诊费设置
  useFeeTemplate?: number;
}

export const doctorApi = {
  getList: (params?: DoctorListParams): Promise<PageResult<Doctor>> => {
    return request.get('/doctors', { params });
  },

  getRecommended: (limit?: number): Promise<Doctor[]> => {
    return request.get('/doctors/recommended', { params: { limit } });
  },

  getByDepartment: (departmentId: string): Promise<Doctor[]> => {
    return request.get(`/doctors/by-department/${departmentId}`);
  },

  /**
   * 检查医生账号是否已存在
   */
  checkUsername: (username: string, excludeId?: string): Promise<{ exists: boolean; suggestions: string[] }> => {
    return request.post('/doctors/check-username', { username, exclude_id: excludeId });
  },

  /**
   * 根据姓名生成医生账号
   */
  generateUsername: (name: string): Promise<{ username: string }> => {
    return request.post('/doctors/generate-username', { name });
  },

  /**
   * 搜索医生
   */
  search: async (keyword: string, limit?: number): Promise<Doctor[]> => {
    const result = await request.get<PageResult<Doctor>>('/doctors', {
      params: { name: keyword, page: 1, pageSize: limit || 10 },
    });
    return result.data ?? [];
  },

  getByStore: async (storeId: string): Promise<Doctor[]> => {
    const result = await request.get<any>('/doctors', {
      params: { store_id: storeId, page_size: 100 }
    });
    return result.data ?? [];
  },

  /**
   * 获取医生详情（公开接口，无需登录）
   * 用于患者端查看医生详情页
   */
  getDetail: (id: string): Promise<Doctor> => {
    return request.get(`/doctors/public/${id}`);
  },

  /**
   * 获取医生详情（管理端接口，需要管理员权限）
   */
  getDetailAdmin: (id: string): Promise<Doctor> => {
    return request.get(`/doctors/${id}`);
  },

  create: (data: DoctorCreateData): Promise<Doctor> => {
    // 自动将所有 camelCase 键转换为 snake_case
    const payload = toSnakeCaseKeys(data as Record<string, any>);
    return request.post('/doctors', payload);
  },

  update: (id: string, data: Partial<DoctorCreateData>): Promise<Doctor> => {
    // 自动将所有 camelCase 键转换为 snake_case，只保留有值的字段
    const payload: Record<string, any> = {};
    for (const [key, value] of Object.entries(data)) {
      if (value !== undefined) {
        payload[toSnakeCase(key)] = value;
      }
    }
    return request.put(`/doctors/${id}`, payload);
  },

  delete: (id: string): Promise<void> => {
    return request.delete(`/doctors/${id}`);
  },
};
