import Taro from '@tarojs/taro';
import { STORAGE_KEYS } from '@hospital/shared';
import type { User } from '@hospital/shared';

export const AUTH_EVENTS = {
  LOGIN: 'auth:login',
  UPDATED: 'auth:updated',
  LOGOUT: 'auth:logout',
  EXPIRED: 'auth:expired',
} as const;

export type AuthEventName = typeof AUTH_EVENTS[keyof typeof AUTH_EVENTS];
export type AuthClearReason = 'logout' | 'expired';

export interface AuthEventPayload {
  type: AuthEventName;
  reason?: AuthClearReason;
  user?: User | null;
}

export interface AuthSessionPayload {
  accessToken: string;
  refreshToken?: string;
  user?: User | null;
}

let tokenExpiredHandling = false;
let tokenExpiredTimer: ReturnType<typeof setTimeout> | null = null;

const emitAuthEvent = (payload: AuthEventPayload) => {
  Taro.eventCenter.trigger(payload.type, payload);
};

const withStorage = <T>(handler: () => T, fallback: T): T => {
  try {
    return handler();
  } catch {
    return fallback;
  }
};

const resetTokenExpiredHandling = () => {
  tokenExpiredHandling = false;
  if (tokenExpiredTimer) {
    clearTimeout(tokenExpiredTimer);
    tokenExpiredTimer = null;
  }
};

export const getToken = (): string | null =>
  withStorage(() => Taro.getStorageSync(STORAGE_KEYS.TOKEN) || null, null);

export const getRefreshToken = (): string | null =>
  withStorage(() => Taro.getStorageSync(STORAGE_KEYS.REFRESH_TOKEN) || null, null);

export const getCachedUser = (): User | null =>
  withStorage(() => {
    const value = Taro.getStorageSync(STORAGE_KEYS.USER_INFO);
    if (!value) return null;
    if (typeof value === 'string') {
      return JSON.parse(value) as User;
    }
    return value as User;
  }, null);

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

export const setStorage = (key: string, value: any): void => {
  try {
    Taro.setStorageSync(key, typeof value === 'string' ? value : JSON.stringify(value));
  } catch (error) {
    console.error('设置存储失败', error);
  }
};

export const removeStorage = (key: string): void => {
  try {
    Taro.removeStorageSync(key);
  } catch (error) {
    console.error('移除存储失败', error);
  }
};

export const setRefreshToken = (refreshToken: string): void => {
  try {
    Taro.setStorageSync(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
  } catch (error) {
    console.error('设置 Refresh Token 失败', error);
  }
};

export const setAuthSession = ({ accessToken, refreshToken, user }: AuthSessionPayload): void => {
  try {
    Taro.setStorageSync(STORAGE_KEYS.TOKEN, accessToken);
    if (refreshToken) {
      Taro.setStorageSync(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
    }
    if (typeof user !== 'undefined') {
      Taro.setStorageSync(STORAGE_KEYS.USER_INFO, JSON.stringify(user));
    }
    resetTokenExpiredHandling();
    emitAuthEvent({
      type: AUTH_EVENTS.LOGIN,
      user: user ?? getCachedUser(),
    });
  } catch (error) {
    console.error('设置认证会话失败', error);
  }
};

export const updateAccessToken = ({ accessToken, refreshToken, user }: AuthSessionPayload): void => {
  try {
    Taro.setStorageSync(STORAGE_KEYS.TOKEN, accessToken);
    if (refreshToken) {
      Taro.setStorageSync(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
    }
    if (typeof user !== 'undefined') {
      Taro.setStorageSync(STORAGE_KEYS.USER_INFO, JSON.stringify(user));
    }
    emitAuthEvent({
      type: AUTH_EVENTS.UPDATED,
      user: user ?? getCachedUser(),
    });
  } catch (error) {
    console.error('更新认证会话失败', error);
  }
};

export const clearAuthSession = (reason: AuthClearReason = 'logout'): void => {
  if (reason === 'expired' && tokenExpiredHandling) {
    return;
  }

  if (reason === 'expired') {
    tokenExpiredHandling = true;
  }

  try {
    Taro.removeStorageSync(STORAGE_KEYS.TOKEN);
    Taro.removeStorageSync(STORAGE_KEYS.REFRESH_TOKEN);
    Taro.removeStorageSync(STORAGE_KEYS.USER_INFO);
  } catch (error) {
    console.error('清理认证会话失败', error);
  }

  if (reason === 'expired') {
    Taro.showToast({ title: '登录已失效，请重新登录', icon: 'none' });
    tokenExpiredTimer = setTimeout(() => {
      resetTokenExpiredHandling();
    }, 3000);
  } else {
    resetTokenExpiredHandling();
  }

  emitAuthEvent({
    type: reason === 'expired' ? AUTH_EVENTS.EXPIRED : AUTH_EVENTS.LOGOUT,
    reason,
    user: null,
  });
};

export const subscribeAuthChange = (
  listener: (payload: AuthEventPayload) => void
): (() => void) => {
  const handlers = Object.values(AUTH_EVENTS).map((eventName) => {
    const handler = (payload: AuthEventPayload) => listener(payload);
    Taro.eventCenter.on(eventName, handler);
    return { eventName, handler };
  });

  return () => {
    handlers.forEach(({ eventName, handler }) => {
      Taro.eventCenter.off(eventName, handler);
    });
  };
};

export const isLoggedIn = (): boolean => !!getToken();

export const checkLogin = (): boolean => isLoggedIn();

export const setToken = (token: string): void => {
  updateAccessToken({ accessToken: token });
};

export const removeToken = (): void => {
  clearAuthSession('logout');
};
