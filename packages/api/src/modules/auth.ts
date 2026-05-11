import { request } from '../request';
import type { LoginParams, LoginResult, User } from '@hospital/shared';

const PREFIX = '/auth';

export interface WechatLoginResponse {
  isNewUser: boolean;
  needBindPhone: boolean;
  openid: string;
  accessToken?: string;
  refreshToken?: string;
  expiresIn?: number;
}

// ============================================================
// 统一账号类型（对应后端 auth_types.py 的 AccountInfo）
// ============================================================

/** 角色类型枚举 */
export type RoleType = 'admin' | 'doctor' | 'user';

/** 管理员角色额外信息 */
export interface AdminAccountInfo {
  roleId?: string;
  roleCode?: string;
  roleName?: string;
  permissions?: string[];
  currentStoreId?: string;
  currentStoreName?: string;
  currentStoreLogo?: string;
  currentStoreTheme?: string;
  storeIds?: string[];
  stores?: { id: string; name: string; logo?: string }[];
  tenantId?: string;
  tenantName?: string;
  tenantCode?: string;
  tenantStatus?: number;
  isSuperAdmin?: boolean;
  isStoreAdmin?: boolean;
  isTenantAdmin?: boolean;
  isPlatformAdmin?: boolean;
  canViewAllStores?: boolean;
  canSwitchStores?: boolean;
}

/** 医生角色额外信息 */
export interface DoctorAccountInfo {
  id?: string;
  name?: string;
  departmentId?: string;
  departmentName?: string;
  title?: string;
  storeId?: string;
  storeName?: string;
  permissions?: string[];
}

/** 患者/用户角色额外信息 */
export interface UserAccountInfo {
  openid?: string;
  points?: number;
  isDoctor?: boolean;
  doctorId?: string;
  permissions?: string[];
}

/** 统一账号信息（对应后端 AccountInfo.to_dict() 的返回格式） */
export interface AccountInfo {
  // 基础信息
  id: string;
  roleType: RoleType;
  tenantId?: string;
  phone?: string;
  name?: string;
  nickname?: string;
  avatar?: string;
  status: number;

  // 管理员角色标志（扁平化，由后端 to_dict 合并）
  username?: string;
  isAdmin?: boolean;
  isDoctor?: boolean;
  permissions?: string[];

  // 管理员特有字段（扁平化后直接在顶层）
  roleId?: string;
  roleCode?: string;
  roleName?: string;
  currentStoreId?: string;
  currentStoreName?: string;
  storeIds?: string[];
  stores?: { id: string; name: string; logo?: string }[];
  isSuperAdmin?: boolean;
  isStoreAdmin?: boolean;
  isTenantAdmin?: boolean;
  isPlatformAdmin?: boolean;
  canSwitchStores?: boolean;

  // 医生特有字段（嵌套在 doctor 字段中）
  doctor?: DoctorAccountInfo;
  doctorId?: string;

  // 用户特有字段（扁平化后直接在顶层）
  gender?: number;
  openid?: string;
  points?: number;

  // 租户信息
  tenant?: {
    id?: string;
    name?: string;
    tenantCode?: string;
    status?: number;
  };
}

/**
 * 用户登录
 */
export const login = (data: LoginParams): Promise<LoginResult> => {
  return request.post(`${PREFIX}/login`, data);
};

/**
 * 用户注册
 */
export const register = (data: {
  phone: string;
  password: string;
  code: string;
  name: string;
}): Promise<User> => {
  return request.post(`${PREFIX}/register`, data);
};

/**
 * 退出登录
 */
export const logout = (): Promise<void> => {
  return request.post(`${PREFIX}/logout`);
};

/**
 * 刷新 Token
 */
export const refreshToken = (refreshToken: string): Promise<LoginResult> => {
  return request.post(`${PREFIX}/refresh`, { refresh_token: refreshToken });
};

export type SmsCodeType = 'login' | 'register' | 'reset';

/**
 * 发送短信验证码（统一入口）
 */
export const sendCode = (
  phone: string,
  codeType: SmsCodeType = 'reset',
): Promise<{ message: string; code?: string }> => {
  return request.post(`${PREFIX}/send-code`, { phone, code_type: codeType });
};

/**
 * 微信登录（获取 openid）
 * @param code 微信登录凭证
 * @param storeId 门店ID（用于获取对应门店的微信配置）
 */
export const wechatLogin = (code: string, storeId?: string): Promise<WechatLoginResponse> => {
  return request.post(`${PREFIX}/wechat/login`, { code, storeId });
};

/**
 * 微信获取手机号并登录
 * @param code 手机号获取凭证
 * @param openid 用户 openid
 * @param storeId 门店ID（用于获取对应门店的微信配置）
 */
export const wechatGetPhone = (code: string, openid: string, storeId?: string): Promise<LoginResult> => {
  return request.post(`${PREFIX}/wechat/phone`, { code, openid, storeId });
};

/**
 * 微信绑定手机号（手动输入）
 */
export const wechatBindPhone = (openid: string, phone: string): Promise<LoginResult> => {
  return request.post(`${PREFIX}/wechat/bind-phone`, { openid, phone });
};

/**
 * 微信绑定用户信息（头像昵称）并完成登录
 * @param openid 用户 openid
 * @param nickname 昵称
 * @param avatar 头像 URL
 */
export const wechatBindUserInfo = (openid: string, nickname: string, avatar?: string): Promise<LoginResult> => {
  return request.post(`${PREFIX}/wechat/bind-userinfo`, { openid, nickname, avatar });
};

/**
 * 管理员登录
 */
export const adminLogin = (data: { username: string; password: string }): Promise<LoginResult & { admin: any }> => {
  return request.post('/admin/login', data);
};

/**
 * 医生登录
 */
export const doctorLogin = (data: { phone: string; password: string }): Promise<LoginResult & { doctor: any }> => {
  return request.post('/doctors/login', data);
};

/**
 * 用户修改密码
 * @deprecated 请改用 userApi.changePassword（/users/change-password）
 */
export const changePassword = (data: { oldPassword: string; newPassword: string }): Promise<{ message: string }> => {
  return request.post('/users/change-password', {
    old_password: data.oldPassword,
    new_password: data.newPassword,
  });
};

/**
 * @deprecated 请改用 sendCode
 */
export const sendAuthCode = (phone: string, codeType: SmsCodeType = 'reset'): Promise<{ message: string; code?: string }> => {
  return sendCode(phone, codeType);
};

/**
 * 忘记密码（通过验证码重置）
 */
export const forgotPassword = (data: { phone: string; verificationCode: string; newPassword: string }): Promise<{ message: string }> => {
  return request.post(`${PREFIX}/forgot-password`, {
    phone: data.phone,
    verification_code: data.verificationCode,
    new_password: data.newPassword,
  });
};

/**
 * 获取统一账号信息（对应后端 get_current_account）
 * 返回 AccountInfo 格式的数据，包含角色类型、权限等信息
 */
export const getAccountMe = (): Promise<AccountInfo> => {
  return request.get(`/accounts/me`);
};

// ==================== 邮箱认证相关 ====================

/**
 * 发送邮箱验证码
 */
export const sendEmailCode = (
  email: string,
  codeType: 'login' | 'register' | 'reset' | 'bind' = 'login',
): Promise<{ message: string; code?: string }> => {
  return request.post(`${PREFIX}/email/send-code`, { email, code_type: codeType });
};

/**
 * 邮箱验证码登录（支持自动注册）
 */
export const emailLogin = (data: {
  email: string;
  code: string;
}): Promise<LoginResult> => {
  return request.post(`${PREFIX}/email/login`, {
    email: data.email,
    code: data.code,
  });
};

/**
 * 绑定邮箱
 */
export const emailBind = (data: {
  email: string;
  code: string;
}): Promise<{ message: string }> => {
  return request.post(`${PREFIX}/email/bind`, {
    email: data.email,
    code: data.code,
  });
};

/**
 * 解绑邮箱
 */
export const emailUnbind = (data: {
  code: string;
}): Promise<{ message: string }> => {
  return request.post(`${PREFIX}/email/unbind`, {
    code: data.code,
  });
};

/**
 * 换绑邮箱
 */
export const emailChange = (data: {
  newEmail: string;
  newEmailCode: string;
  oldEmailCode: string;
}): Promise<{ message: string }> => {
  return request.post(`${PREFIX}/email/change`, {
    new_email: data.newEmail,
    new_email_code: data.newEmailCode,
    old_email_code: data.oldEmailCode,
  });
};

export const authApi = {
  login,
  register,
  logout,
  refreshToken,
  sendCode,
  wechatLogin,
  wechatGetPhone,
  wechatBindPhone,
  wechatBindUserInfo,
  adminLogin,
  doctorLogin,
  changePassword,
  sendAuthCode,
  forgotPassword,
  /** 获取统一账号信息（预留，后端路由就绪后可用） */
  getAccountMe,
  sendEmailCode,
  emailLogin,
  emailBind,
  emailUnbind,
  emailChange,
};
