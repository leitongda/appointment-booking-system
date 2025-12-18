/**
 * 本地存储 Key
 */
export const STORAGE_KEYS = {
  TOKEN: 'hospital_token',
  REFRESH_TOKEN: 'hospital_refresh_token',
  USER_INFO: 'hospital_user_info',
  /** 上次访问的页面路径 */
  LAST_PATH: 'hospital_last_path',
  /** 登录方式 */
  LOGIN_TYPE: 'hospital_login_type',
  /** 手机号登录子方式 */
  PHONE_LOGIN_TYPE: 'hospital_phone_login_type',
} as const;

/**
 * 获取存储
 */
export const getStorage = <T = string>(key: string): T | null => {
  try {
    const value = localStorage.getItem(key);
    if (!value) return null;
    return JSON.parse(value) as T;
  } catch {
    return localStorage.getItem(key) as T | null;
  }
};

/**
 * 设置存储
 */
export const setStorage = (key: string, value: any): void => {
  if (typeof value === 'string') {
    localStorage.setItem(key, value);
  } else {
    localStorage.setItem(key, JSON.stringify(value));
  }
};

/**
 * 移除存储
 */
export const removeStorage = (key: string): void => {
  localStorage.removeItem(key);
};

/**
 * 清空存储
 */
export const clearStorage = (): void => {
  localStorage.clear();
};

/**
 * Token 相关
 */
export const getToken = (): string | null => {
  return getStorage<string>(STORAGE_KEYS.TOKEN);
};

export const setToken = (token: string): void => {
  setStorage(STORAGE_KEYS.TOKEN, token);
};

export const removeToken = (): void => {
  removeStorage(STORAGE_KEYS.TOKEN);
  removeStorage(STORAGE_KEYS.REFRESH_TOKEN);
};

/**
 * Token 失效处理工具
 * 用于防止多个请求同时返回 401 时重复弹窗
 */
let isTokenExpiredHandling = false;
let tokenExpiredTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * 处理 Token 失效
 * @param callback 回调函数，用于执行实际的处理逻辑（如弹窗、跳转）
 * @returns 如果是第一次触发返回 true，重复触发返回 false
 */
export const handleTokenExpired = (callback?: () => void): boolean => {
  // 如果正在处理中，忽略后续请求
  if (isTokenExpiredHandling) {
    return false;
  }
  
  isTokenExpiredHandling = true;
  
  // 清除 token
  removeToken();
  
  // 执行回调
  callback?.();
  
  // 清除之前的定时器
  if (tokenExpiredTimer) {
    clearTimeout(tokenExpiredTimer);
  }
  
  // 3 秒后重置状态，允许再次触发
  tokenExpiredTimer = setTimeout(() => {
    isTokenExpiredHandling = false;
    tokenExpiredTimer = null;
  }, 3000);
  
  return true;
};

/**
 * 重置 Token 失效处理状态
 * 在登录成功后调用
 */
export const resetTokenExpiredState = (): void => {
  isTokenExpiredHandling = false;
  if (tokenExpiredTimer) {
    clearTimeout(tokenExpiredTimer);
    tokenExpiredTimer = null;
  }
};

