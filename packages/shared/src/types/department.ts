/**
 * 科室信息
 */
export interface Department {
  id: string;
  hospitalId: string;
  branchId?: string;
  parentId?: string;
  name: string;
  code?: string;
  icon?: string;
  description?: string;
  sortOrder: number;
  isHot: boolean;
  status: number;
  createdAt: string;
  updatedAt: string;
  // 子科室
  children?: Department[];
}

/**
 * 科室简要信息
 */
export interface DepartmentBrief {
  id: string;
  name: string;
  icon?: string;
}

