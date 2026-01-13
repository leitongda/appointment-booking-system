import { get } from '@/utils/request';
import type { Schedule, Doctor, Department, DepartmentTreeNode, PaginatedResponse } from '@/types/api';

/**
 * 获取医生可预约排班
 */
export function getAvailableSchedules(doctorId: string, days?: number) {
  return get<Schedule[]>(`/schedules/available/${doctorId}`, { days });
}

/**
 * 获取推荐医生
 */
export function getRecommendedDoctors(limit?: number) {
  return get<Doctor[]>('/doctors/recommended', { limit });
}

/**
 * 按科室获取医生
 */
export function getDoctorsByDepartment(departmentId: string) {
  return get<Doctor[]>(`/doctors/by-department/${departmentId}`);
}

/**
 * 获取医生详情（公开）
 */
export function getDoctorById(id: string) {
  return get<Doctor>(`/doctors/public/${id}`);
}

/**
 * 搜索医生
 */
export function searchDoctors(name: string, page: number = 1, pageSize: number = 10) {
  return get<PaginatedResponse<Doctor>>('/doctors', {
    name,
    page,
    pageSize
  });
}

/**
 * 获取科室树
 */
export function getDepartmentTree(status?: number) {
  return get<DepartmentTreeNode[]>('/departments/tree', { status });
}

/**
 * 获取热门科室
 */
export function getHotDepartments(limit?: number) {
  return get<Department[]>('/departments/hot', { limit });
}

/**
 * 搜索科室
 */
export function searchDepartments(name: string, page: number = 1, pageSize: number = 10) {
  return get<PaginatedResponse<Department>>('/departments', {
    name,
    page,
    pageSize
  });
}
