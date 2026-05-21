import { request } from '../request';
import { withRetry } from '../utils/retry';
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

// ========== 权限 ==========
export interface Permission {
  id: string;
  code: string;
  name: string;
  type: 'menu' | 'button';
  controlType?: 'page' | 'tab' | 'action' | 'api';
  parentCode?: string;
  icon?: string;
  sort: number;
  children?: Permission[];
}

// ========== 门店信息 ==========
export interface StoreInfo {
  id: string;
  name: string;
  logo?: string;
  themeStyle?: string;
}

// ========== 管理员 ==========
export interface TenantStatusInfo {
  status: number;
  subscriptionPlanName?: string;
  subscriptionEndAt?: string;
  isSubscriptionActive: boolean;
  daysUntilExpiry?: number;
  contactPhone?: string;
}

export interface Admin {
  id: string;
  username: string;
  name?: string;
  phone?: string;
  email?: string;
  avatar?: string;
  roleId?: string;
  roleName?: string;
  roleCode?: string;
  // 当前选中门店
  currentStoreId?: string;
  currentStoreName?: string;
  // 兼容旧字段
  storeId?: string;
  storeName?: string;
  // 绑定的所有门店
  storeIds?: string[];
  stores?: StoreInfo[];
  // 权限相关
  permissions?: string[];
  isSuperAdmin?: boolean;
  isStoreAdmin?: boolean;
  canSwitchStores?: boolean;
  // 租户信息（多租户支持）
  tenantId?: string;
  tenant?: TenantStatusInfo;
  // 其他字段
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
  avatar?: string;
  roleId?: string;
  storeId?: string;
  storeIds?: string[];
  status?: number;
}

export interface AdminUpdateData {
  username?: string;
  password?: string;
  name?: string;
  phone?: string;
  email?: string;
  avatar?: string;
  roleId?: string;
  storeId?: string;
  storeIds?: string[];
  status?: number;
}

// ========== 门店切换 ==========
export interface MyStoresResult {
  stores: StoreInfo[];
  currentStoreId?: string;
  canSwitchStores: boolean;
}

export interface SwitchStoreResult {
  message: string;
  currentStore?: StoreInfo;
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
  store?: StoreInfo;  // 兼容旧版本，返回第一个门店
  stores?: StoreInfo[];  // 多门店管理员返回所有门店
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
  // 新字段：角色相关
  actorId?: string;
  actorName?: string;
  actorRole?: 'admin' | 'doctor' | 'user';
  // 保留旧字段以向后兼容
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

// ========== 在线用户 ==========
export interface DeviceInfo {
  browser: string;
  os: string;
  deviceType: 'desktop' | 'mobile' | 'tablet';
}

export interface OnlineUser {
  adminId: string;
  username: string;
  name?: string;
  roleName?: string;
  loginTime: string;
  loginIp: string;
  userAgent: string;
  deviceInfo: DeviceInfo;
  ttl: number;  // Token 剩余有效期（秒）
}

// ========== 用户状态 ==========
export interface UserStatus {
  adminId: string;
  username: string;
  name?: string;
  roleName?: string;
  status: 'online' | 'offline';
  // 在线时显示
  loginTime?: string;
  loginIp?: string;
  deviceInfo?: DeviceInfo;
  ttl?: number;
  // 离线时显示
  lastLoginAt?: string;
  lastLoginIp?: string;
}

// ========== 登录历史 ==========
export interface LoginHistory {
  id: string;
  loginTime: string;
  logoutTime?: string;
  logoutType?: 'manual' | 'timeout' | 'kicked';
  loginIp?: string;
  browser?: string;
  os?: string;
  deviceType?: 'desktop' | 'mobile' | 'tablet';
  duration?: number;  // 在线时长（秒）
}

export interface LoginHistoryResult {
  list: LoginHistory[];
  total: number;
  page: number;
  pageSize: number;
}

const PREFIX = '/admin';

export const adminApi = {
  // 获取 RSA 公钥
  getPublicKey: async (): Promise<string> => {
    console.log('📡 正在获取 RSA 公钥...');
    const result = await request.get<PublicKeyResponse>(
      `${PREFIX}/public-key`,
      withRetry({ maxRetries: 1 })
    );
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
      // 检查多种可能的错误消息格式
      const errorMessage = error.message || error.detail || '';
      const isDecryptError = errorMessage.includes('解密失败') || 
                            errorMessage.includes('密码解密失败') ||
                            errorMessage.includes('RSA密钥不匹配') ||
                            errorMessage.includes('Base64解码失败') ||
                            errorMessage.includes('无法解码为UTF-8字符串') ||
                            errorMessage.includes('密码加密数据格式错误');
      
      if (!retried && isDecryptError) {
        console.log('🔄 检测到公钥可能过期或密钥不匹配，清除缓存并重试...');
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

  // 更新当前管理员个人信息
  updateProfile: (data: { name?: string; phone?: string; email?: string; avatar?: string }): Promise<Admin> => {
    return request.put(`${PREFIX}/me`, data);
  },

  // 修改当前管理员密码
  changePassword: (data: { oldPassword: string; newPassword: string }): Promise<void> => {
    return request.put(`${PREFIX}/me/change-password`, {
      old_password: data.oldPassword,
      new_password: data.newPassword,
    });
  },

  // 发送管理员邮箱验证码
  sendEmailCode: (email: string): Promise<{ message: string; code?: string }> => {
    return request.post(`${PREFIX}/email/send-code`, { email, code_type: 'login' });
  },

  // 管理员邮箱验证码登录
  emailLogin: (data: { email: string; code: string }): Promise<AdminLoginResult> => {
    return request.post(`${PREFIX}/email/login`, {
      email: data.email,
      code: data.code,
    });
  },

  // 当前管理员发送邮箱绑定验证码
  sendProfileEmailCode: (email: string): Promise<{ message: string; code?: string }> => {
    return request.post(`${PREFIX}/me/email/send-code`, { email, code_type: 'bind' });
  },

  // 绑定当前管理员邮箱
  bindEmail: (data: { email: string; code: string }): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/me/email/bind`, {
      email: data.email,
      code: data.code,
    });
  },

  // 解绑当前管理员邮箱
  unbindEmail: (data: { code: string }): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/me/email/unbind`, {
      code: data.code,
    });
  },

  // 更换当前管理员邮箱
  changeEmail: (data: { newEmail: string; newEmailCode: string; oldEmailCode: string }): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/me/email/change`, {
      new_email: data.newEmail,
      new_email_code: data.newEmailCode,
      old_email_code: data.oldEmailCode,
    });
  },

  // 获取管理员详情（用于编辑）
  getAdminDetail: (id: string): Promise<Admin> => {
    return request.get(`${PREFIX}/admins/${id}`);
  },

  // ========== 手机号登录 ==========
  // 手机号+密码登录
  phoneLogin: async (data: PhoneLoginParams, retried = false): Promise<AdminLoginResult> => {
    try {
      // 检查是否已有缓存的公钥
      let publicKey = getPublicKey();
      
      if (!publicKey) {
        publicKey = await adminApi.getPublicKey();
      }
      
      // 加密密码
      const encryptedPassword = rsaEncrypt(data.password);
      
      // 发送加密后的密码
      const result = await request.post<AdminLoginResult>(`${PREFIX}/phone-login`, {
        phone: data.phone,
        password: encryptedPassword,
        encrypted: true,
      });
      
      return result;
    } catch (error: any) {
      // 如果是密码解密失败且未重试过，清除公钥缓存后重试
      // 检查多种可能的错误消息格式
      const errorMessage = error.message || error.detail || '';
      const isDecryptError = errorMessage.includes('解密失败') || 
                            errorMessage.includes('密码解密失败') ||
                            errorMessage.includes('RSA密钥不匹配') ||
                            errorMessage.includes('Base64解码失败') ||
                            errorMessage.includes('无法解码为UTF-8字符串') ||
                            errorMessage.includes('密码加密数据格式错误');
      
      if (!retried && isDecryptError) {
        console.log('🔄 检测到公钥可能过期或密钥不匹配，清除缓存并重试...');
        clearPublicKey();
        return adminApi.phoneLogin(data, true);
      }
      
      throw error;
    }
  },

  // ========== 短信验证码登录 ==========
  // 发送短信验证码
  sendSmsCode: (phone: string): Promise<void> => {
    return request.post(`${PREFIX}/sms/send`, { phone });
  },

  // 短信验证码登录
  smsLogin: (data: SmsLoginParams): Promise<AdminLoginResult> => {
    return request.post(`${PREFIX}/sms/login`, data);
  },

  // ========== 微信扫码登录 ==========
  // 获取微信扫码二维码
  getWechatQrcode: (): Promise<WechatQrcodeResult> => {
    return request.get(`${PREFIX}/wechat/qrcode`);
  },

  // 检查微信扫码状态
  checkWechatScan: (ticket: string): Promise<WechatCheckResult> => {
    return request.get(
      `${PREFIX}/wechat/check`,
      withRetry(
        { params: { ticket } },
        {
          maxRetries: 0,
          logRetry: false,
        }
      )
    );
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
    // 转换 camelCase 为后端期望的 snake_case
    const { roleId, storeId, ...rest } = data;
    return request.post(`${PREFIX}/admins`, { 
      ...rest, 
      role_id: roleId,
      store_id: storeId,
    });
  },

  updateAdmin: (id: string, data: AdminUpdateData): Promise<Admin> => {
    // 转换 camelCase 为后端期望的 snake_case
    const { roleId, storeId, ...rest } = data;
    const payload: any = { ...rest };
    if (roleId !== undefined) payload.role_id = roleId;
    if (storeId !== undefined) payload.store_id = storeId;
    return request.put(`${PREFIX}/admins/${id}`, payload);
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

  // ========== 权限管理 ==========
  // 获取权限树形结构（用于角色权限分配）
  getPermissionsTree: (): Promise<Permission[]> => {
    return request.get(`${PREFIX}/permissions/tree`);
  },

  // 获取所有权限（平铺列表）
  getAllPermissions: (): Promise<Permission[]> => {
    return request.get(`${PREFIX}/permissions/all`);
  },

  // 创建权限
  createPermission: (data: {
    code: string;
    name: string;
    type: string;
    controlType?: string;
    parentCode?: string;
    icon?: string;
    sort?: number;
  }): Promise<Permission> => {
    return request.post(`${PREFIX}/permissions`, {
      code: data.code,
      name: data.name,
      type: data.type,
      control_type: data.controlType,
      parent_code: data.parentCode,
      icon: data.icon,
      sort: data.sort ?? 0,
    });
  },

  // 批量创建权限
  batchCreatePermissions: (permissions: Array<{
    code: string;
    name: string;
    type: string;
    controlType?: string;
    parentCode?: string;
    icon?: string;
    sort?: number;
  }>): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/permissions/batch`, permissions.map((p) => ({
      code: p.code,
      name: p.name,
      type: p.type,
      control_type: p.controlType,
      parent_code: p.parentCode,
      icon: p.icon,
      sort: p.sort ?? 0,
    })));
  },

  // 删除权限
  deletePermission: (code: string): Promise<void> => {
    return request.delete(`${PREFIX}/permissions/${code}`);
  },

  // ========== 在线用户管理 ==========
  // 获取在线用户列表
  getOnlineUsers: (): Promise<OnlineUser[]> => {
    return request.get(`${PREFIX}/online-users`);
  },

  // 强制用户下线
  kickUser: (adminId: string): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/online-users/${adminId}/kick`);
  },

  // 退出登录
  logout: (): Promise<{ message: string }> => {
    return request.post(`${PREFIX}/logout`);
  },

  // ========== 用户状态管理 ==========
  // 获取所有用户状态列表（在线+离线）
  getUserStatus: (): Promise<UserStatus[]> => {
    return request.get(`${PREFIX}/user-status`);
  },

  // 获取指定用户的登录历史
  getLoginHistory: (adminId: string, params?: { page?: number; pageSize?: number }): Promise<LoginHistoryResult> => {
    return request.get(`${PREFIX}/login-history/${adminId}`, { params });
  },

  // ========== 门店切换 ==========
  // 获取当前用户绑定的门店列表
  getMyStores: (): Promise<MyStoresResult> => {
    return request.get(`${PREFIX}/me/stores`);
  },

  // 切换当前门店
  switchStore: (storeId: string): Promise<SwitchStoreResult> => {
    return request.put(`${PREFIX}/me/current-store`, { store_id: storeId });
  },

  // 切换当前租户（仅平台管理员）
  switchTenant: (tenantId: string): Promise<{ message: string; tenant: { id: string; name: string; tenantCode: string } }> => {
    return request.put(`${PREFIX}/me/current-tenant`, { tenant_id: tenantId });
  },
};
