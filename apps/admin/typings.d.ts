declare module 'slash2';
declare module '*.css';
declare module '*.less';
declare module '*.scss';
declare module '*.sass';
declare module '*.svg';
declare module '*.png';
declare module '*.jpg';
declare module '*.jpeg';
declare module '*.gif';
declare module '*.bmp';
declare module '*.tiff';

// API 类型定义
declare namespace API {
  interface CurrentUser {
    id?: string;
    username?: string;
    name?: string;
    avatar?: string;
    phone?: string;
    roleId?: string;
    roleName?: string;
    roleCode?: string;
    permissions?: string[];
  }

  interface LoginParams {
    username: string;
    password: string;
  }

  interface LoginResult {
    accessToken: string;
    refreshToken: string;
  }

  interface PageParams {
    current?: number;
    pageSize?: number;
  }

  interface PageResult<T> {
    data: T[];
    total: number;
    success: boolean;
  }
}
