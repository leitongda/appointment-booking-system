import { request } from '../request';
import { rsaEncrypt, setPublicKey, getPublicKey, clearPublicKey } from './crypto';

// ========== 公钥响应 ==========
export interface PublicKeyResponse {
  publicKey: string;
}

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

export interface PhoneLoginParams {
  phone: string;
  password: string;
}

export interface SmsLoginParams {
  phone: string;
  code: string;
}

export interface AdminLoginResult {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  admin: Admin;
}

// ========== 微信扫码登录 ==========
export interface WechatQrcodeResult {
  qrcodeUrl: string;
  ticket: string;
  expireSeconds: number;
}

export interface WechatCheckResult {
  status: 'waiting' | 'scanned' | 'confirmed' | 'expired';
  accessToken?: string;
  refreshToken?: string;
  expiresIn?: number;
  admin?: Admin;
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
  // 获取 RSA 公钥
  getPublicKey: async (): Promise<string> => {
    console.log('📡 正在获取 RSA 公钥...');
    const result = await request.get<PublicKeyResponse>(`${PREFIX}/public-key`);
    console.log('🚀 收到响应:', result);
    
    const publicKey = result.publicKey;
    
    if (!publicKey) {
      console.error('❌ 公钥获取失败，返回数据:', result);
      throw new Error('公钥获取失败');
    }
    
    console.log('✓ 公钥获取成功，长度:', publicKey.length);
    
    // 缓存公钥
    setPublicKey(publicKey);
    return publicKey;
  },

  // 管理员登录（密码 RSA 加密传输）
  login: async (data: AdminLoginParams, retried = false): Promise<AdminLoginResult> => {
    console.log('🔐 开始登录流程...');
    
    try {
      // 检查是否已有缓存的公钥
      let publicKey = getPublicKey();
      
      if (!publicKey) {
        console.log('📡 未找到缓存的公钥，正在获取...');
        publicKey = await adminApi.getPublicKey();
      } else {
        console.log('✓ 使用缓存的公钥');
      }
      
      // 加密密码
      console.log('🔒 正在加密密码...');
      const encryptedPassword = rsaEncrypt(data.password);
      console.log('✓ 密码加密完成');
      
      // 发送加密后的密码
      console.log('📤 发送登录请求...');
      const result = await request.post<AdminLoginResult>(`${PREFIX}/login`, {
        username: data.username,
        password: encryptedPassword,
        encrypted: true,
      });
      
      console.log('✓ 登录成功');
      return result;
    } catch (error: any) {
      console.error('❌ 登录失败:', error);
      
      // 如果是密码解密失败且未重试过，清除公钥缓存后重试
      if (!retried && error.message?.includes('解密失败')) {
        console.log('🔄 检测到公钥可能过期，清除缓存并重试...');
        clearPublicKey();
        return adminApi.login(data, true);
      }
      
      throw error;
    }
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

