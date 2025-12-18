import request from '../request';
import type { Doctor, PageResult } from '@hospital/shared';

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

  getDetail: (id: string): Promise<Doctor> => {
    return request.get(`/doctors/${id}`);
  },

  create: (data: DoctorCreateData): Promise<Doctor> => {
    return request.post('/doctors', data);
  },

  update: (id: string, data: Partial<DoctorCreateData>): Promise<Doctor> => {
    return request.put(`/doctors/${id}`, data);
  },

  delete: (id: string): Promise<void> => {
    return request.delete(`/doctors/${id}`);
  },
};
