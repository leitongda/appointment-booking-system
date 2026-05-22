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
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, any>;
  };
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
