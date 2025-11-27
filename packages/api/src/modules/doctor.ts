import request from '../request';
import type { Doctor, PageResult } from '@hospital/shared';

export interface DoctorListParams {
  name?: string;
  departmentId?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

export interface DoctorCreateData {
  departmentId: string;
  name: string;
  phone?: string;
  avatar?: string;
  title?: string;
  specialty?: string;
  introduction?: string;
  registrationFee?: number;
  isRecommended?: number;
  sortOrder?: number;
  status?: number;
  password?: string;
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
