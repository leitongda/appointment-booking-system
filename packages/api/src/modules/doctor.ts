import { request } from '../request';
import type { Doctor, DoctorQueryParams, PageParams, PageResult, Schedule } from '@hospital/shared';

const PREFIX = '/doctors';

/**
 * 获取医生列表
 */
export const getList = (params?: PageParams & DoctorQueryParams): Promise<PageResult<Doctor>> => {
  return request.get(PREFIX, { params });
};

/**
 * 获取医生详情
 */
export const getDetail = (id: string): Promise<Doctor> => {
  return request.get(`${PREFIX}/${id}`);
};

/**
 * 获取医生排班
 */
export const getSchedules = (id: string, params?: {
  startDate?: string;
  endDate?: string;
}): Promise<Schedule[]> => {
  return request.get(`${PREFIX}/${id}/schedules`, { params });
};

/**
 * 获取推荐医生
 */
export const getRecommended = (limit?: number): Promise<Doctor[]> => {
  return request.get(`${PREFIX}/recommended`, { params: { limit } });
};

/**
 * 创建医生
 */
export const create = (data: Partial<Doctor>): Promise<Doctor> => {
  return request.post(PREFIX, data);
};

/**
 * 更新医生
 */
export const update = (id: string, data: Partial<Doctor>): Promise<Doctor> => {
  return request.put(`${PREFIX}/${id}`, data);
};

/**
 * 删除医生
 */
export const remove = (id: string): Promise<void> => {
  return request.delete(`${PREFIX}/${id}`);
};

