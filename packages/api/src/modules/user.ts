import request from '../request';
import type { User, Patient } from '@hospital/shared';

export interface PatientCreateData {
  name: string;
  phone: string;
  idCard?: string;
  gender?: number;
  relationship?: string;
  isDefault?: boolean;
}

export interface ChangePasswordData {
  oldPassword: string;
  newPassword: string;
}

export interface BindPhoneData {
  phone: string;
  code?: string;
}

export const userApi = {
  getProfile: (): Promise<User> => {
    return request.get('/users/profile');
  },

  updateProfile: (data: Partial<User>): Promise<User> => {
    return request.put('/users/profile', data);
  },

  /**
   * 修改密码
   */
  changePassword: (data: ChangePasswordData): Promise<{ message: string }> => {
    return request.post('/users/change-password', data);
  },

  /**
   * 绑定/更换手机号
   */
  bindPhone: (data: BindPhoneData): Promise<{ message: string }> => {
    return request.post('/users/bind-phone', data);
  },

  getPatients: (): Promise<Patient[]> => {
    return request.get('/users/patients');
  },

  /**
   * 获取就诊人详情
   */
  getPatientDetail: (id: string): Promise<Patient> => {
    return request.get(`/users/patients/${id}`);
  },

  addPatient: (data: PatientCreateData): Promise<Patient> => {
    return request.post('/users/patients', data);
  },

  /**
   * 创建就诊人（addPatient 的别名）
   */
  createPatient: (data: PatientCreateData): Promise<Patient> => {
    return request.post('/users/patients', data);
  },

  updatePatient: (id: string, data: Partial<PatientCreateData>): Promise<Patient> => {
    return request.put(`/users/patients/${id}`, data);
  },

  deletePatient: (id: string): Promise<void> => {
    return request.delete(`/users/patients/${id}`);
  },
};
