import { request } from '../request';
import type { 
  Appointment, 
  CreateAppointmentParams, 
  AppointmentQueryParams,
  AppointmentStats,
  PageParams, 
  PageResult 
} from '@hospital/shared';

const PREFIX = '/appointments';

/**
 * 获取预约列表
 */
export const getList = (params?: PageParams & AppointmentQueryParams): Promise<PageResult<Appointment>> => {
  return request.get(PREFIX, { params });
};

/**
 * 获取预约详情
 */
export const getDetail = (id: string): Promise<Appointment> => {
  return request.get(`${PREFIX}/${id}`);
};

/**
 * 创建预约
 */
export const create = (data: CreateAppointmentParams): Promise<Appointment> => {
  return request.post(PREFIX, data);
};

/**
 * 取消预约
 */
export const cancel = (id: string, reason?: string): Promise<void> => {
  return request.put(`${PREFIX}/${id}/cancel`, { reason });
};

/**
 * 签到
 */
export const signIn = (id: string): Promise<void> => {
  return request.put(`${PREFIX}/${id}/sign-in`);
};

/**
 * 叫号
 */
export const call = (id: string): Promise<void> => {
  return request.put(`${PREFIX}/${id}/call`);
};

/**
 * 完成就诊
 */
export const complete = (id: string): Promise<void> => {
  return request.put(`${PREFIX}/${id}/complete`);
};

/**
 * 获取预约统计
 */
export const getStats = (params?: {
  startDate?: string;
  endDate?: string;
  doctorId?: string;
  departmentId?: string;
}): Promise<AppointmentStats> => {
  return request.get(`${PREFIX}/statistics`, { params });
};

/**
 * 获取今日预约
 */
export const getToday = (doctorId?: string): Promise<Appointment[]> => {
  return request.get(`${PREFIX}/today`, { params: { doctorId } });
};

