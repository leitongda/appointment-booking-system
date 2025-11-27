import { request } from '../request';
import type { Schedule, ScheduleQueryParams, ScheduleTemplate, PageParams, PageResult } from '@hospital/shared';

const PREFIX = '/schedules';

/**
 * 获取排班列表
 */
export const getList = (params?: PageParams & ScheduleQueryParams): Promise<PageResult<Schedule>> => {
  return request.get(PREFIX, { params });
};

/**
 * 获取可预约排班
 */
export const getAvailable = (params: {
  doctorId: string;
  startDate?: string;
  endDate?: string;
}): Promise<Schedule[]> => {
  return request.get(`${PREFIX}/available`, { params });
};

/**
 * 创建排班
 */
export const create = (data: Partial<Schedule>): Promise<Schedule> => {
  return request.post(PREFIX, data);
};

/**
 * 批量创建排班
 */
export const batchCreate = (data: Partial<Schedule>[]): Promise<Schedule[]> => {
  return request.post(`${PREFIX}/batch`, data);
};

/**
 * 根据模板生成排班
 */
export const generate = (params: {
  doctorId: string;
  startDate: string;
  endDate: string;
}): Promise<Schedule[]> => {
  return request.post(`${PREFIX}/generate`, params);
};

/**
 * 更新排班
 */
export const update = (id: string, data: Partial<Schedule>): Promise<Schedule> => {
  return request.put(`${PREFIX}/${id}`, data);
};

/**
 * 删除排班
 */
export const remove = (id: string): Promise<void> => {
  return request.delete(`${PREFIX}/${id}`);
};

/**
 * 停诊
 */
export const suspend = (id: string, reason?: string): Promise<void> => {
  return request.put(`${PREFIX}/${id}/suspend`, { reason });
};

/**
 * 获取排班模板
 */
export const getTemplates = (doctorId: string): Promise<ScheduleTemplate[]> => {
  return request.get(`${PREFIX}/templates`, { params: { doctorId } });
};

/**
 * 保存排班模板
 */
export const saveTemplate = (data: Partial<ScheduleTemplate>): Promise<ScheduleTemplate> => {
  return request.post(`${PREFIX}/templates`, data);
};

