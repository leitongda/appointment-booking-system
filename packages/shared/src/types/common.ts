/**
 * API 响应结构
 */
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
  timestamp?: number;
}

/**
 * 分页请求参数
 */
export interface PageParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/**
 * 分页响应
 */
export interface PageResult<T> {
  list: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/**
 * 选项类型
 */
export interface Option<T = string | number> {
  label: string;
  value: T;
  disabled?: boolean;
}

/**
 * 树形结构
 */
export interface TreeNode<T = any> {
  id: string;
  parentId?: string;
  children?: TreeNode<T>[];
  [key: string]: any;
}

