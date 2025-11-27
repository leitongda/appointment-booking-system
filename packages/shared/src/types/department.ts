export interface Department {
  id: string;
  name: string;
  parentId?: string;
  description?: string;
  sortOrder: number;
  isHot: number;
  status: number;
  createdAt: string;
  updatedAt: string;
}

export interface DepartmentTreeNode {
  id: string;
  name: string;
  parentId?: string;
  children: DepartmentTreeNode[];
}
