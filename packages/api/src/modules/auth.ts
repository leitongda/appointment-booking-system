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
 */
export const wechatLogin = (code: string): Promise<WechatLoginResponse> => {
  return request.post(`${PREFIX}/wechat/login`, { code });
};

/**
 * 微信获取手机号并登录
 */
export const wechatGetPhone = (code: string, openid: string): Promise<LoginResult> => {
  return request.post(`${PREFIX}/wechat/phone`, { code, openid });
};

/**
 * 微信绑定手机号（手动输入）
 */
export const wechatBindPhone = (openid: string, phone: string): Promise<LoginResult> => {
  return request.post(`${PREFIX}/wechat/bind-phone`, { openid, phone });
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
};
