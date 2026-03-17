import Taro from '@tarojs/taro';
import type { User } from '@/types/api';
import { STORAGE_KEYS } from '@/constants/index';

export interface AuthPayload {
  accessToken: string;
  refreshToken?: string;
  user?: User | null;
}

export function getToken(): string {
  try {
    return Taro.getStorageSync(STORAGE_KEYS.TOKEN) || '';
  } catch (error) {
    console.error('Get token failed:', error);
    return '';
  }
}

export function getRefreshToken(): string {
  try {
    return Taro.getStorageSync(STORAGE_KEYS.REFRESH_TOKEN) || '';
  } catch (error) {
    console.error('Get refresh token failed:', error);
    return '';
  }
}

export function getCachedUser(): User | null {
  try {
    return Taro.getStorageSync(STORAGE_KEYS.USER_INFO) || null;
  } catch (error) {
    console.error('Get cached user failed:', error);
    return null;
  }
}

export function setCachedUser(user: User | null): void {
  try {
    if (user) {
      Taro.setStorageSync(STORAGE_KEYS.USER_INFO, user);
      return;
    }

    Taro.removeStorageSync(STORAGE_KEYS.USER_INFO);
  } catch (error) {
    console.error('Set cached user failed:', error);
  }
}

export function setAuth(payload: AuthPayload): void {
  try {
    Taro.setStorageSync(STORAGE_KEYS.TOKEN, payload.accessToken);

    if (payload.refreshToken) {
      Taro.setStorageSync(STORAGE_KEYS.REFRESH_TOKEN, payload.refreshToken);
    }

    if (payload.user !== undefined) {
      setCachedUser(payload.user);
    }
  } catch (error) {
    console.error('Set auth failed:', error);
  }
}

export function clearAuth(): void {
  try {
    Taro.removeStorageSync(STORAGE_KEYS.TOKEN);
    Taro.removeStorageSync(STORAGE_KEYS.REFRESH_TOKEN);
    Taro.removeStorageSync(STORAGE_KEYS.USER_INFO);
  } catch (error) {
    console.error('Clear auth failed:', error);
  }
}

export function checkLogin(): boolean {
  return !!getToken();
}
