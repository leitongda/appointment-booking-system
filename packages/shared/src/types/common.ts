export interface PageResult<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data?: T;
  // 分页响应额外字段
  total?: number;
  page?: number;
  pageSize?: number;
  page_size?: number; // 兼容后端 snake_case
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
}
