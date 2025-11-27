/**
 * 本地存储 Key
 */
export const STORAGE_KEYS = {
  TOKEN: 'hospital_token',
  REFRESH_TOKEN: 'hospital_refresh_token',
  USER_INFO: 'hospital_user_info',
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

