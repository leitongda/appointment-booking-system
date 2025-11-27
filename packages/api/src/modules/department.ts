import { request } from '../request';
import type { Department, PageParams, PageResult } from '@hospital/shared';

const PREFIX = '/departments';

/**
 * 获取科室列表
 */
export const getList = (params?: PageParams & { branchId?: string }): Promise<PageResult<Department>> => {
  return request.get(PREFIX, { params });
};

/**
 * 获取科室详情
 */
export const getDetail = (id: string): Promise<Department> => {
  return request.get(`${PREFIX}/${id}`);
};

/**
 * 获取科室树
 */
export const getTree = (branchId?: string): Promise<Department[]> => {
  return request.get(`${PREFIX}/tree`, { params: { branchId } });
};

/**
 * 获取热门科室
 */
export const getHot = (limit?: number): Promise<Department[]> => {
  return request.get(`${PREFIX}/hot`, { params: { limit } });
};

/**
 * 创建科室
 */
export const create = (data: Partial<Department>): Promise<Department> => {
  return request.post(PREFIX, data);
};

/**
 * 更新科室
 */
export const update = (id: string, data: Partial<Department>): Promise<Department> => {
  return request.put(`${PREFIX}/${id}`, data);
};

/**
 * 删除科室
 */
export const remove = (id: string): Promise<void> => {
  return request.delete(`${PREFIX}/${id}`);
};

