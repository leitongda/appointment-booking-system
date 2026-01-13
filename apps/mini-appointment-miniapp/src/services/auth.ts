import { get, post } from '@/utils/request';
import type { User } from '@/types/api';

/**
 * 微信登录响应
 */
export interface WechatLoginResponse {
  isNewUser: boolean;
  needBindPhone: boolean;
  openid: string;
  accessToken?: string;
  refreshToken?: string;
  expiresIn?: number;
}

/**
 * 微信手机号登录响应
 */
export interface WechatPhoneLoginResponse {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  user: User;
}

/**
 * 微信登录
 */
export function wechatLogin(code: string, storeId?: string) {
  return post<WechatLoginResponse>('/auth/wechat/login', {
    code,
    storeId
  }, {
    needAuth: false
  });
}

/**
 * 微信获取手机号并登录
 */
export function wechatPhoneLogin(code: string, openid: string, storeId?: string) {
  return post<WechatPhoneLoginResponse>('/auth/wechat/phone', {
    code,
    openid,
    storeId
  }, {
    needAuth: false
  });
}

/**
 * 微信绑定手机号（手动输入）
 */
export function wechatBindPhone(openid: string, phone: string) {
  return post('/auth/wechat/bind-phone', {
    openid,
    phone
  }, {
    needAuth: false
  });
}

/**
 * 微信绑定用户信息
 */
export function wechatBindUserInfo(openid: string, nickname: string, avatar?: string) {
  return post('/auth/wechat/bind-userinfo', {
    openid,
    nickname,
    avatar
  }, {
    needAuth: false
  });
}

/**
 * 刷新 Token
 */
export function refreshToken(refreshToken: string) {
  return post<WechatPhoneLoginResponse>('/auth/refresh', {
    refresh_token: refreshToken
  }, {
    needAuth: false
  });
}
