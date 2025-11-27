import { request } from '../request';
import type { User, Patient } from '@hospital/shared';

const PREFIX = '/users';

/**
 * 获取当前用户信息
 */
export const getProfile = (): Promise<User> => {
  return request.get(`${PREFIX}/profile`);
};

/**
 * 更新用户信息
 */
export const updateProfile = (data: Partial<User>): Promise<User> => {
  return request.put(`${PREFIX}/profile`, data);
};

/**
 * 修改密码
 */
export const updatePassword = (data: {
  oldPassword: string;
  newPassword: string;
}): Promise<void> => {
  return request.put(`${PREFIX}/password`, data);
};

/**
 * 获取就诊人列表
 */
export const getPatients = (): Promise<Patient[]> => {
  return request.get(`${PREFIX}/patients`);
};

/**
 * 添加就诊人
 */
export const addPatient = (data: Omit<Patient, 'id' | 'userId' | 'status' | 'createdAt'>): Promise<Patient> => {
  return request.post(`${PREFIX}/patients`, data);
};

/**
 * 更新就诊人
 */
export const updatePatient = (id: string, data: Partial<Patient>): Promise<Patient> => {
  return request.put(`${PREFIX}/patients/${id}`, data);
};

/**
 * 删除就诊人
 */
export const deletePatient = (id: string): Promise<void> => {
  return request.delete(`${PREFIX}/patients/${id}`);
};

/**
 * 设置默认就诊人
 */
export const setDefaultPatient = (id: string): Promise<void> => {
  return request.put(`${PREFIX}/patients/${id}/default`);
};

