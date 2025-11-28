import { request } from '../request';

// ========== 角色 ==========
export interface Role {
  id: string;
  name: string;
  code: string;
  description?: string;
  permissions?: string[];
  status: number;
  createdAt: string;
  updatedAt?: string;
}

export interface RoleCreateData {
  name: string;
  code: string;
  description?: string;
  permissions?: string[];
  status?: number;
}

// ========== 管理员 ==========
export interface Admin {
  id: string;
  username: string;
  name?: string;
  phone?: string;
  email?: string;
  avatar?: string;
  roleId?: string;
  roleName?: string;
  status: number;
  lastLoginAt?: string;
  lastLoginIp?: string;
  createdAt: string;
}

export interface AdminCreateData {
  username: string;
  password: string;
  name?: string;
  phone?: string;
  email?: string;
  roleId?: string;
  status?: number;
}

export interface AdminUpdateData {
  username?: string;
  password?: string;
  name?: string;
  phone?: string;
  email?: string;
  roleId?: string;
  status?: number;
}

export interface AdminLoginParams {
  username: string;
  password: string;
}

export interface AdminLoginResult {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  admin: Admin;
}

// ========== 操作日志 ==========
export interface OperationLog {
  id: string;
  adminId?: string;
  adminName?: string;
  module?: string;
  action?: string;
  method?: string;
  path?: string;
  params?: string;
  result?: string;
  ip?: string;
  userAgent?: string;
  duration?: number;
  createdAt: string;
}

export interface PageResult<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}

const PREFIX = '/admin';

export const adminApi = {
  // 管理员登录
  login: (data: AdminLoginParams): Promise<AdminLoginResult> => {
    return request.post(`${PREFIX}/login`, data);
  },

  // 获取当前管理员信息
  getCurrentAdmin: (): Promise<Admin> => {
    return request.get(`${PREFIX}/me`);
  },

  // ========== 角色管理 ==========
  getRoles: (params?: { 
    status?: number; 
    keyword?: string; 
    page?: number; 
    pageSize?: number 
  }): Promise<PageResult<Role>> => {
    return request.get(`${PREFIX}/roles`, { params });
  },

  getAllRoles: (): Promise<Role[]> => {
    return request.get(`${PREFIX}/roles/all`);
  },

  getRole: (id: string): Promise<Role> => {
    return request.get(`${PREFIX}/roles/${id}`);
  },

  createRole: (data: RoleCreateData): Promise<Role> => {
    return request.post(`${PREFIX}/roles`, data);
  },

  updateRole: (id: string, data: Partial<RoleCreateData>): Promise<Role> => {
    return request.put(`${PREFIX}/roles/${id}`, data);
  },

  updateRolePermissions: (id: string, permissions: string[]): Promise<void> => {
    return request.put(`${PREFIX}/roles/${id}/permissions`, permissions);
  },

  deleteRole: (id: string): Promise<void> => {
    return request.delete(`${PREFIX}/roles/${id}`);
  },

  // ========== 管理员管理 ==========
  getAdmins: (params?: { 
    roleId?: string;
    status?: number; 
    keyword?: string; 
    page?: number; 
    pageSize?: number 
  }): Promise<PageResult<Admin>> => {
    return request.get(`${PREFIX}/admins`, { params });
  },

  getAdmin: (id: string): Promise<Admin> => {
    return request.get(`${PREFIX}/admins/${id}`);
  },

  createAdmin: (data: AdminCreateData): Promise<Admin> => {
    return request.post(`${PREFIX}/admins`, data);
  },

  updateAdmin: (id: string, data: AdminUpdateData): Promise<Admin> => {
    return request.put(`${PREFIX}/admins/${id}`, data);
  },

  resetAdminPassword: (id: string, newPassword: string): Promise<void> => {
    return request.put(`${PREFIX}/admins/${id}/reset-password`, null, {
      params: { new_password: newPassword },
    });
  },

  deleteAdmin: (id: string): Promise<void> => {
    return request.delete(`${PREFIX}/admins/${id}`);
  },

  // ========== 操作日志 ==========
  getLogs: (params?: {
    adminId?: string;
    module?: string;
    startTime?: string;
    endTime?: string;
    page?: number;
    pageSize?: number;
  }): Promise<PageResult<OperationLog>> => {
    return request.get(`${PREFIX}/logs`, { params });
  },
};

