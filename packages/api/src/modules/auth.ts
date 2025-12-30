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

/**
 * 发送验证码
 */
export const sendCode = (phone: string, type: 'login' | 'register' = 'login'): Promise<void> => {
  return request.post(`${PREFIX}/send-code`, { phone, type });
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

export const authApi = {
  login,
  register,
  logout,
  refreshToken,
  sendCode,
  wechatLogin,
  wechatGetPhone,
  wechatBindPhone,
  adminLogin,
  doctorLogin,
};
