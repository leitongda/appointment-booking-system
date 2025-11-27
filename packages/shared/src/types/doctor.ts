import type { Department } from './department';

/**
 * 医生信息
 */
export interface Doctor {
  id: string;
  userId: string;
  hospitalId: string;
  branchId?: string;
  departmentId: string;
  employeeNo?: string;
  name: string;
  title?: string;
  specialty?: string;
  introduction?: string;
  avatar?: string;
  consultationFee: number;
  isExpert: boolean;
  isRecommended: boolean;
  status: number;
  createdAt: string;
  updatedAt: string;
  // 关联信息
  department?: Department;
}

/**
 * 医生简要信息
 */
export interface DoctorBrief {
  id: string;
  name: string;
  title?: string;
  avatar?: string;
  departmentName?: string;
  consultationFee: number;
}

/**
 * 医生查询参数
 */
export interface DoctorQueryParams {
  departmentId?: string;
  branchId?: string;
  title?: string;
  keyword?: string;
  isExpert?: boolean;
  isRecommended?: boolean;
}

