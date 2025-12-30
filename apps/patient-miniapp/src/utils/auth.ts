import Taro from '@tarojs/taro';
import { STORAGE_KEYS } from '@hospital/shared';

/**
 * 小程序专用的 Token 操作函数
 * 使用 Taro Storage API 替代 localStorage
 */

/**
 * 获取 Token
 */
export const getToken = (): string | null => {
  try {
    return Taro.getStorageSync(STORAGE_KEYS.TOKEN) || null;
  } catch {
    return null;
  }
};

/**
 * 设置 Token
 */
export const setToken = (token: string): void => {
  try {
    Taro.setStorageSync(STORAGE_KEYS.TOKEN, token);
  } catch (error) {
    console.error('设置 Token 失败', error);
  }
};

/**
 * 移除 Token
 */
export const removeToken = (): void => {
  try {
    Taro.removeStorageSync(STORAGE_KEYS.TOKEN);
    Taro.removeStorageSync(STORAGE_KEYS.REFRESH_TOKEN);
  } catch (error) {
    console.error('移除 Token 失败', error);
  }
};

/**
 * 获取存储
 */
export const getStorage = <T = string>(key: string): T | null => {
  try {
    const value = Taro.getStorageSync(key);
    if (!value) return null;
    if (typeof value === 'string') {
      try {
        return JSON.parse(value) as T;
      } catch {
        return value as T;
      }
    }
    return value as T;
  } catch {
    return null;
  }
};

/**
 * 设置存储
 */
export const setStorage = (key: string, value: any): void => {
  try {
    Taro.setStorageSync(key, typeof value === 'string' ? value : JSON.stringify(value));
  } catch (error) {
    console.error('设置存储失败', error);
  }
};

/**
 * 移除存储
 */
export const removeStorage = (key: string): void => {
  try {
    Taro.removeStorageSync(key);
  } catch (error) {
    console.error('移除存储失败', error);
  }
};

/**
 * 检查登录状态，未登录则跳转到登录页
 * @returns 是否已登录
 */
export const checkLogin = (): boolean => {
  const token = getToken();
  if (!token) {
    Taro.showToast({ title: '请先登录', icon: 'none' });
    Taro.navigateTo({ url: '/pages/login/index' });
    return false;
  }
  return true;
};

